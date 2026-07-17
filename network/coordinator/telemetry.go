package coordinator

import (
	"encoding/binary"
	"errors"
	"fmt"
)

// Binary telemetry layout (fixed 28 bytes) — avoids JSON across millions of phones:
//
//	[0:16]  NodeID bytes (UTF-8, zero-padded / truncated to 16)
//	[16]    Battery percent 0–100
//	[17]    Flags: bit0=WiFi, bit1=Idle, bit2–7 reserved
//	[18:20] Country code (2 ASCII bytes, uppercased)
//	[20:28] Reserved / CRC64 placeholder (zero for v1)
const (
	TelemetrySize     = 28
	telemetryIDLen    = 16
	flagWiFi          = 1 << 0
	flagIdle          = 1 << 1
	TelemetryVersion1 = 1
)

var (
	ErrTelemetryShort   = errors.New("telemetry: buffer too short")
	ErrTelemetryCorrupt = errors.New("telemetry: corrupt payload")
)

// DeviceStats is the compact device telemetry model.
type DeviceStats struct {
	NodeID  NodeID
	Battery uint8 // 0–100
	OnWiFi  bool
	Idle    bool
	Country string // ISO alpha-2
}

// PackTelemetry compresses device stats into a fixed-size binary blob.
func PackTelemetry(s DeviceStats) ([]byte, error) {
	if s.Battery > 100 {
		return nil, fmt.Errorf("telemetry: battery %d out of range", s.Battery)
	}
	buf := make([]byte, TelemetrySize)
	id := []byte(s.NodeID)
	if len(id) > telemetryIDLen {
		id = id[:telemetryIDLen]
	}
	copy(buf[0:telemetryIDLen], id)
	buf[16] = s.Battery
	var flags byte
	if s.OnWiFi {
		flags |= flagWiFi
	}
	if s.Idle {
		flags |= flagIdle
	}
	buf[17] = flags
	cc := normalizeCountry(s.Country)
	buf[18] = cc[0]
	buf[19] = cc[1]
	// bytes 20–27 reserved (zero). Presence of zeros acts as a simple integrity pad.
	binary.LittleEndian.PutUint64(buf[20:28], 0)
	return buf, nil
}

// UnpackTelemetry decodes a binary telemetry blob into DeviceStats.
func UnpackTelemetry(buf []byte) (DeviceStats, error) {
	if len(buf) < TelemetrySize {
		return DeviceStats{}, ErrTelemetryShort
	}
	idBytes := buf[0:telemetryIDLen]
	// Trim trailing NUL padding from NodeID.
	end := telemetryIDLen
	for end > 0 && idBytes[end-1] == 0 {
		end--
	}
	if end == 0 {
		return DeviceStats{}, ErrTelemetryCorrupt
	}
	flags := buf[17]
	return DeviceStats{
		NodeID:  NodeID(idBytes[:end]),
		Battery: buf[16],
		OnWiFi:  flags&flagWiFi != 0,
		Idle:    flags&flagIdle != 0,
		Country: string([]byte{buf[18], buf[19]}),
	}, nil
}

func normalizeCountry(cc string) [2]byte {
	var out [2]byte
	out[0], out[1] = 'X', 'X'
	if len(cc) >= 2 {
		out[0] = toUpperASCII(cc[0])
		out[1] = toUpperASCII(cc[1])
	}
	return out
}

func toUpperASCII(b byte) byte {
	if b >= 'a' && b <= 'z' {
		return b - ('a' - 'A')
	}
	return b
}
