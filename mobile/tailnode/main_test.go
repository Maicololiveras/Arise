package main

import (
	"bufio"
	"bytes"
	"encoding/binary"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestPrivatePipe(t *testing.T) {
	const host = "arise-mobile.example.ts.net"
	var wire bytes.Buffer
	response := "HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}"
	g := gateway{host, bufio.NewReader(strings.NewReader(response)), &wire, make(chan struct{}, 1), make(chan struct{}, 16), func(*http.Request) string { return "verified-phone" }}
	request := httptest.NewRequest("POST", "/approval", strings.NewReader("{}"))
	request.Host = host
	denied := httptest.NewRecorder()
	g.ServeHTTP(denied, request)
	if denied.Code != 403 || wire.Len() != 0 {
		t.Fatal("unexpected cross-origin forwarding")
	}
	request.Header.Set("Origin", "https://"+host)
	request.Header.Set("X-Arise-Tailnode", "untrusted")
	request.Header.Set("Authorization", "desktop-only")
	request.Header.Set("Cookie", "arise_device=paired")
	ok := httptest.NewRecorder()
	g.ServeHTTP(ok, request)
	if ok.Code != 200 || ok.Body.String() != "{}" {
		t.Fatal(ok.Result())
	}
	var size uint32
	if err := binary.Read(&wire, binary.BigEndian, &size); err != nil || int(size) != wire.Len() {
		t.Fatal("bad pipe frame")
	}
	forwarded, err := http.ReadRequest(bufio.NewReader(&wire))
	if err != nil {
		t.Fatal(err)
	}
	body, err := io.ReadAll(forwarded.Body)
	if err != nil || string(body) != "{}" || forwarded.URL.Path != "/approval" || forwarded.Header.Get("Authorization") != "" || forwarded.Header.Get("X-Arise-Tailnode") != "verified-phone" || forwarded.Header.Get("Cookie") != "arise_device=paired" {
		t.Fatal("incorrect private request")
	}
}
