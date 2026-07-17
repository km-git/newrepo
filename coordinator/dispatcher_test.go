package coordinator

import (
	"testing"
)

func TestDispatcherRouteIdleWiFi(t *testing.T) {
	redis := NewMemoryRedis()
	h := NewHub(redis)
	d := NewDispatcher(h)

	good := NewClient(h, nil, "good-1", "US", "10.0.0.5")
	good.OnWiFi = true
	good.Idle = true
	h.Register(good)

	busy := NewClient(h, nil, "busy-1", "US", "10.0.0.6")
	busy.OnWiFi = true
	busy.Idle = false
	h.Register(busy)

	cell := NewClient(h, nil, "cell-1", "US", "10.0.0.7")
	cell.OnWiFi = false
	cell.Idle = true
	h.Register(cell)

	other := NewClient(h, nil, "eu-1", "DE", "10.0.0.8")
	other.OnWiFi = true
	other.Idle = true
	h.Register(other)

	res, err := d.Route(EnterpriseRequest{
		CountryCode: "US",
		IPMask:      "10.0.0.0/24",
		Payload:     []byte("exec-job"),
	})
	if err != nil {
		t.Fatalf("route: %v", err)
	}
	if res.Matched != 1 || res.Delivered != 1 {
		t.Fatalf("result=%+v", res)
	}
	if res.NodeIDs[0] != "good-1" {
		t.Fatalf("nodes=%v", res.NodeIDs)
	}
	if good.Idle {
		t.Fatal("delivered node should be marked busy")
	}

	// Non-blocking: payload landed on channel
	select {
	case got := <-good.send:
		if string(got) != "exec-job" {
			t.Fatalf("payload=%q", got)
		}
	default:
		t.Fatal("expected payload on send channel")
	}
}

func TestDispatcherNoMatch(t *testing.T) {
	h := NewHub(nil)
	d := NewDispatcher(h)
	_, err := d.Route(EnterpriseRequest{
		CountryCode: "JP",
		IPMask:      "203.0.113.0/24",
		Payload:     []byte("x"),
	})
	if err != ErrNoMatchingNodes {
		t.Fatalf("err=%v", err)
	}
}

func TestDispatcherNonBlockingFullQueue(t *testing.T) {
	h := NewHub(nil)
	d := NewDispatcher(h)
	c := NewClient(h, nil, "full", "US", "192.0.2.10")
	c.OnWiFi = true
	c.Idle = true
	h.Register(c)

	// Fill the bounded send queue.
	for i := 0; i < WSWriteQueueSize; i++ {
		if !c.TrySend([]byte{byte(i)}) {
			t.Fatalf("prefill failed at %d", i)
		}
	}

	res, err := d.Route(EnterpriseRequest{
		CountryCode: "US",
		IPMask:      "192.0.2.0/24",
		Payload:     []byte("overflow"),
	})
	if err != ErrDispatchBlocked {
		t.Fatalf("err=%v res=%+v", err, res)
	}
}
