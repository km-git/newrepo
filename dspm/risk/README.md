# dspm/risk

DuckDB-equivalent SQL risk scoring over findings ∪ exposures.

JSON is the default CLI output. Pass `--human` for a table.

```bash
dspm risk score --since 7d
```

Primary OSS tools and honest gaps are listed in the package inventory (`dspm audit inventory`). This module does not add paid APIs, GPUs, or Ollama.
