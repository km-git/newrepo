package edgecoordinator

import (
	"bytes"
	"testing"
)

func TestTelemetryRoundTrip(t *testing.T) {
	in := Telemetry{NodeID: 0xDEADBEEFCAFEBABE, Battery: 87, WiFi: true, CountryCode: 840}
	b, err := in.MarshalBinary()
	if err != nil {
		t.Fatal(err)
	}
	if len(b) != TelemetrySize {
		t.Fatalf("size=%d want %d", len(b), TelemetrySize)
	}
	var out Telemetry
	if err := out.UnmarshalBinary(b); err != nil {
		t.Fatal(err)
	}
	if out != in {
		t.Fatalf("got %+v want %+v", out, in)
	}
}

func TestTelemetryPackUnpack(t *testing.T) {
	in := &Telemetry{NodeID: 42, Battery: 10, WiFi: false, CountryCode: 826}
	var buf bytes.Buffer
	if err := PackTelemetry(in, &buf); err != nil {
		t.Fatal(err)
	}
	out, err := UnpackTelemetry(&buf)
	if err != nil {
		t.Fatal(err)
	}
	if *out != *in {
		t.Fatalf("got %+v want %+v", out, in)
	}
}

func TestTelemetryTruncated(t *testing.T) {
	var tlm Telemetry
	if err := tlm.UnmarshalBinary([]byte{1, 2, 3}); err != ErrTelemetryTruncated {
		t.Fatalf("want ErrTelemetryTruncated got %v", err)
	}
}
