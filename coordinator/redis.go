package coordinator

import (
	"context"
	"sync"
)

// NodeState is the Redis-backed view of a mobile edge node for O(1) lookups.
type NodeState struct {
	NodeID      string
	CountryCode string
	IPMask      string
	BatteryPct  uint8
	OnWiFi      bool
	Idle        bool
	Connected   bool
}

// RedisCluster is the storage interface for O(1) node state operations.
// Implementations may wrap go-redis ClusterClient; MemoryRedis is for tests.
type RedisCluster interface {
	SetNodeState(ctx context.Context, state NodeState) error
	GetNodeState(ctx context.Context, nodeID string) (NodeState, bool, error)
	DeleteNodeState(ctx context.Context, nodeID string) error
	// IdleWiFiNodeIDs returns candidate IDs for a country in O(1) set lookup time.
	IdleWiFiNodeIDs(ctx context.Context, country string) ([]string, error)
}

// MemoryRedis is an in-process Redis Cluster stand-in used by unit tests and
// local dry-runs when a real cluster is unavailable.
type MemoryRedis struct {
	mu       sync.RWMutex
	byID     map[string]NodeState
	idleWiFi map[string]map[string]struct{} // country -> set of node IDs
}

// NewMemoryRedis constructs an empty in-memory cluster facade.
func NewMemoryRedis() *MemoryRedis {
	return &MemoryRedis{
		byID:     make(map[string]NodeState),
		idleWiFi: make(map[string]map[string]struct{}),
	}
}

func (m *MemoryRedis) SetNodeState(ctx context.Context, state NodeState) error {
	_ = ctx
	m.mu.Lock()
	defer m.mu.Unlock()
	if prev, ok := m.byID[state.NodeID]; ok {
		m.removeIdleIndexLocked(prev)
	}
	m.byID[state.NodeID] = state
	if state.Connected && state.Idle && state.OnWiFi {
		set, ok := m.idleWiFi[state.CountryCode]
		if !ok {
			set = make(map[string]struct{})
			m.idleWiFi[state.CountryCode] = set
		}
		set[state.NodeID] = struct{}{}
	}
	return nil
}

func (m *MemoryRedis) GetNodeState(ctx context.Context, nodeID string) (NodeState, bool, error) {
	_ = ctx
	m.mu.RLock()
	defer m.mu.RUnlock()
	s, ok := m.byID[nodeID]
	return s, ok, nil
}

func (m *MemoryRedis) DeleteNodeState(ctx context.Context, nodeID string) error {
	_ = ctx
	m.mu.Lock()
	defer m.mu.Unlock()
	if prev, ok := m.byID[nodeID]; ok {
		m.removeIdleIndexLocked(prev)
		delete(m.byID, nodeID)
	}
	return nil
}

func (m *MemoryRedis) IdleWiFiNodeIDs(ctx context.Context, country string) ([]string, error) {
	_ = ctx
	m.mu.RLock()
	defer m.mu.RUnlock()
	set := m.idleWiFi[country]
	out := make([]string, 0, len(set))
	for id := range set {
		out = append(out, id)
	}
	return out, nil
}

func (m *MemoryRedis) removeIdleIndexLocked(prev NodeState) {
	if set, ok := m.idleWiFi[prev.CountryCode]; ok {
		delete(set, prev.NodeID)
		if len(set) == 0 {
			delete(m.idleWiFi, prev.CountryCode)
		}
	}
}
