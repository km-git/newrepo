# dspm/audit

Workspace + OSS tool inventory (`pip-audit` + Mend Bolt).

JSON is the default CLI output. Pass `--human` for a table.

```bash
dspm audit inventory
```

Primary OSS tools and honest gaps are listed in the package inventory (`dspm audit inventory`). This module does not add paid APIs, GPUs, or Ollama.
