---
type: architecture
title: Go mobile-edge network coordinator
description: Hub+dispatcher+binary telemetry for 10M nodes
timestamp: '2026-07-17T16:20:31Z'
tags:
- go
- websocket
- redis
- edge
- coordinator
resource: coordinator/
token_ceiling: 10000
models_workhorse: haiku/gemini/grok
models_architect: gpt-5.6-sol/opus
---

# Go Edge Network Coordinator

## Schema
- Hub: map[nodeID]*Client under sync.RWMutex; 45s cleanup ticker
- Dispatcher: country+IP mask → idle Wi-Fi nodes; non-blocking send
- Telemetry: binary pack (nodeID, battery%, wifi, country)
- RedisCluster: Get/Set/ScanByCountry interface for O(1) lookups

## Files
- coordinator/hub.go
- coordinator/dispatcher.go
- coordinator/telemetry.go
- coordinator/redis.go
- coordinator/client.go
- coordinator/go.mod
- coordinator/*_test.go

## Deps
- github.com/gorilla/websocket
- redis cluster client interface (abstract for tests)
