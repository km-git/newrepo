package coordinator

import (
	"net"
)

// RouteRequest is an enterprise routing query for idle Wi-Fi edge nodes.
type RouteRequest struct {
	CountryCode string
	TargetIP    net.IP
	IPMask      net.IPMask
	Payload     []byte
}

// DispatchResult captures one routed payload attempt.
type DispatchResult struct {
	NodeID  string
	Sent    bool
	Reason  string
	Payload []byte
}

// DispatchReport aggregates routing outcomes for a single request.
type DispatchReport struct {
	Matched int
	Sent    int
	Results []DispatchResult
}

// ipMatchesMask returns true when nodeIP shares the same masked prefix as targetIP.
func ipMatchesMask(nodeIP, targetIP net.IP, mask net.IPMask) bool {
	if len(mask) == 0 {
		return true
	}
	if len(nodeIP) == 0 || len(targetIP) == 0 {
		return false
	}
	return nodeIP.Mask(mask).Equal(targetIP.Mask(mask))
}

// RouteIdleWiFiNodes selects idle Wi-Fi clients matching country + IP mask and
// pipes payloads down each node's outbound channel without blocking callers.
func (h *Hub) RouteIdleWiFiNodes(req RouteRequest) DispatchReport {
	clients := h.Snapshot()
	report := DispatchReport{
		Results: make([]DispatchResult, 0, len(clients)),
	}

	for _, c := range clients {
		if !c.Idle || !c.WiFi {
			continue
		}
		if req.CountryCode != "" && c.CountryCode != req.CountryCode {
			continue
		}
		if req.IPMask != nil && !ipMatchesMask(c.IP, req.TargetIP, req.IPMask) {
			continue
		}

		report.Matched++
		res := DispatchResult{NodeID: c.NodeID, Payload: req.Payload}
		if len(req.Payload) == 0 {
			res.Reason = "empty payload"
			report.Results = append(report.Results, res)
			continue
		}
		if c.trySend(req.Payload) {
			res.Sent = true
			report.Sent++
		} else {
			res.Reason = "send channel full"
		}
		report.Results = append(report.Results, res)
	}

	return report
}
