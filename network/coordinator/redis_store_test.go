package coordinator

import (
	"context"
	"testing"
	"time"
)

func TestMemoryStateStoreO1(t *testing.T) {
	store := NewMemoryStateStore()
	c := &ClientConn{
		ID: "r1", Country: "NL", IP: "10.9.8.7",
		OnWiFi: true, Idle: false, Battery: 40, LastSeen: time.Now().UTC(),
	}
	if err := store.PutNode(c); err != nil {
		t.Fatal(err)
	}
	got, err := store.GetNode("r1")
	if err != nil {
		t.Fatal(err)
	}
	if got.Country != "NL" || got.IP != "10.9.8.7" {
		t.Fatalf("%+v", got)
	}
	if err := store.Ping(context.Background()); err != nil {
		t.Fatal(err)
	}
	_ = store.DeleteNode("r1")
	if _, err := store.GetNode("r1"); err == nil {
		t.Fatal("expected miss")
	}
}

func TestHubWithStateStore(t *testing.T) {
	store := NewMemoryStateStore()
	h := NewHub(WithStateStore(store))
	h.Register(&ClientConn{ID: "s1", Country: "IT", IP: "1.1.1.1", OnWiFi: true, Idle: true})
	got, err := store.GetNode("s1")
	if err != nil || got.Country != "IT" {
		t.Fatalf("store mirror failed: %v %+v", err, got)
	}
	h.Unregister("s1")
	if _, err := store.GetNode("s1"); err == nil {
		t.Fatal("expected delete from store")
	}
}
