# Mobile Edge Network Coordinator

Go service (`edgecoordinator`) that routes enterprise traffic across millions of
mobile edge devices over high-efficiency WebSockets.

## Modules

| File | Role |
|------|------|
| `hub.go` | Connection hub — `sync.RWMutex` client map, gorilla/websocket, 45s idle cleanup |
| `dispatcher.go` | Country + IP-mask routing to idle Wi-Fi nodes; non-blocking channel sends |
| `telemetry.go` | Fixed 12-byte binary device stats (no JSON) |
| `state.go` | Redis Cluster `StateStore` + in-memory stub for tests |

## Run tests

```bash
cd edge-coordinator && go test ./...
```

## Token / AI policy (repo-wide)

- Per-model ceiling: `EW_LLM_MAX_TOKENS_PER_MODEL=10000`
- Workhorse models for implementation; GPT-5.6 Sol / Opus for architect/executive
- OKF secondary brain: `EW_OKF_BRAIN=1` + `EW_BRAIN_CONSENSUS=1`
- PR auto-approve: `scripts/pr_executive_consensus.py` (5/7 multi-model consensus)
