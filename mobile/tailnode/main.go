// The desktop owns both pipes. Only the embedded tailnet listener accepts TCP.
package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/tls"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"slices"
	"strings"
	"time"

	"tailscale.com/tsnet"
)

type config struct{ Dir, Key, Channel string }

type gateway struct {
	protocol string
	host     string
	input    *bufio.Reader
	output   io.Writer
	slot     chan struct{}
	pending  chan struct{}
	peer     func(*http.Request) string
}

func (g *gateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Host != g.host || r.URL.RawQuery != "" || r.URL.IsAbs() {
		http.Error(w, "Invalid origin", 403)
		return
	}
	if r.Method != "GET" && r.Method != "POST" {
		w.WriteHeader(405)
		return
	}
	if r.Method == "POST" && r.Header.Get("Origin") != "https://"+g.host {
		w.WriteHeader(403)
		return
	}
	route, private := strings.CutPrefix(r.URL.Path, g.protocol+"/")
	if !private {
		switch r.URL.Path {
		case "/", "/companion.js", "/companion-language.js", "/companion-install.js", "/companion.css", "/companion.webmanifest", "/companion-icon-180.png", "/companion-icon-192.png", "/companion-icon-512.png":
			if r.Method != http.MethodGet {
				w.WriteHeader(405)
				return
			}
		default:
			w.WriteHeader(404)
			return
		}
	}
	limit := int64(40000)
	switch route {
	case "prompt":
		limit = 12000000
	case "transcribe":
		limit = 1400000
	}
	select {
	case g.pending <- struct{}{}:
		defer func() { <-g.pending }()
	default:
		http.Error(w, "Try again", 503)
		return
	}
	select {
	case g.slot <- struct{}{}:
		defer func() { <-g.slot }()
	case <-r.Context().Done():
		return
	}
	data, err := io.ReadAll(http.MaxBytesReader(w, r.Body, limit))
	if err != nil {
		http.Error(w, "Invalid request", 413)
		return
	}
	proxy := &http.Request{Method: r.Method, URL: &url.URL{Path: r.URL.Path}, Host: g.host, Header: make(http.Header), Body: io.NopCloser(bytes.NewReader(data)), ContentLength: int64(len(data))}
	id := g.peer(r)
	if id == "" {
		w.WriteHeader(403)
		return
	}
	proxy.Header.Set("X-Arise-Tailnode", id)
	for _, k := range []string{"Content-Type", "Cookie", "Origin"} {
		if v := r.Header.Get(k); v != "" {
			proxy.Header.Set(k, v)
		}
	}
	// A framing error invalidates the pipe; never reuse a partial exchange.
	var packet bytes.Buffer
	if err = proxy.Write(&packet); err != nil {
		w.WriteHeader(400)
		return
	}
	if err = binary.Write(g.output, binary.BigEndian, uint32(packet.Len())); err != nil {
		os.Exit(2)
	}
	if _, err = packet.WriteTo(g.output); err != nil {
		os.Exit(2)
	}
	resp, err := http.ReadResponse(g.input, proxy)
	if err != nil || resp.ContentLength < 0 {
		os.Exit(2)
	}
	defer resp.Body.Close()
	for k, vs := range resp.Header {
		for _, v := range vs {
			w.Header().Add(k, v)
		}
	}
	w.Header().Set("Strict-Transport-Security", "max-age=31536000")
	w.WriteHeader(resp.StatusCode)
	// Drain the desktop response even when the phone goes offline mid-download.
	_, _ = io.Copy(w, resp.Body)
	if _, err = io.Copy(io.Discard, resp.Body); err != nil {
		os.Exit(2)
	}
}

func run() error {
	pr, pw := io.Pipe()
	go func() { _, _ = io.Copy(pw, os.Stdin); os.Exit(0) }()
	in := bufio.NewReader(pr)
	line, err := in.ReadBytes('\n')
	if err != nil {
		return err
	}
	var cfg config
	if err = json.Unmarshal(line, &cfg); err != nil || cfg.Dir == "" {
		return errors.New("invalid configuration")
	}
	if cfg.Channel != "preview" && cfg.Channel != "stable" {
		return errors.New("invalid release channel")
	}
	name := "arise-" + cfg.Channel
	node := &tsnet.Server{Hostname: name, Dir: cfg.Dir, AuthKey: cfg.Key, Logf: func(string, ...any) {}, UserLogf: func(string, ...any) {}}
	defer node.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 35*time.Second)
	defer cancel()
	st, err := node.Up(ctx)
	if err != nil {
		return err
	}
	if st.Self == nil || st.Self.Tags == nil || st.Self.Tags.Len() != 1 || !slices.Contains(st.Self.Tags.AsSlice(), "tag:"+name) {
		return errors.New("missing node tag")
	}
	host := strings.TrimSuffix(st.Self.DNSName, ".")
	if !strings.HasSuffix(host, ".ts.net") {
		return errors.New("MagicDNS required")
	}
	listener, err := node.Listen("tcp", ":443")
	if err != nil {
		return err
	}
	client, err := node.LocalClient()
	if err != nil {
		return err
	}
	if _, err = client.GetCertificate(&tls.ClientHelloInfo{ServerName: host}); err != nil {
		return err
	}
	identity := func(r *http.Request) string {
		who, err := client.WhoIs(r.Context(), r.RemoteAddr)
		if err != nil || who.Node == nil {
			return ""
		}
		return string(who.Node.StableID)
	}
	server := &http.Server{Handler: &gateway{"/mobile/" + cfg.Channel + "/v1", host, in, os.Stdout, make(chan struct{}, 1), make(chan struct{}, 16), identity}, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 20 * time.Second, WriteTimeout: 150 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16384}
	fmt.Fprintln(os.Stdout, host)
	return server.Serve(tls.NewListener(listener, &tls.Config{MinVersion: tls.VersionTLS13, GetCertificate: func(hello *tls.ClientHelloInfo) (*tls.Certificate, error) {
		if hello.ServerName != host {
			return nil, errors.New("unexpected name")
		}
		return client.GetCertificate(hello)
	}}))
}

func main() {
	if run() != nil {
		os.Exit(1)
	}
}
