# Simplest Bugbot Replacement: Ruff + PR-Agent (or CodeRabbit Free)

Use what you already have first, then add one free Python library and one free GitHub tool. That's the whole thing.

---

## 1. What Cursor already gives you (no setup)

- **Tab completion** — unlimited, doesn't burn credits. Use it.
- **Auto mode** — unlimited on Pro/Pro+/Ultra. Routes routine work to cheap models. Doesn't review PRs, but covers the in-editor half of what Bugbot does.
- **Bugbot itself** — already part of Cursor. The "usage limit reached" email means your individual/team cap fired, not that the tool is gone. When you have credits, it works.
- **`/review` command** in Cursor 3.7+ — runs Bugbot + Security Review *before* you push, so a Bugbot hit is essentially free during dev. Use this and the cap rarely matters in practice.

So: **use Bugbot via `/review` before pushing** to stay ahead of the cap.

---

## 2. The one Python library to add: Ruff

Free, MIT, ~0.2s on 50k LOC, catches `eval`, hardcoded secrets patterns, undefined names, mutable defaults, and a Bandit-compatible security subset. No LLM, no API key, no infra. Install as a pre-commit hook:

```bash
pip install ruff pre-commit
```

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix, --select, "E,F,W,I,UP,B,SIM,RUF,S"]
      - id: ruff-format
```

That `S` is the Bandit-equivalent security ruleset. Zero setup, catches ~70% of "real bugs" Bugbot would flag, runs in 200ms.

If you want one more: add `gitleaks` (`pip install gitleaks` via the GitHub Action — catches leaked API keys in diffs). Still free, still no LLM.

---

## 3. The one free GitHub tool for AI PR review: PR-Agent

Apache 2.0, BYOK (OpenAI or Anthropic key), installs as a GitHub Action in 5 minutes. Free except for the model call, which on `gpt-4o-mini` runs ~$0.01–$0.05 per PR.

`.github/workflows/pr-agent.yml`:

```yaml
name: PR Agent
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  pr_agent:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: qodo-ai/pr-agent@main
        env:
          OPENAI_KEY: ${{ secrets.OPENAI_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          github_action_config.auto_review: "true"
          github_action_config.auto_describe: "true"
          github_action_config.auto_improve: "true"
```

That replaces the Bugbot narrative on every PR. If you don't have a model key, comment `@CodiumAI-Agent /review` on the PR — free for public repos, no setup.

---

## 4. Or: CodeRabbit (zero setup, zero keys)

If you want zero-config and don't mind the rate limit (~4 PRs/hr on the free tier, unlimited public + private repos): install **CodeRabbit** from the GitHub Marketplace in two clicks. No API key, no workflow file, no Python. It's the closest "drop-in" to Bugbot's "just works" feel.

---

## The 5-Minute Setup (do this today)

1. **Ruff pre-commit hook** — 2 minutes, catches most real bugs locally before the PR exists.
2. **Bugbot via `/review`** — already in Cursor 3.7+, no install, dodge the cap.
3. **PR-Agent GitHub Action** — 5 minutes, BYOK, gives the AI narrative on every PR.

That's the whole thing. No GPU, no Ollama, no 8-layer cake, no self-hosting. Ruff + PR-Agent + Bugbot-when-you-have-credits covers the same surface as Bugbot alone, for $0 of dedicated tooling cost.

---

## 5. Zero-key GitHub-native scanners (use these when Bugbot is capped)

Cursor Bugbot is usage-metered. When it skips, do **not** retry it. This public repo can run GitHub's own tools for free:

1. **CodeQL** (`.github/workflows/bugbot-free.yml`) — GitHub code scanning, Python + Actions, `security-and-quality`. Free on public repos. SHA-pinned to `github/codeql-action` v4.37.9.
2. **Semgrep Community Edition** — `p/python` + `p/security-audit`, no Semgrep App token. SARIF uploaded to the Security tab.
3. **reviewdog** — posts Semgrep findings as inline PR review comments with `GITHUB_TOKEN` (no LLM key). SHA-pinned `reviewdog/action-setup` v1.5.0, reviewdog CLI v0.21.0.
4. **Ruff `--output-format=github`** — native PR annotations from the existing lint-security workflow.

Do not install random BYOK review bots that need OpenAI/Anthropic keys. Do not pin `aquasecurity/trivy-action` by mutable tag (TeamPCP supply-chain lesson). First-party `actions/*` stay ref-pinned like the rest of this repo; third-party actions are SHA-pinned.

---

## References

[1] Cursor docs — Bugbot (capabilities and `/review` command in Cursor 3.7+). https://cursor.com/docs/bugbot and https://cursor.com/blog/bugbot-updates-june-2026

[2] GitHub — The-PR-Agent/pr-agent (Apache 2.0, BYOK, GitHub Action install). https://github.com/The-PR-Agent/pr-agent

[3] Ruff — official docs and pre-commit integration. https://docs.astral.sh/ruff/ and https://github.com/astral-sh/ruff-pre-commit

[4] CodeRabbit docs — Free plan covers unlimited public + private repos, ~4 PRs/hr rate limit. https://docs.coderabbit.ai/management/plans
