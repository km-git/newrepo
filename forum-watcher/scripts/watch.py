#!/usr/bin/env python3
"""Weekly forum watcher: fetch, dedupe, classify, write discoveries markdown."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "sources.yaml"
BLOCKLIST_PATH = ROOT / "blocklist.yaml"
STATE_DIR = ROOT / "state"
STATE = STATE_DIR / "seen.json"
OUT = ROOT / "discoveries"
USER_AGENT = "t2c-forum-watcher/1.0 (free; +https://github.com/km-git/newrepo)"

MODULES = (
    "audit, analytics, vtl-cloud, restore, disk-ingest, email-extract, "
    "email-migrate, tape-duplicate, media-ingest, tape-ops, tape-saas, "
    "tape-vault, destroy, llm-corpus, ml-enrich, monetize"
)
MODULE_LIST = [m.strip() for m in MODULES.split(",")]

# Free-tier classification: Flash-Lite is 15 RPM / 1,000 RPD; Flash is 10 RPM / 250 RPD.
CLASSIFY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
CLASSIFY_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{CLASSIFY_MODEL}:generateContent"
)
DISCOVER_THRESHOLD = int(os.environ.get("DISCOVER_THRESHOLD", "7"))


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def load_seen() -> set[str]:
    if not STATE.exists():
        return set()
    data = json.loads(STATE.read_text())
    return set(data) if isinstance(data, list) else set()


def load_blocklist() -> list[str]:
    if not BLOCKLIST_PATH.exists():
        return []
    data = yaml.safe_load(BLOCKLIST_PATH.read_text()) or []
    if isinstance(data, dict):
        data = data.get("keywords", [])
    return [str(x).lower() for x in data]


def blocked(title: str, summary: str, keywords: list[str]) -> bool:
    blob = f"{title} {summary}".lower()
    return any(kw in blob for kw in keywords if kw)


def parse_rss(text: str, src: dict) -> list[dict]:
    feed = feedparser.parse(text)
    items: list[dict] = []
    for entry in feed.entries[: src.get("max_items", 25)]:
        url = entry.get("link") or entry.get("id")
        if not url:
            continue
        items.append(
            {
                "source": src["name"],
                "title": entry.get("title", "(no title)"),
                "url": url,
                "summary": (entry.get("summary") or entry.get("description") or "")[:600],
                "published": entry.get("published", "") or entry.get("updated", ""),
                "module_hint": src.get("module_hint", ""),
            }
        )
    return items


def parse_algolia(payload: dict, src: dict) -> list[dict]:
    items: list[dict] = []
    for hit in payload.get("hits", [])[: src.get("max_items", 25)]:
        object_id = hit.get("objectID")
        url = hit.get("url") or (
            f"https://news.ycombinator.com/item?id={object_id}" if object_id else None
        )
        if not url:
            continue
        items.append(
            {
                "source": src["name"],
                "title": hit.get("title", "(no title)"),
                "url": url,
                "summary": (hit.get("story_text") or hit.get("title") or "")[:600],
                "published": str(hit.get("created_at", "")),
                "module_hint": src.get("module_hint", ""),
            }
        )
    return items


def parse_se(payload: dict, src: dict) -> list[dict]:
    items: list[dict] = []
    for question in payload.get("items", [])[: src.get("max_items", 25)]:
        url = question.get("link")
        if not url:
            continue
        items.append(
            {
                "source": src["name"],
                "title": question.get("title", "(no title)"),
                "url": url,
                "summary": "tags: " + ",".join(question.get("tags") or []),
                "published": str(question.get("last_activity_date", "")),
                "module_hint": src.get("module_hint", ""),
            }
        )
    return items


def fetch_source(client: httpx.Client, src: dict) -> list[dict]:
    kind = src.get("kind", "rss")
    response = client.get(src["url"])
    response.raise_for_status()
    if kind == "algolia":
        return parse_algolia(response.json(), src)
    if kind == "se-api":
        return parse_se(response.json(), src)
    return parse_rss(response.text, src)


def heuristic_classify(item: dict) -> dict:
    """Keyword fallback when GEMINI_API_KEY is unset or the API fails."""
    blob = f"{item['title']} {item['summary']}".lower()
    module = "unknown"
    fit = 0
    for name in MODULE_LIST:
        token = name.replace("-", " ")
        if name in blob or token in blob:
            module = name
            fit = 3
            break
    if fit == 0:
        hints = [h.strip() for h in str(item.get("module_hint", "")).split(",") if h.strip()]
        matched = [h for h in hints if h.replace("-", " ") in blob or h in blob]
        if matched:
            module = matched[0]
            fit = 2
        elif hints:
            module = hints[0]
            fit = 0
    action = 3 if any(k in blob for k in ("github.com", "pip install", "how to", "library")) else 1
    trust = 2 if item.get("source", "").startswith(("borg", "kopia", "restic", "velero", "SO ")) else 1
    score = min(12, fit + action + 2 + trust)
    if score >= DISCOVER_THRESHOLD:
        verdict = "discover"
    elif score >= 5:
        verdict = "watch"
    else:
        verdict = "skip"
    return {
        "module": module,
        "score": score,
        "verdict": verdict,
        "reason": "heuristic fallback",
    }


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def llm_classify(item: dict) -> dict:
    prompt = f"""You are filtering a weekly forum scan for a tape-to-cloud migration tool.
