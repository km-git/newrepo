package coordinator

import (
	"encoding/binary"
	"errors"
	"fmt"
)

const (
	telemetryMagic   uint16 = 0x4557 // "EW"
	telemetryVersion uint8  = 1
	telemetryHeader  int    = 8 // magic(2) + ver(1) + idLen(1) + battery(1) + flags(1) + country(2)
	maxNodeIDLen     int    = 64
)

// DeviceStats holds compact telemetry for a mobile edge node.
type DeviceStats struct {
	NodeID      string
	BatteryPct  uint8
	WiFi        bool
	CountryCode string // ISO 3166-1 alpha-2
}

// PackTelemetry serializes device stats into a tight binary blob (no JSON).
func PackTelemetry(stats DeviceStats) ([]byte, error) {
	if stats.NodeID == "" {
		return nil, errors.New("telemetry: node id required")
	}
	if len(stats.NodeID) > maxNodeIDLen {
		return nil, fmt.Errorf("telemetry: node id exceeds %d bytes", maxNodeIDLen)
	}
	cc := stats.CountryCode
	if len(cc) != 2 {
		return nil, errors.New("telemetry: country code must be 2 ASCII chars")
	}

	out := make([]byte, telemetryHeader+len(stats.NodeID))
	binary.BigEndian.PutUint16(out[0:2], telemetryMagic)
	out[2] = telemetryVersion
	out[3] = uint8(len(stats.NodeID))
	out[4] = stats.BatteryPct
	flags := uint8(0)
	if stats.WiFi {
		flags |= 1
	}
	out[5] = flags
	copy(out[6:8], []byte(cc))
	copy(out[telemetryHeader:], []byte(stats.NodeID))
	return out, nil
}

// UnpackTelemetry decodes a binary telemetry blob produced by PackTelemetry.
func UnpackTelemetry(data []byte) (DeviceStats, error) {
	if len(data) < telemetryHeader {
		return DeviceStats{}, errors.New("telemetry: buffer too short")
	}
	if binary.BigEndian.Uint16(data[0:2]) != telemetryMagic {
		return DeviceStats{}, errors.New("telemetry: invalid magic")
	}
	if data[2] != telemetryVersion {
		return DeviceStats{}, fmt.Errorf("telemetry: unsupported version %d", data[2])
	}

	idLen := int(data[3])
	if idLen == 0 || idLen > maxNodeIDLen {
		return DeviceStats{}, errors.New("telemetry: invalid node id length")
	}
	if len(data) < telemetryHeader+idLen {
		return DeviceStats{}, errors.New("telemetry: truncated node id")
	}

	stats := DeviceStats{
		NodeID:      string(data[telemetryHeader : telemetryHeader+idLen]),
		BatteryPct:  data[4],
		WiFi:        data[5]&1 != 0,
		CountryCode: string(data[6:8]),
	}
	return stats, nil
}
