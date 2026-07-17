package coordinator

import (
	"net/http"
	"time"

	"github.com/gorilla/websocket"
)

const (
	// Tuned buffer sizes — large enough for binary telemetry bursts,
	// small enough to bound RAM under millions of concurrent sockets.
	wsReadBufferSize  = 1024
	wsWriteBufferSize = 1024
	wsWriteWait       = 10 * time.Second
	wsPongWait        = 60 * time.Second
	wsPingPeriod      = 30 * time.Second // must be < wsPongWait
	wsMaxMessageSize  = 4096
)

// Upgrader is a shared gorilla/websocket upgrader with leak-conscious buffers.
var Upgrader = websocket.Upgrader{
	ReadBufferSize:  wsReadBufferSize,
	WriteBufferSize: wsWriteBufferSize,
	CheckOrigin: func(r *http.Request) bool {
		// Edge devices may connect from arbitrary origins; tighten in gateway.
		return true
	},
}

// ServeWS upgrades an HTTP request to a WebSocket, registers the node on the hub,
// and runs read/write pumps until the socket goes silent or the peer disconnects.
func ServeWS(hub *Hub, w http.ResponseWriter, r *http.Request, node ClientConn) error {
	conn, err := Upgrader.Upgrade(w, r, nil)
	if err != nil {
		return err
	}

	client := &ClientConn{
		ID:       node.ID,
		Country:  node.Country,
		IP:       clientIP(r, node.IP),
		OnWiFi:   node.OnWiFi,
		Idle:     node.Idle,
		Battery:  node.Battery,
		LastSeen: time.Now().UTC(),
		Send:     make(chan []byte, DefaultSendBuffer),
	}
	hub.Register(client)

	go writePump(conn, client)
	readPump(hub, conn, client)
	return nil
}

func clientIP(r *http.Request, fallback string) string {
	if fallback != "" {
		return fallback
	}
	host := r.RemoteAddr
	return host
}

func readPump(hub *Hub, conn *websocket.Conn, c *ClientConn) {
	defer func() {
		hub.Unregister(c.ID)
		_ = conn.Close()
	}()

	conn.SetReadLimit(wsMaxMessageSize)
	_ = conn.SetReadDeadline(time.Now().Add(wsPongWait))
	conn.SetPongHandler(func(string) error {
		c.Touch()
		return conn.SetReadDeadline(time.Now().Add(wsPongWait))
	})

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			return
		}
		c.Touch()
		if stats, err := UnpackTelemetry(message); err == nil && stats.NodeID == c.ID {
			hub.UpdateFlags(c.ID, stats.OnWiFi, stats.Idle, stats.Battery, stats.Country)
		}
	}
}

func writePump(conn *websocket.Conn, c *ClientConn) {
	ticker := time.NewTicker(wsPingPeriod)
	defer func() {
		ticker.Stop()
		_ = conn.Close()
	}()

	for {
		select {
		case payload, ok := <-c.Send:
			_ = conn.SetWriteDeadline(time.Now().Add(wsWriteWait))
			if !ok {
				_ = conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}
			if err := conn.WriteMessage(websocket.BinaryMessage, payload); err != nil {
				return
			}
		case <-ticker.C:
			_ = conn.SetWriteDeadline(time.Now().Add(wsWriteWait))
			if err := conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}
