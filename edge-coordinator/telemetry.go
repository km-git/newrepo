package edgecoordinator

import (
	"encoding/binary"
	"errors"
	"io"
)

// TelemetrySize is the fixed binary footprint for device stats (no JSON).
// Layout (little-endian):
//
//	0-7   NodeID      uint64
//	8     Battery     uint8  (0-100)
//	9     Flags       uint8  (bit0 = WiFi)
//	10-11 CountryCode uint16
const TelemetrySize = 12

// ErrTelemetryTruncated is returned when the buffer is shorter than TelemetrySize.
var ErrTelemetryTruncated = errors.New("telemetry buffer truncated")

// Telemetry is the compact device stats payload for millions of phones.
type Telemetry struct {
	NodeID      uint64
	Battery     uint8
	WiFi        bool
	CountryCode uint16
}

// MarshalBinary packs telemetry into a tight 12-byte structure.
func (t Telemetry) MarshalBinary() ([]byte, error) {
	buf := make([]byte, TelemetrySize)
	binary.LittleEndian.PutUint64(buf[0:8], t.NodeID)
	buf[8] = t.Battery
	var flags uint8
	if t.WiFi {
		flags |= 0x01
	}
	buf[9] = flags
	binary.LittleEndian.PutUint16(buf[10:12], t.CountryCode)
	return buf, nil
}

// UnmarshalBinary unpacks a 12-byte telemetry blob.
func (t *Telemetry) UnmarshalBinary(data []byte) error {
	if len(data) < TelemetrySize {
		return ErrTelemetryTruncated
	}
	t.NodeID = binary.LittleEndian.Uint64(data[0:8])
	t.Battery = data[8]
	t.WiFi = data[9]&0x01 != 0
	t.CountryCode = binary.LittleEndian.Uint16(data[10:12])
	return nil
}

// PackTelemetry writes binary telemetry to w.
func PackTelemetry(t *Telemetry, w io.Writer) error {
	b, err := t.MarshalBinary()
	if err != nil {
		return err
	}
	_, err = w.Write(b)
	return err
}

// UnpackTelemetry reads binary telemetry from r.
func UnpackTelemetry(r io.Reader) (*Telemetry, error) {
	buf := make([]byte, TelemetrySize)
	if _, err := io.ReadFull(r, buf); err != nil {
		return nil, err
	}
	var t Telemetry
	if err := t.UnmarshalBinary(buf); err != nil {
		return nil, err
	}
	return &t, nil
}
