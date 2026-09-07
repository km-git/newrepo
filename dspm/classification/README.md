# dspm/classification

PII/PHI/PCI classification (Presidio-compatible recognizers).

JSON is the default CLI output. Pass `--human` for a table.

```bash
dspm classify examples/sample.csv
```

Primary OSS tools and honest gaps are listed in the package inventory (`dspm audit inventory`). This module does not add paid APIs, GPUs, or Ollama.
