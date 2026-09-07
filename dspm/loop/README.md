# dspm/loop

5-stage Discover → Evaluate → Integrate → Validate → Compound.

```bash
dspm loop improve          # forums + GitHub search fixture + PyPI + gap-audit
dspm loop gap-audit        # catalog self-challenge (github / pypi / other tools)
dspm loop watch --fetch    # live RSS (optional)
```

Sources: `sources.yaml` (Reddit, HN, Lobsters, Track Awesome List, GitHub Releases, PyPI RSS).
Catalog: `catalog.yaml` (forums, GitHub tools, other tools, Python libs) with honest missing/partial status.
Rubric: 4-axis (module-fit, signal, license, actionability), threshold ≥ 7.
No paid APIs, no GPU, no Ollama.
