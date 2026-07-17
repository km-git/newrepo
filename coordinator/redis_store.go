package coordinator

import (
	"context"
	"fmt"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

// NodeStore provides O(1) Redis-backed node metadata lookups (cluster-ready interface).
type NodeStore struct {
	rdb redis.UniversalClient
	ttl time.Duration
}

// NewNodeStore connects to Redis Cluster or a single-node fallback.
func NewNodeStore(addrs []string, password string) (*NodeStore, error) {
	if len(addrs) == 0 {
		addrs = []string{"127.0.0.1:6379"}
	}
	rdb := redis.NewUniversalClient(&redis.UniversalOptions{
		Addrs:    addrs,
		Password: password,
	})
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("redis ping: %w", err)
	}
	return &NodeStore{rdb: rdb, ttl: defaultStaleAfter}, nil
}

func nodeKey(nodeID string) string { return "edge:node:" + nodeID }

func countryIdleKey(country string) string { return "edge:country:" + country + ":idle" }

// UpsertNode writes node metadata and maintains country idle index sets.
func (s *NodeStore) UpsertNode(ctx context.Context, c *Client) error {
	key := nodeKey(c.NodeID)
	pipe := s.rdb.TxPipeline()
	pipe.HSet(ctx, key, map[string]interface{}{
		"country":  c.CountryCode,
		"ip":       c.IP.String(),
		"battery":  strconv.Itoa(int(c.BatteryPct)),
		"wifi":     boolStr(c.WiFi),
		"idle":     boolStr(c.Idle),
		"lastseen": time.Now().Unix(),
	})
	pipe.Expire(ctx, key, s.ttl)
	if c.Idle && c.WiFi && c.CountryCode != "" {
		idleKey := countryIdleKey(c.CountryCode)
		pipe.SAdd(ctx, idleKey, c.NodeID)
		pipe.Expire(ctx, idleKey, s.ttl)
	}
	_, err := pipe.Exec(ctx)
	return err
}

// RemoveNode deletes node metadata and index membership.
func (s *NodeStore) RemoveNode(ctx context.Context, c *Client) error {
	pipe := s.rdb.TxPipeline()
	pipe.Del(ctx, nodeKey(c.NodeID))
	if c.CountryCode != "" {
		pipe.SRem(ctx, countryIdleKey(c.CountryCode), c.NodeID)
	}
	_, err := pipe.Exec(ctx)
	return err
}

// IdleNodeIDs returns node ids indexed as idle+wifi for a country (O(1) set fetch).
func (s *NodeStore) IdleNodeIDs(ctx context.Context, country string) ([]string, error) {
	return s.rdb.SMembers(ctx, countryIdleKey(country)).Result()
}

// Close releases Redis connections.
func (s *NodeStore) Close() error { return s.rdb.Close() }

func boolStr(v bool) string {
	if v {
		return "1"
	}
	return "0"
}
