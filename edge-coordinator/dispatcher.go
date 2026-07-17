package edgecoordinator

import (
	"context"
	"errors"
	"net"
	"sync"
)

// ErrNoMatchingNodes is returned when no idle Wi-Fi nodes match the route.
var ErrNoMatchingNodes = errors.New("no matching idle Wi-Fi nodes")

// ErrDispatchFull is returned when the dispatch queue is saturated.
var ErrDispatchFull = errors.New("dispatch channel full")

// Envelope is an enterprise data request targeting country + IP mask.
type Envelope struct {
	CountryCode uint16
	IPMask      net.IPMask
	Network     net.IP // network address to AND with IPMask
	Payload     []byte
}

// NodeCache is an in-memory index of idle Wi-Fi nodes by country for O(1) slices.
type NodeCache struct {
	mu        sync.RWMutex
	byCountry map[uint16]map[uint64]struct{}
	meta      map[uint64]cacheMeta
}

type cacheMeta struct {
	country uint16
	idle    bool
	wifi    bool
	ip      net.IP
}

// NewNodeCache creates an empty routing cache.
func NewNodeCache() *NodeCache {
	return &NodeCache{
		byCountry: make(map[uint16]map[uint64]struct{}),
		meta:      make(map[uint64]cacheMeta),
	}
}

// Update refreshes idle/Wi-Fi/country flags for a node.
func (nc *NodeCache) Update(id uint64, idle, wifi bool, country uint16, ip net.IP) {
	nc.mu.Lock()
	defer nc.mu.Unlock()
	if old, ok := nc.meta[id]; ok {
		if set, ok2 := nc.byCountry[old.country]; ok2 {
			delete(set, id)
			if len(set) == 0 {
				delete(nc.byCountry, old.country)
			}
		}
	}
	nc.meta[id] = cacheMeta{country: country, idle: idle, wifi: wifi, ip: cloneIP(ip)}
	if idle && wifi {
		set, ok := nc.byCountry[country]
		if !ok {
			set = make(map[uint64]struct{})
			nc.byCountry[country] = set
		}
		set[id] = struct{}{}
	}
}

// Remove drops a node from the cache.
func (nc *NodeCache) Remove(id uint64) {
	nc.mu.Lock()
	defer nc.mu.Unlock()
	if old, ok := nc.meta[id]; ok {
		if set, ok2 := nc.byCountry[old.country]; ok2 {
			delete(set, id)
			if len(set) == 0 {
				delete(nc.byCountry, old.country)
			}
		}
		delete(nc.meta, id)
	}
}

// IdleWiFi returns node IDs currently flagged idle and on Wi-Fi for a country.
func (nc *NodeCache) IdleWiFi(country uint16) []uint64 {
	nc.mu.RLock()
	defer nc.mu.RUnlock()
	set := nc.byCountry[country]
	out := make([]uint64, 0, len(set))
	for id := range set {
		out = append(out, id)
	}
	return out
}

// Dispatcher routes envelopes to matching mobile nodes without blocking callers.
type Dispatcher struct {
	hub     *ConnectionHub
	cache   *NodeCache
	routes  chan Envelope
	workers int
}

// NewDispatcher builds a load evaluator with a buffered non-blocking route channel.
func NewDispatcher(hub *ConnectionHub, cache *NodeCache, workers int) *Dispatcher {
	if workers < 1 {
		workers = 4
	}
	return &Dispatcher{
		hub:     hub,
		cache:   cache,
		routes:  make(chan Envelope, 4096),
		workers: workers,
	}
}

// Start launches worker goroutines that drain the route channel.
func (d *Dispatcher) Start(ctx context.Context) {
	for i := 0; i < d.workers; i++ {
		go func() {
			for {
				select {
				case <-ctx.Done():
					return
				case env := <-d.routes:
					d.route(env)
				}
			}
		}()
	}
}

// Dispatch accepts an enterprise request and pipes it to workers without blocking
// the main event loop. Returns ErrDispatchFull if the channel is saturated.
func (d *Dispatcher) Dispatch(env Envelope) error {
	select {
	case d.routes <- env:
		return nil
	default:
		return ErrDispatchFull
	}
}

// route selects idle Wi-Fi nodes matching country + IP mask and trySends payload.
func (d *Dispatcher) route(env Envelope) {
	ids := d.cache.IdleWiFi(env.CountryCode)
	for _, id := range ids {
		c, ok := d.hub.Get(id)
		if !ok {
			continue
		}
		if !matchIPMask(c.IP, env.Network, env.IPMask) {
			continue
		}
		if d.trySend(c, env.Payload) {
			c.Idle.Store(false)
			d.cache.Update(id, false, c.WiFi.Load(), c.CountryCode, c.IP)
			return
		}
	}
}

// trySend pipes payload down the client channel without blocking the event loop.
func (d *Dispatcher) trySend(c *Client, payload []byte) bool {
	select {
	case c.Send <- payload:
		return true
	default:
		return false
	}
}

// MatchNodes returns idle Wi-Fi clients matching country + IP mask (for tests).
func (d *Dispatcher) MatchNodes(env Envelope) []*Client {
	ids := d.cache.IdleWiFi(env.CountryCode)
	out := make([]*Client, 0, len(ids))
	for _, id := range ids {
		c, ok := d.hub.Get(id)
		if !ok {
			continue
		}
		if matchIPMask(c.IP, env.Network, env.IPMask) {
			out = append(out, c)
		}
	}
	return out
}

func matchIPMask(ip, network net.IP, mask net.IPMask) bool {
	if ip == nil || network == nil || mask == nil {
		return mask == nil && network == nil
	}
	ip4 := ip.To4()
	net4 := network.To4()
	if ip4 == nil || net4 == nil {
		return false
	}
	masked := make(net.IP, len(ip4))
	for i := range ip4 {
		masked[i] = ip4[i] & mask[i]
	}
	for i := range net4 {
		if masked[i] != (net4[i] & mask[i]) {
			return false
		}
	}
	return true
}

func cloneIP(ip net.IP) net.IP {
	if ip == nil {
		return nil
	}
	out := make(net.IP, len(ip))
	copy(out, ip)
	return out
}
