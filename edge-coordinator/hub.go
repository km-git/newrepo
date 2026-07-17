// Package edgecoordinator is a high-concurrency network coordinator for
// routing traffic across millions of mobile edge devices.
package edgecoordinator

import (
	"context"
	"net"
	"net/http"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

const (
	// IdleTimeout drops silent sockets to reclaim RAM under load.
	IdleTimeout = 45 * time.Second
	// SendBufferSize is the per-client outbound queue depth.
	SendBufferSize = 64
	// ReadBufferSize / WriteBufferSize tune gorilla/websocket to limit allocs.
	ReadBufferSize  = 4096
	WriteBufferSize = 4096
)

// Client is one connected mobile edge node.
type Client struct {
	NodeID      uint64
	Conn        *websocket.Conn
	Send        chan []byte
	CountryCode uint16
	IP          net.IP
	LastSeen    atomic.Int64
	Idle        atomic.Bool
	WiFi        atomic.Bool
	hub         *ConnectionHub
	closeOnce   sync.Once
}

// close tears down the send channel and socket at most once.
func (c *Client) close() {
	c.closeOnce.Do(func() {
		close(c.Send)
		if c.Conn != nil {
			_ = c.Conn.Close()
		}
	})
}

// touch updates LastSeen for the idle cleanup ticker.
func (c *Client) touch() {
	c.LastSeen.Store(time.Now().UnixNano())
}

// ConnectionHub manages the active WebSocket client map with RWMutex safety.
type ConnectionHub struct {
	mu       sync.RWMutex
	clients  map[uint64]*Client
	register chan *Client
	unregister chan uint64
	state    StateStore
	upgrader websocket.Upgrader
	done     chan struct{}
}

// NewConnectionHub builds a hub backed by the given StateStore (Redis or stub).
func NewConnectionHub(store StateStore) *ConnectionHub {
	return &ConnectionHub{
		clients:    make(map[uint64]*Client),
		register:   make(chan *Client, 1024),
		unregister: make(chan uint64, 1024),
		state:      store,
		upgrader: websocket.Upgrader{
			ReadBufferSize:    ReadBufferSize,
			WriteBufferSize:   WriteBufferSize,
			EnableCompression: false, // avoid per-message zlib alloc storms
			CheckOrigin:       func(r *http.Request) bool { return true },
		},
		done: make(chan struct{}),
	}
}

// Run owns map mutations via register/unregister channels and the 45s cleanup ticker.
func (h *ConnectionHub) Run(ctx context.Context) {
	ticker := time.NewTicker(IdleTimeout)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			close(h.done)
			return
		case c := <-h.register:
			h.addClient(c)
		case id := <-h.unregister:
			h.removeClient(id)
		case <-ticker.C:
			h.cleanupIdle()
		}
	}
}

func (h *ConnectionHub) addClient(c *Client) {
	h.mu.Lock()
	if old, ok := h.clients[c.NodeID]; ok {
		delete(h.clients, c.NodeID)
		h.mu.Unlock()
		old.close()
		h.mu.Lock()
	}
	c.hub = h
	c.touch()
	h.clients[c.NodeID] = c
	h.mu.Unlock()
}

func (h *ConnectionHub) removeClient(id uint64) {
	h.mu.Lock()
	c, ok := h.clients[id]
	if ok {
		delete(h.clients, id)
	}
	h.mu.Unlock()
	if !ok {
		return
	}
	c.close()
}

// Register queues a client onto the hub event loop (non-blocking for callers that
// already hold the client pointer; Run applies the map write).
func (h *ConnectionHub) Register(c *Client) {
	select {
	case h.register <- c:
	case <-h.done:
	}
}

// Unregister queues removal by node ID.
func (h *ConnectionHub) Unregister(id uint64) {
	select {
	case h.unregister <- id:
	case <-h.done:
	}
}

// Get returns a client under a read lock for O(1) concurrent lookups.
func (h *ConnectionHub) Get(id uint64) (*Client, bool) {
	h.mu.RLock()
	c, ok := h.clients[id]
	h.mu.RUnlock()
	return c, ok
}

// Len returns the number of active connections (RLock).
func (h *ConnectionHub) Len() int {
	h.mu.RLock()
	n := len(h.clients)
	h.mu.RUnlock()
	return n
}

// SnapshotIDs returns all node IDs under RLock (for tests / admin).
func (h *ConnectionHub) SnapshotIDs() []uint64 {
	h.mu.RLock()
	ids := make([]uint64, 0, len(h.clients))
	for id := range h.clients {
		ids = append(ids, id)
	}
	h.mu.RUnlock()
	return ids
}

// cleanupIdle drops silent, non-responsive sockets every IdleTimeout.
func (h *ConnectionHub) cleanupIdle() {
	cutoff := time.Now().Add(-IdleTimeout).UnixNano()
	var stale []uint64
	h.mu.RLock()
	for id, c := range h.clients {
		if c.LastSeen.Load() < cutoff {
			stale = append(stale, id)
		}
	}
	h.mu.RUnlock()
	for _, id := range stale {
		h.removeClient(id)
	}
}

// ServeWS upgrades an HTTP request to a WebSocket and registers the node.
// Query: node_id (required), country (uint16), ip (optional override).
func (h *ConnectionHub) ServeWS(w http.ResponseWriter, r *http.Request) {
	nodeID, err := parseUint64Query(r, "node_id")
	if err != nil || nodeID == 0 {
		http.Error(w, "node_id required", http.StatusBadRequest)
		return
	}
	country, _ := parseUint16Query(r, "country")
	conn, err := h.upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	ip := net.ParseIP(r.URL.Query().Get("ip"))
	if ip == nil {
		host, _, _ := net.SplitHostPort(r.RemoteAddr)
		ip = net.ParseIP(host)
	}
	c := &Client{
		NodeID:      nodeID,
		Conn:        conn,
		Send:        make(chan []byte, SendBufferSize),
		CountryCode: country,
		IP:          ip,
	}
	c.Idle.Store(true)
	c.WiFi.Store(true)
	h.Register(c)
	go c.writePump()
	go c.readPump()
}

func (c *Client) readPump() {
	defer func() {
		if c.hub != nil {
			c.hub.Unregister(c.NodeID)
		}
	}()
	_ = c.Conn.SetReadDeadline(time.Now().Add(IdleTimeout))
	c.Conn.SetPongHandler(func(string) error {
		c.touch()
		return c.Conn.SetReadDeadline(time.Now().Add(IdleTimeout))
	})
	for {
		_, data, err := c.Conn.ReadMessage()
		if err != nil {
			return
		}
		c.touch()
		if len(data) >= TelemetrySize {
			var t Telemetry
			if err := t.UnmarshalBinary(data); err == nil {
				c.CountryCode = t.CountryCode
				c.WiFi.Store(t.WiFi)
				if c.hub != nil && c.hub.state != nil {
					_ = c.hub.state.SetNode(context.Background(), c.NodeID, NodeState{
						Battery:     t.Battery,
						WiFi:        t.WiFi,
						Idle:        c.Idle.Load(),
						CountryCode: t.CountryCode,
						LastSeen:    c.LastSeen.Load(),
					})
				}
			}
		}
	}
}

func (c *Client) writePump() {
	ping := time.NewTicker(IdleTimeout / 3)
	defer func() {
		ping.Stop()
		_ = c.Conn.Close()
	}()
	for {
		select {
		case msg, ok := <-c.Send:
			_ = c.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				_ = c.Conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}
			if err := c.Conn.WriteMessage(websocket.BinaryMessage, msg); err != nil {
				return
			}
		case <-ping.C:
			_ = c.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.Conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}
