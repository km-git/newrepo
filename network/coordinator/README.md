# Network Coordinator (Go)

High-concurrency edge routing for up to 10M mobile devices.

## Modules

| File | Role |
|------|------|
| `hub.go` | Connection hub — `sync.RWMutex` map, 45s silent-socket cleanup |
| `dispatcher.go` | Country + IP-mask routing to idle Wi-Fi nodes (non-blocking) |
| `telemetry.go` | 28-byte binary device stats (no JSON) |
| `redis_store.go` | Redis Cluster interface for O(1) state lookup |
| `ws.go` | `gorilla/websocket` with tuned read/write buffers |

## Run tests

```bash
cd network/coordinator
go test ./...
```

## Token / model policy (repo-wide)

- Per-model ceiling: `EW_LLM_MAX_TOKENS_PER_MODEL=10000`
- Workhorse (implementation): Haiku / Composer / Grok
- Architect / executive: GPT-5.6 Sol / Opus / Fable (budgeted via `engine/architect_budget.py`)
- Token savers: tiktoken, diskcache, zstd, llm-token-optimizer, tokenpruner, cachetic, foldback-ai
- OKF secondary brain + multi-model PR consensus for auto-approve
