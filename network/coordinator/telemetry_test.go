package coordinator

import (
	"testing"
)

func TestPackUnpackTelemetry(t *testing.T) {
	in := DeviceStats{
		NodeID:  "edge-device-001",
		Battery: 73,
		OnWiFi:  true,
		Idle:    true,
		Country: "us",
	}
	buf, err := PackTelemetry(in)
	if err != nil {
		t.Fatal(err)
	}
	if len(buf) != TelemetrySize {
		t.Fatalf("size=%d want %d", len(buf), TelemetrySize)
	}
	out, err := UnpackTelemetry(buf)
	if err != nil {
		t.Fatal(err)
	}
	if out.NodeID != in.NodeID {
		t.Fatalf("id=%q", out.NodeID)
	}
	if out.Battery != 73 || !out.OnWiFi || !out.Idle {
		t.Fatalf("flags=%+v", out)
	}
	if out.Country != "US" {
		t.Fatalf("country=%q", out.Country)
	}
}

func TestPackTelemetryBatteryRange(t *testing.T) {
	_, err := PackTelemetry(DeviceStats{NodeID: "x", Battery: 101})
	if err == nil {
		t.Fatal("expected battery error")
	}
}

func TestUnpackTelemetryShort(t *testing.T) {
	_, err := UnpackTelemetry([]byte{1, 2, 3})
	if err != ErrTelemetryShort {
		t.Fatalf("err=%v", err)
	}
}

func TestTelemetrySmallerThanJSON(t *testing.T) {
	buf, err := PackTelemetry(DeviceStats{
		NodeID: "node-ABCDEF123456", Battery: 50, OnWiFi: true, Idle: false, Country: "DE",
	})
	if err != nil {
		t.Fatal(err)
	}
	// Equivalent JSON is far larger than 28 bytes.
	jsonApprox := len(`{"node_id":"node-ABCDEF123456","battery":50,"wifi":true,"idle":false,"country":"DE"}`)
	if len(buf) >= jsonApprox {
		t.Fatalf("binary %d not smaller than json ~%d", len(buf), jsonApprox)
	}
}
