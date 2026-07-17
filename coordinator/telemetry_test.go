package coordinator

import (
	"net"
	"testing"
	"time"
)

func TestPackUnpackTelemetryRoundTrip(t *testing.T) {
	in := DeviceStats{
		NodeID:      "node-abc-123",
		BatteryPct:  87,
		WiFi:        true,
		CountryCode: "US",
	}
	blob, err := PackTelemetry(in)
	if err != nil {
		t.Fatalf("pack: %v", err)
	}
	if len(blob) > 80 {
		t.Fatalf("expected compact blob, got %d bytes", len(blob))
	}
	out, err := UnpackTelemetry(blob)
	if err != nil {
		t.Fatalf("unpack: %v", err)
	}
	if out != in {
		t.Fatalf("round-trip mismatch: %+v vs %+v", in, out)
	}
}

func TestHubRegisterUnregister(t *testing.T) {
	h := NewHub()
	defer h.Stop()

	c := &Client{NodeID: "n1", Idle: true, WiFi: true, CountryCode: "DE"}
	h.Register(c)
	if h.Len() != 1 {
		t.Fatalf("expected 1 client, got %d", h.Len())
	}
	h.Unregister(c)
	if h.Len() != 0 {
		t.Fatalf("expected 0 clients after unregister")
	}
}

func TestHubCleanupDropsStaleConnections(t *testing.T) {
	h := &Hub{
		clients:    make(map[string]*Client),
		staleAfter: 50 * time.Millisecond,
		stopCh:     make(chan struct{}),
	}
	c := &Client{NodeID: "stale"}
	c.lastSeen = time.Now().Add(-time.Second)
	h.clients[c.NodeID] = c

	h.dropStale()
	if h.Len() != 0 {
		t.Fatalf("stale client should be removed")
	}
}

func TestRouteIdleWiFiNodesFiltersAndDispatches(t *testing.T) {
	h := NewHub()
	defer h.Stop()

	match := &Client{
		NodeID:      "match",
		CountryCode: "US",
		IP:          net.ParseIP("10.1.2.3"),
		Idle:        true,
		WiFi:        true,
		send:        make(chan []byte, 1),
	}
	skip := &Client{
		NodeID:      "skip",
		CountryCode: "US",
		IP:          net.ParseIP("10.1.2.3"),
		Idle:        false,
		WiFi:        true,
		send:        make(chan []byte, 1),
	}
	h.Register(match)
	h.Register(skip)

	mask := net.CIDRMask(24, 32)
	report := h.RouteIdleWiFiNodes(RouteRequest{
		CountryCode: "US",
		TargetIP:    net.ParseIP("10.1.2.0"),
		IPMask:      mask,
		Payload:     []byte{0x01, 0x02},
	})
	if report.Matched != 1 || report.Sent != 1 {
		t.Fatalf("expected 1 match and 1 send, got %+v", report)
	}
	select {
	case got := <-match.send:
		if len(got) != 2 || got[0] != 0x01 {
			t.Fatalf("unexpected payload: %v", got)
		}
	default:
		t.Fatalf("payload not delivered")
	}
}

func TestIPMatchesMask(t *testing.T) {
	ip := net.ParseIP("192.168.1.44")
	network := net.ParseIP("192.168.1.0")
	mask := net.CIDRMask(24, 32)
	if !ipMatchesMask(ip, network, mask) {
		t.Fatalf("expected /24 match")
	}
	if ipMatchesMask(net.ParseIP("192.168.2.1"), network, mask) {
		t.Fatalf("expected /24 mismatch")
	}
}
