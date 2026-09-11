# dspm/compliance

Hand-maintained GDPR/HIPAA/PCI/SOC2 control mapping.

JSON is the default CLI output. Pass `--human` for a table.

```bash
dspm compliance map --framework gdpr
```

Primary OSS tools and honest gaps are listed in the package inventory (`dspm audit inventory`). This module does not add paid APIs, GPUs, or Ollama.
