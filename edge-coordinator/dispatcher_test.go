package edgecoordinator

import (
	"context"
	"net"
	"testing"
	"time"
)

func TestDispatcherCountryIPRouting(t *testing.T) {
	hub := NewConnectionHub(NewStubStore())
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go hub.Run(ctx)

	c := &Client{
		NodeID:      7,
		Send:        make(chan []byte, 4),
		CountryCode: 840,
		IP:          net.ParseIP("10.1.2.3").To4(),
	}
	c.Idle.Store(true)
	c.WiFi.Store(true)
	hub.Register(c)
	waitFor(t, func() bool { _, ok := hub.Get(7); return ok })

	cache := NewNodeCache()
	cache.Update(7, true, true, 840, c.IP)
	d := NewDispatcher(hub, cache, 2)
	d.Start(ctx)

	payload := []byte("job-1")
	env := Envelope{
		CountryCode: 840,
		Network:     net.ParseIP("10.1.0.0").To4(),
		IPMask:      net.CIDRMask(16, 32),
		Payload:     payload,
	}
	if err := d.Dispatch(env); err != nil {
		t.Fatal(err)
	}
	select {
	case got := <-c.Send:
		if string(got) != "job-1" {
			t.Fatalf("payload %q", got)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timeout waiting for dispatch")
	}
}

func TestDispatcherNonBlockingFull(t *testing.T) {
	hub := NewConnectionHub(NewStubStore())
	d := NewDispatcher(hub, NewNodeCache(), 1)
	// Fill route channel
	for i := 0; i < cap(d.routes); i++ {
		d.routes <- Envelope{}
	}
	if err := d.Dispatch(Envelope{}); err != ErrDispatchFull {
		t.Fatalf("want ErrDispatchFull got %v", err)
	}
}

func TestTrySendNonBlocking(t *testing.T) {
	d := NewDispatcher(nil, nil, 1)
	c := &Client{Send: make(chan []byte, 1)}
	c.Send <- []byte("full")
	if d.trySend(c, []byte("drop")) {
		t.Fatal("expected non-blocking drop")
	}
}

func TestMatchIPMask(t *testing.T) {
	ip := net.ParseIP("192.168.10.5").To4()
	network := net.ParseIP("192.168.0.0").To4()
	mask := net.CIDRMask(16, 32)
	if !matchIPMask(ip, network, mask) {
		t.Fatal("expected match")
	}
	if matchIPMask(ip, net.ParseIP("10.0.0.0").To4(), mask) {
		t.Fatal("expected miss")
	}
}

func waitFor(t *testing.T, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if cond() {
			return
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatal("condition timeout")
}
