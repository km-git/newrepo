# dspm

Open-source Data Security Posture Management (DSPM) sibling of the tape-to-cloud tool. Twelve modules map Cyera-like capabilities onto CloudQuery, Presidio, DuckDB, Steampipe (CLI only, AGPL-3.0), Prowler, Trivy 0.71.2+, Cloud Custodian, and DataHub — $0/month.

This is **not** a Cyera replacement. Honest gap: about 70-80% of the value (no 95% long-tail classifier, no unified identity graph, experimental AI-workload scanner, four hand-rolled remediation policies).

```bash
python -m dspm audit inventory
python -m dspm classify examples/sample.csv
make dspm-all
```

Hard gates: never install Trivy 0.69.4 (CVE-2026-33634), never `import steampipe`, install Presidio from `data-privacy-stack/presidio`, never auto-merge `dspm/remediation/policies/`.
