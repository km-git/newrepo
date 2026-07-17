package coordinator

import (
	"net"
	"net/http"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

// Optimized WebSocket buffer sizes — large enough for telemetry bursts,
// small enough to bound RAM across millions of concurrent sockets.
const (
	WSReadBufferSize  = 1024
	WSWriteBufferSize = 1024
	WSWriteQueueSize  = 64
	MaxMessageSize    = 4096
)

// Client is a connected mobile edge node.
type Client struct {
	NodeID      string
	CountryCode string
	IPMask      string // CIDR or dotted prefix used for dispatch matching
	BatteryPct  uint8
	OnWiFi      bool
	Idle        bool

	conn     *websocket.Conn
	send     chan []byte
	hub      *Hub
	lastPong atomic.Int64 // unix nano of last pong / activity

	mu     sync.Mutex
	closed bool
}

// NewClient wraps a websocket connection with a bounded send queue.
func NewClient(hub *Hub, conn *websocket.Conn, nodeID, country, ipMask string) *Client {
	if conn != nil {
		conn.SetReadLimit(MaxMessageSize)
		_ = conn.SetReadDeadline(time.Now().Add(SilentTimeout))
		conn.SetPongHandler(func(string) error {
			_ = conn.SetReadDeadline(time.Now().Add(SilentTimeout))
			return nil
		})
	}
	c := &Client{
		NodeID:      nodeID,
		CountryCode: country,
		IPMask:      ipMask,
		conn:        conn,
		send:        make(chan []byte, WSWriteQueueSize),
		hub:         hub,
		Idle:        true,
	}
	c.Touch()
	return c
}

// Touch records recent activity (pong / telemetry / message).
func (c *Client) Touch() {
	c.lastPong.Store(time.Now().UnixNano())
}

// LastSeen returns the last activity timestamp.
func (c *Client) LastSeen() time.Time {
	return time.Unix(0, c.lastPong.Load())
}

// IsSilent reports whether the socket has been quiet longer than SilentTimeout.
func (c *Client) IsSilent(now time.Time) bool {
	return now.Sub(c.LastSeen()) > SilentTimeout
}

// MatchesIP reports whether the client's IP is covered by want (CIDR or exact).
func (c *Client) MatchesIP(want string) bool {
	if want == "" || c.IPMask == "" {
		return want == c.IPMask
	}
	if c.IPMask == want {
		return true
	}
	wantNet, err := parseIPNet(want)
	if err != nil {
		return false
	}
	haveIP, err := parseHostIP(c.IPMask)
	if err != nil {
		return false
	}
	return wantNet.Contains(haveIP)
}

func parseIPNet(s string) (*net.IPNet, error) {
	_, n, err := net.ParseCIDR(s)
	if err == nil {
		return n, nil
	}
	ip := net.ParseIP(s)
	if ip == nil {
		return nil, err
	}
	if ip.To4() != nil {
		return &net.IPNet{IP: ip.To4(), Mask: net.CIDRMask(32, 32)}, nil
	}
	return &net.IPNet{IP: ip, Mask: net.CIDRMask(128, 128)}, nil
}

func parseHostIP(s string) (net.IP, error) {
	if ip, _, err := net.ParseCIDR(s); err == nil {
		return ip, nil
	}
	ip := net.ParseIP(s)
	if ip == nil {
		return nil, &net.ParseError{Type: "IP address", Text: s}
	}
	return ip, nil
}

// TrySend enqueues a payload without blocking the caller.
// Returns false if the queue is full or the client is closed.
func (c *Client) TrySend(payload []byte) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.closed {
		return false
	}
	select {
	case c.send <- payload:
		return true
	default:
		return false
	}
}

// Close tears down the client and unregisters from the hub.
func (c *Client) Close() {
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return
	}
	c.closed = true
	close(c.send)
	if c.conn != nil {
		_ = c.conn.Close()
	}
	c.mu.Unlock()
	if c.hub != nil {
		c.hub.Unregister(c)
	}
}

// DefaultUpgrader uses optimized buffer sizes to limit per-connection memory.
var DefaultUpgrader = websocket.Upgrader{
	ReadBufferSize:    WSReadBufferSize,
	WriteBufferSize:   WSWriteBufferSize,
	EnableCompression: false, // binary telemetry is already compact
	CheckOrigin:       func(r *http.Request) bool { return true },
}
