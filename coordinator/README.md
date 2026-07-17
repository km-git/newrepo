# Mobile Edge Network Coordinator

Go service that routes enterprise workloads across millions of mobile edge
devices over optimized WebSockets, with Redis Cluster for O(1) node-state
lookups and binary telemetry packing to cut bandwidth.

## Modules

| File | Role |
|------|------|
| `hub.go` | Central connection map + `sync.RWMutex` + 45s silent-socket cleanup |
| `dispatcher.go` | Route by country code + IP mask to idle Wi-Fi nodes (non-blocking) |
| `telemetry.go` | Binary pack/unpack of Node ID, battery %, Wi-Fi, country |
| `redis.go` | Redis Cluster interface (+ in-memory facade for tests) |
| `client.go` | Per-node WebSocket client with bounded send queue / buffer sizes |

## Quick test

```bash
cd coordinator && go test ./...
```

## Design notes

- `gorilla/websocket` upgrader uses 1 KiB read/write buffers to bound RAM.
- Dispatch uses `TrySend` so full queues never block event loops.
- Silent sockets are dropped every 45 seconds (`SilentTimeout` / `CleanupInterval`).
