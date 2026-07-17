package coordinator

import (
	"fmt"
	"sync"
	"testing"
	"time"
)

func TestHubRegisterGetUnregister(t *testing.T) {
	h := NewHub()
	c := &ClientConn{
		ID: "node-1", Country: "US", IP: "10.0.0.1",
		OnWiFi: true, Idle: true, Battery: 80,
	}
	h.Register(c)
	if h.Len() != 1 {
		t.Fatalf("len=%d want 1", h.Len())
	}
	got, ok := h.Get("node-1")
	if !ok || got.Country != "US" {
		t.Fatalf("get failed: ok=%v got=%v", ok, got)
	}
	h.Unregister("node-1")
	if h.Len() != 0 {
		t.Fatalf("len after unregister=%d", h.Len())
	}
}

func TestHubDropSilent(t *testing.T) {
	h := NewHub(WithSilentTimeout(45 * time.Second))
	alive := &ClientConn{ID: "alive", Country: "DE", LastSeen: time.Now().UTC(), Send: make(chan []byte, 1)}
	stale := &ClientConn{ID: "stale", Country: "DE", LastSeen: time.Now().UTC().Add(-2 * time.Minute), Send: make(chan []byte, 1)}
	h.Register(alive)
	h.Register(stale)
	n := h.DropSilent(time.Now().UTC())
	if n != 1 {
		t.Fatalf("dropped=%d want 1", n)
	}
	if _, ok := h.Get("stale"); ok {
		t.Fatal("stale still present")
	}
	if _, ok := h.Get("alive"); !ok {
		t.Fatal("alive missing")
	}
}

func TestHubCleanupTicker(t *testing.T) {
	h := NewHub(
		WithCleanupInterval(20*time.Millisecond),
		WithSilentTimeout(30*time.Millisecond),
	)
	h.Register(&ClientConn{
		ID: "gone", Country: "FR",
		LastSeen: time.Now().UTC().Add(-time.Second),
		Send:     make(chan []byte, 1),
	})
	h.StartCleanup()
	defer h.StopCleanup()

	deadline := time.Now().Add(500 * time.Millisecond)
	for time.Now().Before(deadline) {
		if h.Len() == 0 {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("cleanup did not drop silent socket, len=%d", h.Len())
}

func TestHubConcurrentRegister(t *testing.T) {
	h := NewHub()
	var wg sync.WaitGroup
	const n = 200
	wg.Add(n)
	for i := 0; i < n; i++ {
		i := i
		go func() {
			defer wg.Done()
			id := NodeID(fmt.Sprintf("n-%d", i))
			h.Register(&ClientConn{
				ID: id, Country: "US", IP: "10.0.0.2",
				OnWiFi: true, Idle: true, Send: make(chan []byte, 1),
			})
			_, _ = h.Get(id)
		}()
	}
	wg.Wait()
	if h.Len() == 0 {
		t.Fatal("expected registrations")
	}
}

func TestMatchIdleWiFi(t *testing.T) {
	h := NewHub()
	h.Register(&ClientConn{ID: "a", Country: "US", IP: "10.1.2.3", OnWiFi: true, Idle: true, Send: make(chan []byte, 1)})
	h.Register(&ClientConn{ID: "b", Country: "US", IP: "10.1.2.4", OnWiFi: false, Idle: true, Send: make(chan []byte, 1)})
	h.Register(&ClientConn{ID: "c", Country: "GB", IP: "10.1.2.5", OnWiFi: true, Idle: true, Send: make(chan []byte, 1)})
	h.Register(&ClientConn{ID: "d", Country: "US", IP: "192.168.0.1", OnWiFi: true, Idle: true, Send: make(chan []byte, 1)})

	mask, err := ParseIPMask("10.1.2.0/24")
	if err != nil {
		t.Fatal(err)
	}
	got := h.MatchIdleWiFi("US", mask)
	if len(got) != 1 || got[0].ID != "a" {
		t.Fatalf("match=%v", got)
	}
}
