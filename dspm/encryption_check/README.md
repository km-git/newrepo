# dspm/encryption_check

At-rest/in-flight encryption checks via Trivy v0.71.2+.

JSON is the default CLI output. Pass `--human` for a table.

```bash
dspm encryption-check terraform/
```

Primary OSS tools and honest gaps are listed in the package inventory (`dspm audit inventory`). This module does not add paid APIs, GPUs, or Ollama.
