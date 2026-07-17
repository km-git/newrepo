package edgecoordinator

import (
	"context"
	"testing"
)

func TestStubStoreRoundTrip(t *testing.T) {
	s := NewStubStore()
	st := NodeState{Battery: 55, WiFi: true, Idle: true, CountryCode: 840, LastSeen: 123}
	if err := s.SetNode(context.Background(), 1, st); err != nil {
		t.Fatal(err)
	}
	got, err := s.GetNode(context.Background(), 1)
	if err != nil {
		t.Fatal(err)
	}
	if got != st {
		t.Fatalf("got %+v want %+v", got, st)
	}
	batch, err := s.MGetNodes(context.Background(), []uint64{1, 2})
	if err != nil {
		t.Fatal(err)
	}
	if batch[0] != st {
		t.Fatalf("batch[0]=%+v", batch[0])
	}
	if err := s.Ping(context.Background()); err != nil {
		t.Fatal(err)
	}
}

func TestEncodeDecodeState(t *testing.T) {
	st := NodeState{Battery: 99, WiFi: false, Idle: true, CountryCode: 44, LastSeen: -1}
	raw := encodeState(st)
	got, err := decodeState(raw)
	if err != nil {
		t.Fatal(err)
	}
	// LastSeen encoded as uint64 bit pattern
	if got.Battery != st.Battery || got.WiFi != st.WiFi || got.Idle != st.Idle || got.CountryCode != st.CountryCode {
		t.Fatalf("got %+v want %+v", got, st)
	}
}
