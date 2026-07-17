package edgecoordinator

import (
	"context"
	"testing"
	"time"
)

func TestHubRegisterUnregister(t *testing.T) {
	store := NewStubStore()
	hub := NewConnectionHub(store)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go hub.Run(ctx)

	c := &Client{
		NodeID: 1,
		Send:   make(chan []byte, 4),
		Conn:   nil,
	}
	// Direct add via channel path
	hub.Register(c)
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if _, ok := hub.Get(1); ok {
			break
		}
		time.Sleep(5 * time.Millisecond)
	}
	if _, ok := hub.Get(1); !ok {
		t.Fatal("client not registered")
	}
	if hub.Len() != 1 {
		t.Fatalf("len=%d", hub.Len())
	}
	hub.Unregister(1)
	deadline = time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if _, ok := hub.Get(1); !ok {
			return
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatal("client still registered")
}

func TestHubCleanupIdle(t *testing.T) {
	hub := NewConnectionHub(NewStubStore())
	c := &Client{
		NodeID: 99,
		Send:   make(chan []byte, 1),
	}
	c.LastSeen.Store(time.Now().Add(-2 * IdleTimeout).UnixNano())
	hub.mu.Lock()
	hub.clients[99] = c
	hub.mu.Unlock()
	hub.cleanupIdle()
	if _, ok := hub.Get(99); ok {
		t.Fatal("stale client should be removed")
	}
}
