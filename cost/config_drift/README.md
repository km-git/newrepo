# cost/config_drift

Cost-relevant configuration drift: instance type changes, storage class
changes, reserved-instance / savings-plan expiry.

CLI: `cost drift diff --provider aws --baseline baseline.json`

Prowler 5.41.0 as a CLI subprocess for a config snapshot; DuckDB/SQLite for
the diff. Output is a configuration observation, not a security assessment.
