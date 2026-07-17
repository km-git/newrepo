package coordinator

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

// StateStore is the Redis Cluster (or compatible) interface for O(1) node state.
type StateStore interface {
	PutNode(c *ClientConn) error
	GetNode(id NodeID) (*ClientConn, error)
	DeleteNode(id NodeID) error
	Ping(ctx context.Context) error
	Close() error
}

// NodeState is the serialisable Redis value for a mobile node.
type NodeState struct {
	ID       string    `json:"id"`
	Country  string    `json:"cc"`
	IP       string    `json:"ip"`
	OnWiFi   bool      `json:"wifi"`
	Idle     bool      `json:"idle"`
	Battery  uint8     `json:"bat"`
	LastSeen time.Time `json:"seen"`
}

func nodeKey(id NodeID) string {
	return "edge:node:" + string(id)
}

// MemoryStateStore is an in-process O(1) fallback used when Redis is unavailable
// (tests, local dry-runs). Production should inject RedisClusterStore.
type MemoryStateStore struct {
	data map[NodeID]*NodeState
}

// NewMemoryStateStore creates an empty in-memory state store.
func NewMemoryStateStore() *MemoryStateStore {
	return &MemoryStateStore{data: make(map[NodeID]*NodeState)}
}

func (m *MemoryStateStore) PutNode(c *ClientConn) error {
	if c == nil {
		return fmt.Errorf("nil client")
	}
	m.data[c.ID] = &NodeState{
		ID:       string(c.ID),
		Country:  c.Country,
		IP:       c.IP,
		OnWiFi:   c.OnWiFi,
		Idle:     c.Idle,
		Battery:  c.Battery,
		LastSeen: c.LastSeen,
	}
	return nil
}

func (m *MemoryStateStore) GetNode(id NodeID) (*ClientConn, error) {
	st, ok := m.data[id]
	if !ok {
		return nil, fmt.Errorf("node %s not found", id)
	}
	return stateToClient(st), nil
}

func (m *MemoryStateStore) DeleteNode(id NodeID) error {
	delete(m.data, id)
	return nil
}

func (m *MemoryStateStore) Ping(ctx context.Context) error {
	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
		return nil
	}
}

func (m *MemoryStateStore) Close() error { return nil }

func stateToClient(st *NodeState) *ClientConn {
	return &ClientConn{
		ID:       NodeID(st.ID),
		Country:  st.Country,
		IP:       st.IP,
		OnWiFi:   st.OnWiFi,
		Idle:     st.Idle,
		Battery:  st.Battery,
		LastSeen: st.LastSeen,
		Send:     make(chan []byte, DefaultSendBuffer),
	}
}

// RedisClient abstracts go-redis ClusterClient so tests can stub it.
type RedisClient interface {
	Set(ctx context.Context, key string, value interface{}, expiration time.Duration) error
	Get(ctx context.Context, key string) (string, error)
	Del(ctx context.Context, keys ...string) error
	Ping(ctx context.Context) error
	Close() error
}

// RedisClusterStore persists node state via a Redis Cluster client for O(1) GET/SET.
type RedisClusterStore struct {
	client RedisClient
	ttl    time.Duration
}

// NewRedisClusterStore wraps a Redis Cluster client.
func NewRedisClusterStore(client RedisClient, ttl time.Duration) *RedisClusterStore {
	if ttl <= 0 {
		ttl = 2 * time.Minute
	}
	return &RedisClusterStore{client: client, ttl: ttl}
}

func (r *RedisClusterStore) PutNode(c *ClientConn) error {
	if r == nil || r.client == nil || c == nil {
		return fmt.Errorf("redis store not ready")
	}
	st := NodeState{
		ID:       string(c.ID),
		Country:  c.Country,
		IP:       c.IP,
		OnWiFi:   c.OnWiFi,
		Idle:     c.Idle,
		Battery:  c.Battery,
		LastSeen: c.LastSeen,
	}
	raw, err := json.Marshal(st)
	if err != nil {
		return err
	}
	return r.client.Set(context.Background(), nodeKey(c.ID), raw, r.ttl)
}

func (r *RedisClusterStore) GetNode(id NodeID) (*ClientConn, error) {
	if r == nil || r.client == nil {
		return nil, fmt.Errorf("redis store not ready")
	}
	raw, err := r.client.Get(context.Background(), nodeKey(id))
	if err != nil {
		return nil, err
	}
	var st NodeState
	if err := json.Unmarshal([]byte(raw), &st); err != nil {
		return nil, err
	}
	return stateToClient(&st), nil
}

func (r *RedisClusterStore) DeleteNode(id NodeID) error {
	if r == nil || r.client == nil {
		return fmt.Errorf("redis store not ready")
	}
	return r.client.Del(context.Background(), nodeKey(id))
}

func (r *RedisClusterStore) Ping(ctx context.Context) error {
	if r == nil || r.client == nil {
		return fmt.Errorf("redis store not ready")
	}
	return r.client.Ping(ctx)
}

func (r *RedisClusterStore) Close() error {
	if r == nil || r.client == nil {
		return nil
	}
	return r.client.Close()
}
