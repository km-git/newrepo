package coordinator

import (
	"encoding/binary"
	"errors"
	"fmt"
)

// Binary telemetry layout (little-endian, fixed + length-prefixed strings):
//
//	magic      uint16 = 0xEE01 — format marker
//	version   uint8  = 1
//	flags     uint8  — bit0 = OnWiFi
//	battery   uint8  — 0..100
//	nodeLen   uint8
//	nodeID    [nodeLen]byte
//	ccLen     uint8  — country code length (typically 2)
//	country   [ccLen]byte
//
// Avoids JSON for millions of phones — typically ~12–40 bytes per sample.

const (
	telemetryMagic   uint16 = 0xEE01
	telemetryVersion uint8  = 1
	flagOnWiFi       uint8  = 1 << 0
)

// Telemetry is the device stats snapshot packed for wire transfer.
type Telemetry struct {
	NodeID      string
	BatteryPct  uint8
	OnWiFi      bool
	CountryCode string
}

// ErrTelemetryCorrupt indicates an invalid binary frame.
var ErrTelemetryCorrupt = errors.New("corrupt telemetry frame")

// PackTelemetry compresses device stats into a tight binary structure.
func PackTelemetry(t Telemetry) ([]byte, error) {
	if t.NodeID == "" {
		return nil, fmt.Errorf("node id required")
	}
	if len(t.NodeID) > 255 {
		return nil, fmt.Errorf("node id too long")
	}
	if len(t.CountryCode) > 255 {
		return nil, fmt.Errorf("country code too long")
	}
	if t.BatteryPct > 100 {
		return nil, fmt.Errorf("battery pct out of range")
	}

	n := 2 + 1 + 1 + 1 + 1 + len(t.NodeID) + 1 + len(t.CountryCode)
	buf := make([]byte, n)
	binary.LittleEndian.PutUint16(buf[0:2], telemetryMagic)
	buf[2] = telemetryVersion
	var flags uint8
	if t.OnWiFi {
		flags |= flagOnWiFi
	}
	buf[3] = flags
	buf[4] = t.BatteryPct
	buf[5] = uint8(len(t.NodeID))
	copy(buf[6:], t.NodeID)
	off := 6 + len(t.NodeID)
	buf[off] = uint8(len(t.CountryCode))
	copy(buf[off+1:], t.CountryCode)
	return buf, nil
}

// UnpackTelemetry decodes a binary telemetry frame.
func UnpackTelemetry(data []byte) (Telemetry, error) {
	if len(data) < 7 {
		return Telemetry{}, ErrTelemetryCorrupt
	}
	if binary.LittleEndian.Uint16(data[0:2]) != telemetryMagic {
		return Telemetry{}, ErrTelemetryCorrupt
	}
	if data[2] != telemetryVersion {
		return Telemetry{}, fmt.Errorf("unsupported telemetry version %d", data[2])
	}
	flags := data[3]
	battery := data[4]
	nodeLen := int(data[5])
	if 6+nodeLen+1 > len(data) {
		return Telemetry{}, ErrTelemetryCorrupt
	}
	nodeID := string(data[6 : 6+nodeLen])
	off := 6 + nodeLen
	ccLen := int(data[off])
	if off+1+ccLen > len(data) {
		return Telemetry{}, ErrTelemetryCorrupt
	}
	country := string(data[off+1 : off+1+ccLen])
	return Telemetry{
		NodeID:      nodeID,
		BatteryPct:  battery,
		OnWiFi:      flags&flagOnWiFi != 0,
		CountryCode: country,
	}, nil
}
