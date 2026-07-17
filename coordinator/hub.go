package coordinator

import (
	"context"
	"sync"
	"time"
)

// SilentTimeout is how long a socket may stay quiet before cleanup drops it.
const SilentTimeout = 45 * time.Second

// CleanupInterval is how often the background sweeper runs.
const CleanupInterval = 45 * time.Second

// Hub is the central high-concurrency connection registry for mobile edge nodes.
// Thousands of goroutines may Register / Unregister / Lookup concurrently via RWMutex.
type Hub struct {
	mu      sync.RWMutex
	clients map[string]*Client

	redis RedisCluster

	stopCleanup chan struct{}
	wg          sync.WaitGroup
}

// NewHub creates an empty hub. Pass a RedisCluster for O(1) durable state lookups
// (nil is allowed for in-memory-only operation / tests).
func NewHub(redis RedisCluster) *Hub {
	return &Hub{
		clients:     make(map[string]*Client),
		redis:       redis,
		stopCleanup: make(chan struct{}),
	}
}

// StartCleanup launches the automated background ticker that drops silent,
// non-responsive sockets every 45 seconds to free server RAM.
func (h *Hub) StartCleanup(ctx context.Context) {
	h.wg.Add(1)
	go func() {
		defer h.wg.Done()
		ticker := time.NewTicker(CleanupInterval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-h.stopCleanup:
				return
			case now := <-ticker.C:
				h.DropSilent(now)
			}
		}
	}()
}

// StopCleanup signals the sweeper to exit and waits for it.
func (h *Hub) StopCleanup() {
	select {
	case <-h.stopCleanup:
	default:
		close(h.stopCleanup)
	}
	h.wg.Wait()
}

// Register adds a client to the active map and mirrors idle/Wi-Fi state into Redis.
func (h *Hub) Register(c *Client) {
	h.mu.Lock()
	if prev, ok := h.clients[c.NodeID]; ok && prev != c {
		// Replace stale socket for the same node ID.
		delete(h.clients, c.NodeID)
		go prev.Close()
	}
	h.clients[c.NodeID] = c
	h.mu.Unlock()

	if h.redis != nil {
		_ = h.redis.SetNodeState(context.Background(), NodeState{
			NodeID:      c.NodeID,
			CountryCode: c.CountryCode,
			IPMask:      c.IPMask,
			BatteryPct:  c.BatteryPct,
			OnWiFi:      c.OnWiFi,
			Idle:        c.Idle,
			Connected:   true,
		})
	}
}

// Unregister removes a client if it is still the registered instance.
func (h *Hub) Unregister(c *Client) {
	h.mu.Lock()
	if cur, ok := h.clients[c.NodeID]; ok && cur == c {
		delete(h.clients, c.NodeID)
	}
	h.mu.Unlock()

	if h.redis != nil {
		_ = h.redis.DeleteNodeState(context.Background(), c.NodeID)
	}
}

// Lookup returns a client by node ID (O(1) map read under RLock).
func (h *Hub) Lookup(nodeID string) (*Client, bool) {
	h.mu.RLock()
	c, ok := h.clients[nodeID]
	h.mu.RUnlock()
	return c, ok
}

// Len returns the number of active connections.
func (h *Hub) Len() int {
	h.mu.RLock()
	n := len(h.clients)
	h.mu.RUnlock()
	return n
}

// IdleWiFiByCountry returns connected clients flagged idle + on Wi-Fi in country.
// Prefer Redis index when available for O(1) candidate ID lookup, then resolve
// live sockets from the in-memory map.
func (h *Hub) IdleWiFiByCountry(country string) []*Client {
	var out []*Client

	if h.redis != nil {
		ids, err := h.redis.IdleWiFiNodeIDs(context.Background(), country)
		if err == nil && len(ids) > 0 {
			h.mu.RLock()
			for _, id := range ids {
				if c, ok := h.clients[id]; ok && c.Idle && c.OnWiFi && c.CountryCode == country {
					out = append(out, c)
				}
			}
			h.mu.RUnlock()
			return out
		}
	}

	h.mu.RLock()
	for _, c := range h.clients {
		if c.Idle && c.OnWiFi && c.CountryCode == country {
			out = append(out, c)
		}
	}
	h.mu.RUnlock()
	return out
}

// DropSilent closes and removes sockets that have not responded within SilentTimeout.
func (h *Hub) DropSilent(now time.Time) int {
	h.mu.RLock()
	stale := make([]*Client, 0)
	for _, c := range h.clients {
		if c.IsSilent(now) {
			stale = append(stale, c)
		}
	}
	h.mu.RUnlock()

	for _, c := range stale {
		c.Close()
	}
	return len(stale)
}

// UpdateTelemetry applies packed device stats onto an active client and Redis.
func (h *Hub) UpdateTelemetry(t Telemetry) bool {
	c, ok := h.Lookup(t.NodeID)
	if !ok {
		return false
	}
	c.BatteryPct = t.BatteryPct
	c.OnWiFi = t.OnWiFi
	c.CountryCode = t.CountryCode
	c.Touch()

	if h.redis != nil {
		_ = h.redis.SetNodeState(context.Background(), NodeState{
			NodeID:      c.NodeID,
			CountryCode: c.CountryCode,
			IPMask:      c.IPMask,
			BatteryPct:  c.BatteryPct,
			OnWiFi:      c.OnWiFi,
			Idle:        c.Idle,
			Connected:   true,
		})
	}
	return true
}
