package coordinator

import (
	"encoding/json"
	"testing"
)

func TestPackUnpackTelemetry(t *testing.T) {
	in := Telemetry{
		NodeID:      "edge-42",
		BatteryPct:  87,
		OnWiFi:      true,
		CountryCode: "US",
	}
	bin, err := PackTelemetry(in)
	if err != nil {
		t.Fatal(err)
	}
	out, err := UnpackTelemetry(bin)
	if err != nil {
		t.Fatal(err)
	}
	if out != in {
		t.Fatalf("got %+v want %+v", out, in)
	}
}

func TestTelemetrySmallerThanJSON(t *testing.T) {
	in := Telemetry{NodeID: "n1", BatteryPct: 50, OnWiFi: true, CountryCode: "DE"}
	bin, err := PackTelemetry(in)
	if err != nil {
		t.Fatal(err)
	}
	js, _ := json.Marshal(in)
	if len(bin) >= len(js) {
		t.Fatalf("binary=%d json=%d — binary should be tighter", len(bin), len(js))
	}
}

func TestUnpackCorrupt(t *testing.T) {
	_, err := UnpackTelemetry([]byte{1, 2, 3})
	if err != ErrTelemetryCorrupt {
		t.Fatalf("err=%v", err)
	}
}

func TestHubUpdateTelemetry(t *testing.T) {
	h := NewHub(NewMemoryRedis())
	c := NewClient(h, nil, "t1", "US", "10.0.0.1")
	h.Register(c)
	ok := h.UpdateTelemetry(Telemetry{NodeID: "t1", BatteryPct: 10, OnWiFi: true, CountryCode: "CA"})
	if !ok {
		t.Fatal("update failed")
	}
	if c.BatteryPct != 10 || !c.OnWiFi || c.CountryCode != "CA" {
		t.Fatalf("client=%+v", c)
	}
}