Modules: {MODULES}
Hint (bias module-fit toward these): {item.get('module_hint') or 'none'}

Score this item on four axes, each 0-3, then total 0-12:
- module-fit: does it touch any of the 16 modules? (0=off-topic, 3=core)
- actionability: can the operator act in under 30 minutes? (0=pure discussion, 3=working code)
- freshness: published within (0=>30d, 1=8-30d, 2=2-7d, 3=<24h)
- source-trust: (0=personal blog, 3=releases feed or tagged wiki)

Return ONLY a JSON object:
{{"module":"<one of 16 or unknown>","score":<0-12>,"verdict":"discover|watch|skip","reason":"<8 words max>"}}
Discover if score >= {DISCOVER_THRESHOLD}, watch if 5-6, skip if <= 4.

Title: {item['title']}
Source: {item['source']}
URL: {item['url']}
Summary: {item['summary']}"""
    response = httpx.post(
        CLASSIFY_URL,
        params={"key": os.environ["GEMINI_API_KEY"]},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    response.raise_for_status()
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    parsed = _extract_json(text)
    score = int(parsed.get("score", 0))
    verdict = parsed.get("verdict", "skip")
    if verdict not in {"discover", "watch", "skip"}:
        if score >= DISCOVER_THRESHOLD:
            verdict = "discover"
        elif score >= 5:
            verdict = "watch"
        else:
            verdict = "skip"
    parsed["score"] = score
    parsed["verdict"] = verdict
    parsed["module"] = parsed.get("module") or "unknown"
    parsed["reason"] = parsed.get("reason") or ""
    return parsed


def classify(item: dict) -> dict:
    if not os.environ.get("GEMINI_API_KEY"):
        return heuristic_classify(item)
    try:
        return llm_classify(item)
    except Exception as exc:  # noqa: BLE001 — weekly job must not die on one item
        fallback = heuristic_classify(item)
        fallback["reason"] = f"classifier error: {exc}"
        return fallback


def render_markdown(today: str, classified: list[dict]) -> str:
    discoveries = [i for i in classified if i["classification"]["verdict"] == "discover"]
    watches = [i for i in classified if i["classification"]["verdict"] == "watch"]
    skipped = len(classified) - len(discoveries) - len(watches)
    lines = [
        f"# Discoveries — week of {today}",
        "",
        f"**{len(discoveries)} discover · {len(watches)} watch · {skipped} skip**",
        "",
    ]
    for verdict, items in (("discover", discoveries), ("watch", watches)):
        if not items:
            continue
        lines.append(f"## {verdict.title()} ({len(items)})")
        lines.append("")
        for item in items:
            c = item["classification"]
            lines.append(
                f"- [ ] **[{c.get('module', '?')}]** [{item['title']}]({item['url']})  "
            )
            lines.append(
                f"  {item['source']} · score {c.get('score', '?')} · {c.get('reason', '')}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run() -> int:
    sources = yaml.safe_load(SOURCES_PATH.read_text()) or []
    keywords = load_blocklist()
    seen = load_seen()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    new_items: list[dict] = []
    with httpx.Client(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for index, src in enumerate(sources):
            if index:
                delay = 8.0 if "reddit.com" in src.get("url", "") else 1.5
                time.sleep(delay)
            try:
                fetched = fetch_source(client, src)
            except Exception as exc:  # noqa: BLE001 — one dead source must not fail the week
                print(f"[skip] {src.get('name')}: {exc}")
                continue
            for item in fetched:
                if blocked(item["title"], item["summary"], keywords):
                    continue
                digest = url_hash(item["url"])
                if digest in seen:
                    continue
                seen.add(digest)
                new_items.append(item)

    if not new_items:
        print("no new items")
        STATE.write_text(json.dumps(sorted(seen), indent=2) + "\n")
        return 0

    classified: list[dict] = []
    batch = 10
    for index, item in enumerate(new_items):
        if index and index % batch == 0 and os.environ.get("GEMINI_API_KEY"):
            time.sleep(60)
        item["classification"] = classify(item)
        classified.append(item)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (OUT / f"{today}.md").write_text(render_markdown(today, classified))
    STATE.write_text(json.dumps(sorted(seen), indent=2) + "\n")
    discoveries = sum(1 for i in classified if i["classification"]["verdict"] == "discover")
    watches = sum(1 for i in classified if i["classification"]["verdict"] == "watch")
    print(f"wrote {discoveries} discover, {watches} watch")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
