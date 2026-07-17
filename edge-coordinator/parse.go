package edgecoordinator

import (
	"fmt"
	"net/http"
	"strconv"
)

func parseUint64Query(r *http.Request, key string) (uint64, error) {
	vals := r.URL.Query()[key]
	if len(vals) == 0 {
		return 0, fmt.Errorf("missing %s", key)
	}
	return strconv.ParseUint(vals[0], 10, 64)
}

func parseUint16Query(r *http.Request, key string) (uint16, error) {
	vals := r.URL.Query()[key]
	if len(vals) == 0 {
		return 0, nil
	}
	v, err := strconv.ParseUint(vals[0], 10, 16)
	return uint16(v), err
}
