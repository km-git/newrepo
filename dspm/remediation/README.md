# dspm/remediation

Cloud Custodian dry-run plans. Policies are never auto-merged.

JSON is the default CLI output. Pass `--human` for a table.

```bash
dspm remediate plan --dry-run
```

Primary OSS tools and honest gaps are listed in the package inventory (`dspm audit inventory`). This module does not add paid APIs, GPUs, or Ollama.
