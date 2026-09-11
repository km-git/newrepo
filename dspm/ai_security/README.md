# dspm/ai_security

Experimental vector-store / prompt-log scanner.

JSON is the default CLI output. Pass `--human` for a table.

```bash
dspm ai-security scan-export examples/prompt_log.jsonl
```

Primary OSS tools and honest gaps are listed in the package inventory (`dspm audit inventory`). This module does not add paid APIs, GPUs, or Ollama.
