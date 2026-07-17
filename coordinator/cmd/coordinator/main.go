package main

import (
	"log"
	"os"
	"strings"

	"github.com/ew-tool/coordinator"
)

func main() {
	addr := envOr("COORDINATOR_ADDR", ":8080")
	redisAddrs := strings.Split(envOr("REDIS_ADDRS", "127.0.0.1:6379"), ",")
	redisPass := os.Getenv("REDIS_PASSWORD")

	var store *coordinator.NodeStore
	if os.Getenv("COORDINATOR_REDIS_DISABLED") != "1" {
		s, err := coordinator.NewNodeStore(redisAddrs, redisPass)
		if err != nil {
			log.Printf("redis unavailable, continuing in-memory only: %v", err)
		} else {
			store = s
			defer store.Close()
		}
	}

	srv := coordinator.NewServer(addr, store)
	defer srv.Hub.Stop()
	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
