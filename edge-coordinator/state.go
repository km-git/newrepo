package edgecoordinator

import (
	"context"
	"encoding/binary"
	"fmt"
	"sync"

	"github.com/redis/go-redis/v9"
)

// NodeState is the O(1) Redis-backed snapshot for a mobile edge node.
type NodeState struct {
	Battery     uint8
	WiFi        bool
	Idle        bool
	CountryCode uint16
	LastSeen    int64
}

// StateStore is the Redis Cluster interface for O(1) state lookups.
type StateStore interface {
	GetNode(ctx context.Context, id uint64) (NodeState, error)
	SetNode(ctx context.Context, id uint64, st NodeState) error
	MGetNodes(ctx context.Context, ids []uint64) ([]NodeState, error)
	Ping(ctx context.Context) error
}

// RedisClusterStore implements StateStore against a Redis Cluster client.
type RedisClusterStore struct {
	rdb *redis.ClusterClient
}

// NewRedisClusterStore wraps a go-redis ClusterClient.
func NewRedisClusterStore(rdb *redis.ClusterClient) *RedisClusterStore {
	return &RedisClusterStore{rdb: rdb}
}

func nodeKey(id uint64) string {
	return fmt.Sprintf("edge:node:%d", id)
}

func encodeState(st NodeState) string {
	buf := make([]byte, 14)
	buf[0] = st.Battery
	var flags uint8
	if st.WiFi {
		flags |= 0x01
	}
	if st.Idle {
		flags |= 0x02
	}
	buf[1] = flags
	binary.LittleEndian.PutUint16(buf[2:4], st.CountryCode)
	binary.LittleEndian.PutUint64(buf[4:12], uint64(st.LastSeen))
	return string(buf[:12])
}

func decodeState(raw string) (NodeState, error) {
	b := []byte(raw)
	if len(b) < 12 {
		return NodeState{}, fmt.Errorf("node state truncated")
	}
	return NodeState{
		Battery:     b[0],
		WiFi:        b[1]&0x01 != 0,
		Idle:        b[1]&0x02 != 0,
		CountryCode: binary.LittleEndian.Uint16(b[2:4]),
		LastSeen:    int64(binary.LittleEndian.Uint64(b[4:12])),
	}, nil
}

// GetNode performs an O(1) GET by node key.
func (s *RedisClusterStore) GetNode(ctx context.Context, id uint64) (NodeState, error) {
	val, err := s.rdb.Get(ctx, nodeKey(id)).Result()
	if err != nil {
		return NodeState{}, err
	}
	return decodeState(val)
}

// SetNode writes node state with SET.
func (s *RedisClusterStore) SetNode(ctx context.Context, id uint64, st NodeState) error {
	return s.rdb.Set(ctx, nodeKey(id), encodeState(st), 0).Err()
}

// MGetNodes batch-fetches nodes (best-effort across cluster slots).
func (s *RedisClusterStore) MGetNodes(ctx context.Context, ids []uint64) ([]NodeState, error) {
	out := make([]NodeState, len(ids))
	pipe := s.rdb.Pipeline()
	cmds := make([]*redis.StringCmd, len(ids))
	for i, id := range ids {
		cmds[i] = pipe.Get(ctx, nodeKey(id))
	}
	_, _ = pipe.Exec(ctx)
	for i, cmd := range cmds {
		val, err := cmd.Result()
		if err != nil {
			continue
		}
		st, err := decodeState(val)
		if err != nil {
			continue
		}
		out[i] = st
	}
	return out, nil
}

// Ping checks cluster connectivity.
func (s *RedisClusterStore) Ping(ctx context.Context) error {
	return s.rdb.Ping(ctx).Err()
}

// StubStore is an in-memory StateStore for tests (no live Redis required).
type StubStore struct {
	mu   sync.RWMutex
	data map[uint64]NodeState
}

// NewStubStore creates an empty in-memory store.
func NewStubStore() *StubStore {
	return &StubStore{data: make(map[uint64]NodeState)}
}

func (s *StubStore) GetNode(_ context.Context, id uint64) (NodeState, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	st, ok := s.data[id]
	if !ok {
		return NodeState{}, fmt.Errorf("node %d not found", id)
	}
	return st, nil
}

func (s *StubStore) SetNode(_ context.Context, id uint64, st NodeState) error {
	s.mu.Lock()
	s.data[id] = st
	s.mu.Unlock()
	return nil
}

func (s *StubStore) MGetNodes(_ context.Context, ids []uint64) ([]NodeState, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]NodeState, len(ids))
	for i, id := range ids {
		out[i] = s.data[id]
	}
	return out, nil
}

func (s *StubStore) Ping(context.Context) error { return nil }
