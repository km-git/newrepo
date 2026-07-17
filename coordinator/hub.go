package coordinator

import (
	"sync"
	"time"
)

const defaultStaleAfter = 45 * time.Second

// Hub manages active mobile node WebSocket connections with concurrent-safe access.
type Hub struct {
	mu      sync.RWMutex
	clients map[string]*Client

	staleAfter time.Duration
	stopCh     chan struct{}
}

// NewHub creates a connection hub and starts the silent-socket cleanup ticker.
func NewHub() *Hub {
	h := &Hub{
		clients:    make(map[string]*Client),
		staleAfter: defaultStaleAfter,
		stopCh:     make(chan struct{}),
	}
	go h.cleanupLoop()
	return h
}

// Register adds or replaces a live client connection.
func (h *Hub) Register(c *Client) {
	h.mu.Lock()
	if old, ok := h.clients[c.NodeID]; ok && old != c {
		old.close()
	}
	h.clients[c.NodeID] = c
	h.mu.Unlock()
}

// Unregister removes a client if it is still the active registration.
func (h *Hub) Unregister(c *Client) {
	h.mu.Lock()
	if cur, ok := h.clients[c.NodeID]; ok && cur == c {
		delete(h.clients, c.NodeID)
	}
	h.mu.Unlock()
}

// Get returns a client by node id.
func (h *Hub) Get(nodeID string) (*Client, bool) {
	h.mu.RLock()
	c, ok := h.clients[nodeID]
	h.mu.RUnlock()
	return c, ok
}

// Snapshot returns a shallow copy of all registered clients.
func (h *Hub) Snapshot() []*Client {
	h.mu.RLock()
	out := make([]*Client, 0, len(h.clients))
	for _, c := range h.clients {
		out = append(out, c)
	}
	h.mu.RUnlock()
	return out
}

// Len returns the number of active connections.
func (h *Hub) Len() int {
	h.mu.RLock()
	n := len(h.clients)
	h.mu.RUnlock()
	return n
}

// Stop shuts down the background cleanup goroutine.
func (h *Hub) Stop() {
	close(h.stopCh)
}

func (h *Hub) cleanupLoop() {
	ticker := time.NewTicker(h.staleAfter)
	defer ticker.Stop()

	for {
		select {
		case <-h.stopCh:
			return
		case <-ticker.C:
			h.dropStale()
		}
	}
}

func (h *Hub) dropStale() {
	now := time.Now()
	var stale []*Client

	h.mu.Lock()
	for id, c := range h.clients {
		if now.Sub(c.lastActivity()) >= h.staleAfter {
			delete(h.clients, id)
			stale = append(stale, c)
		}
	}
	h.mu.Unlock()

	for _, c := range stale {
		c.close()
	}
}
