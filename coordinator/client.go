package coordinator

import (
	"net"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// Default WebSocket buffer sizes tuned for high fan-out without per-connection bloat.
const (
	ReadBufferSize  = 4096
	WriteBufferSize = 4096
	sendChannelCap  = 64
)

// Client is one mobile edge node connection managed by the hub.
type Client struct {
	NodeID      string
	CountryCode string
	IP          net.IP
	BatteryPct  uint8
	WiFi        bool
	Idle        bool

	conn     *websocket.Conn
	send     chan []byte
	lastSeen time.Time

	mu sync.Mutex
}

func newClient(conn *websocket.Conn, nodeID string) *Client {
	return &Client{
		NodeID:   nodeID,
		conn:     conn,
		send:     make(chan []byte, sendChannelCap),
		lastSeen: time.Now(),
		Idle:     true,
	}
}

func (c *Client) touch() {
	c.mu.Lock()
	c.lastSeen = time.Now()
	c.mu.Unlock()
}

func (c *Client) lastActivity() time.Time {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.lastSeen
}

func (c *Client) trySend(payload []byte) bool {
	select {
	case c.send <- payload:
		return true
	default:
		return false
	}
}

func (c *Client) close() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.conn != nil {
		_ = c.conn.Close()
	}
}
