package coordinator

import (
	"context"
	"io"
	"log"
	"net"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  ReadBufferSize,
	WriteBufferSize: WriteBufferSize,
	CheckOrigin: func(r *http.Request) bool { return true },
}

// Server wires the hub, optional Redis store, and HTTP/WebSocket handlers.
type Server struct {
	Hub   *Hub
	Store *NodeStore
	Addr  string
}

// NewServer creates a coordinator HTTP server.
func NewServer(addr string, store *NodeStore) *Server {
	return &Server{
		Hub:   NewHub(),
		Store: store,
		Addr:  addr,
	}
}

// Handler returns the root HTTP handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", s.handleHealth)
	mux.HandleFunc("/ws", s.handleWS)
	mux.HandleFunc("/route", s.handleRoute)
	return mux
}

// ListenAndServe starts the coordinator service.
func (s *Server) ListenAndServe() error {
	log.Printf("coordinator listening on %s", s.Addr)
	return http.ListenAndServe(s.Addr, s.Handler())
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ok"))
}

func (s *Server) handleRoute(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	country := r.URL.Query().Get("country")
	cidr := r.URL.Query().Get("cidr")
	maskStr := r.URL.Query().Get("mask")
	payload, _ := io.ReadAll(io.LimitReader(r.Body, 1<<20))

	var targetIP net.IP
	var mask net.IPMask
	if cidr != "" {
		ip, ipNet, err := net.ParseCIDR(cidr)
		if err == nil {
			targetIP = ip
			mask = ipNet.Mask
		}
	} else if maskStr != "" {
		if strings.Contains(maskStr, "/") {
			ip, ipNet, err := net.ParseCIDR(maskStr)
			if err == nil {
				targetIP = ip
				mask = ipNet.Mask
			}
		}
	}

	report := s.Hub.RouteIdleWiFiNodes(RouteRequest{
		CountryCode: strings.ToUpper(country),
		TargetIP:    targetIP,
		IPMask:      mask,
		Payload:     payload,
	})
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write([]byte("{\"matched\":" + strconv.Itoa(report.Matched) + ",\"sent\":" + strconv.Itoa(report.Sent) + "}"))
}

func (s *Server) handleWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}

	nodeID := r.URL.Query().Get("node_id")
	if nodeID == "" {
		nodeID = r.RemoteAddr
	}
	client := newClient(conn, nodeID)
	client.IP = net.ParseIP(strings.Split(r.RemoteAddr, ":")[0])
	client.CountryCode = strings.ToUpper(r.URL.Query().Get("country"))

	s.Hub.Register(client)
	if s.Store != nil {
		_ = s.Store.UpsertNode(r.Context(), client)
	}

	go s.writePump(client)
	s.readPump(client)
}

func (s *Server) readPump(c *Client) {
	defer func() {
		s.Hub.Unregister(c)
		if s.Store != nil {
			_ = s.Store.RemoveNode(context.Background(), c)
		}
		c.close()
	}()

	c.conn.SetReadLimit(1 << 20)
	_ = c.conn.SetReadDeadline(time.Now().Add(defaultStaleAfter))
	c.conn.SetPongHandler(func(string) error {
		c.touch()
		return c.conn.SetReadDeadline(time.Now().Add(defaultStaleAfter))
	})

	for {
		msgType, data, err := c.conn.ReadMessage()
		if err != nil {
			return
		}
		c.touch()
		if msgType == websocket.BinaryMessage {
			stats, err := UnpackTelemetry(data)
			if err != nil {
				continue
			}
			c.BatteryPct = stats.BatteryPct
			c.WiFi = stats.WiFi
			if stats.CountryCode != "" {
				c.CountryCode = stats.CountryCode
			}
			c.Idle = true
			if s.Store != nil {
				_ = s.Store.UpsertNode(context.Background(), c)
			}
		}
	}
}

func (s *Server) writePump(c *Client) {
	ticker := time.NewTicker(defaultStaleAfter / 2)
	defer ticker.Stop()

	for {
		select {
		case payload, ok := <-c.send:
			_ = c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				_ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}
			if err := c.conn.WriteMessage(websocket.BinaryMessage, payload); err != nil {
				return
			}
		case <-ticker.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

