package coordinator

import (
	"context"
	"errors"
	"fmt"
)

// ErrNoMatchingNodes is returned when no idle Wi-Fi peer matches the request.
var ErrNoMatchingNodes = errors.New("no matching idle Wi-Fi nodes")

// ErrDispatchBlocked is returned when every candidate send queue is full.
var ErrDispatchBlocked = errors.New("dispatch channels full")

// EnterpriseRequest describes a routing target for edge execution.
type EnterpriseRequest struct {
	CountryCode string
	IPMask      string // required CIDR / IP filter
	Payload     []byte // network execution payload
	MaxPeers    int    // optional cap; 0 = all matches
}

// DispatchResult summarizes a non-blocking fan-out attempt.
type DispatchResult struct {
	Matched  int
	Delivered int
	NodeIDs  []string
}

// Dispatcher routes enterprise requests onto idle Wi-Fi mobile nodes.
type Dispatcher struct {
	hub *Hub
}

// NewDispatcher binds a dispatcher to the connection hub / memory cache.
func NewDispatcher(hub *Hub) *Dispatcher {
	return &Dispatcher{hub: hub}
}

// Route accepts an enterprise data request (country + IP mask), pulls matching
// idle Wi-Fi connections from the active cache, and pipes the payload down each
// designated channel without blocking the main event loops (TrySend).
func (d *Dispatcher) Route(req EnterpriseRequest) (DispatchResult, error) {
	if req.CountryCode == "" {
		return DispatchResult{}, fmt.Errorf("country code required")
	}
	if len(req.Payload) == 0 {
		return DispatchResult{}, fmt.Errorf("payload required")
	}

	candidates := d.hub.IdleWiFiByCountry(req.CountryCode)
	matched := make([]*Client, 0, len(candidates))
	for _, c := range candidates {
		if c.MatchesIP(req.IPMask) {
			matched = append(matched, c)
		}
	}
	if len(matched) == 0 {
		return DispatchResult{}, ErrNoMatchingNodes
	}

	limit := len(matched)
	if req.MaxPeers > 0 && req.MaxPeers < limit {
		limit = req.MaxPeers
	}

	res := DispatchResult{
		Matched: len(matched),
		NodeIDs: make([]string, 0, limit),
	}
	for i := 0; i < limit; i++ {
		c := matched[i]
		// Non-blocking: never stall the caller / event loop.
		if c.TrySend(req.Payload) {
			res.Delivered++
			res.NodeIDs = append(res.NodeIDs, c.NodeID)
			c.Idle = false // mark busy after accepting work
			if d.hub.redis != nil {
				_ = d.hub.redis.SetNodeState(context.Background(), NodeState{
					NodeID:      c.NodeID,
					CountryCode: c.CountryCode,
					IPMask:      c.IPMask,
					BatteryPct:  c.BatteryPct,
					OnWiFi:      c.OnWiFi,
					Idle:        false,
					Connected:   true,
				})
			}
		}
	}
	if res.Delivered == 0 {
		return res, ErrDispatchBlocked
	}
	return res, nil
}
