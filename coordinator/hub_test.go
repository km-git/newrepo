package coordinator

import (
	"context"
	"sync"
	"testing"
	"time"
)

func TestHubRegisterLookupUnregister(t *testing.T) {
	h := NewHub(NewMemoryRedis())
	c := NewClient(h, nil, "node-1", "US", "10.0.0.0/8")
	h.Register(c)
	if h.Len() != 1 {
		t.Fatalf("len=%d want 1", h.Len())
	}
	got, ok := h.Lookup("node-1")
	if !ok || got != c {
		t.Fatal("lookup failed")
	}
	c.Close()
	if h.Len() != 0 {
		t.Fatalf("after close len=%d", h.Len())
	}
}

func TestHubDropSilentAfter45s(t *testing.T) {
	h := NewHub(nil)
	c := NewClient(h, nil, "quiet", "DE", "192.168.1.10")
	c.lastPong.Store(time.Now().Add(-SilentTimeout - time.Second).UnixNano())
	h.Register(c)

	n := h.DropSilent(time.Now())
	if n != 1 {
		t.Fatalf("dropped=%d want 1", n)
	}
	if h.Len() != 0 {
		t.Fatalf("hub still has %d clients", h.Len())
	}
}

func TestHubCleanupTicker(t *testing.T) {
	h := NewHub(nil)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Short-circuit: manually call DropSilent path via StartCleanup with silent client.
	c := NewClient(h, nil, "tick", "FR", "10.1.2.3")
	c.lastPong.Store(time.Now().Add(-2 * SilentTimeout).UnixNano())
	h.Register(c)

	// Don't wait 45s in tests — exercise DropSilent directly (ticker uses same method).
	if h.DropSilent(time.Now()) != 1 {
		t.Fatal("expected silent drop")
	}
	h.StartCleanup(ctx)
	h.StopCleanup()
}

func TestConcurrentRegister(t *testing.T) {
	h := NewHub(NewMemoryRedis())
	var wg sync.WaitGroup
	const N = 200
	wg.Add(N)
	for i := 0; i < N; i++ {
		i := i
		go func() {
			defer wg.Done()
			c := NewClient(h, nil, "node-"+itoa(i), "US", "10.0.0.0/8")
			h.Register(c)
		}()
	}
	wg.Wait()
	if h.Len() != N {
		t.Fatalf("len=%d want %d", h.Len(), N)
	}
}

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	var b [16]byte
	pos := len(b)
	for i > 0 {
		pos--
		b[pos] = byte('0' + i%10)
		i /= 10
	}
	return string(b[pos:])
}
