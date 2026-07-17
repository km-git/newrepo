package coordinator

import (
	"testing"
	"time"
)

func TestDispatcherRouteNonBlocking(t *testing.T) {
	h := NewHub()
	c := &ClientConn{
		ID: "exec-1", Country: "US", IP: "10.0.0.5",
		OnWiFi: true, Idle: true, Send: make(chan []byte, 1),
	}
	h.Register(c)
	d := NewDispatcher(h)

	res := d.Route(DispatchRequest{
		Country: "US",
		IPMask:  "10.0.0.0/8",
		Payload: []byte("job-1"),
	})
	if res.Err != nil {
		t.Fatal(res.Err)
	}
	if res.Matched != 1 || res.Delivered != 1 {
		t.Fatalf("result=%+v", res)
	}
	select {
	case p := <-c.Send:
		if string(p) != "job-1" {
			t.Fatalf("payload=%q", p)
		}
	case <-time.After(200 * time.Millisecond):
		t.Fatal("timeout waiting for payload")
	}

	// Fill buffer then ensure Route does not block when full.
	c.Send <- []byte("fill")
	start := time.Now()
	res2 := d.Route(DispatchRequest{Country: "US", Payload: []byte("job-2")})
	if time.Since(start) > 100*time.Millisecond {
		t.Fatal("Route blocked on full channel")
	}
	if res2.Dropped != 1 {
		t.Fatalf("expected drop on full buffer, got %+v", res2)
	}
}

func TestDispatcherRequiresCountry(t *testing.T) {
	d := NewDispatcher(NewHub())
	res := d.Route(DispatchRequest{Payload: []byte("x")})
	if res.Err == nil {
		t.Fatal("expected country error")
	}
}

func TestDispatcherRouteOne(t *testing.T) {
	h := NewHub()
	h.Register(&ClientConn{ID: "a", Country: "JP", IP: "1.2.3.4", OnWiFi: true, Idle: true, Send: make(chan []byte, 2)})
	h.Register(&ClientConn{ID: "b", Country: "JP", IP: "1.2.3.5", OnWiFi: true, Idle: true, Send: make(chan []byte, 2)})
	d := NewDispatcher(h)
	res := d.RouteOne(DispatchRequest{Country: "JP", Payload: []byte("one")})
	if res.Delivered != 1 || res.Matched != 2 {
		t.Fatalf("%+v", res)
	}
}

func TestParseIPMask(t *testing.T) {
	m, err := ParseIPMask("203.0.113.10")
	if err != nil || !m.Contains("203.0.113.10") || m.Contains("203.0.113.11") {
		t.Fatalf("exact mask failed: %v %v", m, err)
	}
	_, err = ParseIPMask("not-an-ip")
	if err == nil {
		t.Fatal("expected parse error")
	}
}
