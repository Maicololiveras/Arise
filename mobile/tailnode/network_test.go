//go:build tailnetintegration

package main

import (
	"bufio"
	"context"
	"crypto/tls"
	"crypto/x509"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"tailscale.com/net/netns"
	"tailscale.com/tailcfg"
	"tailscale.com/tsnet"
	"tailscale.com/tstest/integration"
	"tailscale.com/tstest/integration/testcontrol"
	"tailscale.com/types/logger"
)

// Exercise the production gateway between two userspace nodes on a test-only tailnet.
func TestTailnetPhone(t *testing.T) {
	netns.SetEnabled(false)
	t.Cleanup(func() { netns.SetEnabled(true) })
	ctl := &testcontrol.Server{DERPMap: integration.RunDERPAndSTUN(t, logger.Discard, "127.0.0.1"), MagicDNSDomain: "tail-scale.ts.net", DNSConfig: &tailcfg.DNSConfig{Proxied: true}}
	ctl.HTTPTestServer = httptest.NewServer(ctl)
	t.Cleanup(ctl.HTTPTestServer.Close)
	ctx, cancel := context.WithTimeout(context.Background(), 40*time.Second)
	defer cancel()
	start := func(name string) *tsnet.Server {
		n := &tsnet.Server{ControlURL: ctl.HTTPTestServer.URL, Dir: t.TempDir(), Hostname: name, Ephemeral: true}
		t.Cleanup(func() { n.Close() })
		if _, err := n.Up(ctx); err != nil {
			t.Fatal(err)
		}
		return n
	}
	host := start("arise-mobile")
	phone := start("phone")
	local, err := host.LocalClient()
	if err != nil {
		t.Fatal(err)
	}
	clientTransport := func(ctx context.Context, network, addr string) (net.Conn, error) {
		return phone.Dial(ctx, network, addr)
	}
	ln, err := host.Listen("tcp", ":443")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	certServer := httptest.NewTLSServer(nil)
	certificate := certServer.Certificate()
	certPair := certServer.TLS.Certificates[0]
	certServer.Close()
	roots := x509.NewCertPool()
	roots.AddCert(certificate)
	const service = "arise-mobile.tail-scale.ts.net"
	seen := make(chan string, 1)
	g := &gateway{"/mobile/preview/v1", service, bufio.NewReader(strings.NewReader("HTTP/1.0 200 OK\r\nContent-Length: 4\r\n\r\npass")), io.Discard, make(chan struct{}, 1), make(chan struct{}, 16), func(r *http.Request) string {
		w, e := local.WhoIs(r.Context(), r.RemoteAddr)
		if e != nil {
			return ""
		}
		seen <- string(w.Node.StableID)
		return string(w.Node.StableID)
	}}
	srv := http.Server{Handler: g}
	go srv.Serve(tls.NewListener(ln, &tls.Config{MinVersion: tls.VersionTLS13, Certificates: []tls.Certificate{certPair}}))
	defer srv.Close()
	tr := &http.Transport{DialContext: clientTransport, TLSClientConfig: &tls.Config{RootCAs: roots, ServerName: certificate.DNSNames[0], MinVersion: tls.VersionTLS13}}
	defer tr.CloseIdleConnections()
	addr, _ := host.TailscaleIPs()
	client := http.Client{Transport: tr}
	req, _ := http.NewRequestWithContext(ctx, "GET", "https://"+addr.String()+"/mobile/preview/v1/agents", nil)
	req.Host = service
	resp, err := client.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil || string(body) != "pass" || resp.TLS.Version != tls.VersionTLS13 {
		t.Fatalf("bad response %s %v", body, err)
	}
	pclient, _ := phone.LocalClient()
	status, err := pclient.Status(ctx)
	if err != nil || <-seen != string(status.Self.ID) {
		t.Fatal("wrong peer identity")
	}
}
