"""Forum watcher: Discover slot of the 5-stage loop. SHA-256 URL dedupe."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import yaml

from cost.loop.classify import classify_item

SOURCES_PATH = Path(__file__).with_name("sources.yaml")
STATE_PATH = Path(os.environ.get("COST_SEEN", "state/seen.json"))
ACCEPT_LOG = Path(os.environ.get("COST_ACCEPT_LOG", "state/accept-reject.jsonl"))

COST_CONTEXT = """
Cost context (for vendor and OSS-tool sources only):
- FinOps = Financial Operations, the practice of managing cloud spend (FinOps Foundation)
- CSPM = Cloud Security Posture Management (Wiz, Orca, Prisma Cloud) — NOT this build's focus
- Prowler = open-source cloud configuration scanner, Apache-2.0, v5.41.0 in Sep 2026
- Steampipe = SQL over cloud APIs, AGPL-3.0, must be used as CLI subprocess only
- Cloud Custodian = policy-as-code, Apache-2.0, supports AWS/Azure/GCP/Kubernetes
- c7n-org = multi-account runner for Cloud Custodian, Apache-2.0
- AWS Cost Explorer = free with customer's own AWS account
- Azure Cost Management = free with customer's own Azure subscription
- GCP Cloud Billing = free with customer's own GCP project
- Trivy = IaC + image + secret scanner, v0.71.2 (avoid v0.69.4 — CVE-2026-33634)

Disallowed report language: use "cost observation", "configuration reference", "framework reference" instead.
"""


def canonical_url(url: str) -> str:
    return (url or "").strip().split("#")[0].rstrip("/")


def url_digest(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode("utf-8")).hexdigest()


def load_sources(path: Path | None = None) -> list[dict[str, Any]]:
    raw = yaml.safe_load((path or SOURCES_PATH).read_text(encoding="utf-8")) or []
    return list(raw)


def load_seen(path: Path | None = None) -> dict[str, Any]:
    target = path or STATE_PATH
    if not target.exists():
        return {"items": {}}
    return json.loads(target.read_text(encoding="utf-8"))


def save_seen(state: dict[str, Any], path: Path | None = None) -> None:
    target = path or STATE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _tag(block: str, name: str) -> str:
    match = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, flags=re.I | re.S)
    if not match:
        match = re.search(rf"<{name}[^>]*href=[\"']([^\"']+)", block, flags=re.I)
        return match.group(1).strip() if match else ""
    text = re.sub(r"<[^>]+>", "", match.group(1))
    return text.replace("<![CDATA[", "").replace("]]>", "").strip()


def parse_rss(text: str, *, max_items: int) -> list[dict[str, str]]:
    items = []
    for block in re.findall(r"<item>(.*?)</item>", text, flags=re.I | re.S):
        link = _tag(block, "link") or _tag(block, "guid")
        title = _tag(block, "title")
        summary = _tag(block, "description")[:600]
        if not link:
            continue
        items.append({"url": link, "title": title, "summary": summary})
        if len(items) >= max_items:
            break
    if items:
        return items
    for block in re.findall(r"<entry>(.*?)</entry>", text, flags=re.I | re.S):
        link = _tag(block, "link") or _tag(block, "id")
        title = _tag(block, "title")
        summary = (_tag(block, "summary") or _tag(block, "content"))[:600]
        if not link:
            continue
        items.append({"url": link, "title": title, "summary": summary})
        if len(items) >= max_items:
            break
    return items


def fetch_text(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "cost-watcher/0.1"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def watch(
    *,
    mode: str = "all",
    fetch: bool = False,
    sources_path: Path | None = None,
    seen_path: Path | None = None,
    fixture_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sources = load_sources(sources_path)
    seen = load_seen(seen_path)
    known = set((seen.get("items") or {}).keys())
    discovered: list[dict[str, Any]] = []
    raw_items: list[dict[str, Any]] = list(fixture_items or [])
    if fetch and fixture_items is None:
        for source in sources:
            if mode != "all":
                kind = "vendor" if "releases.atom" in source["url"] else "community"
                if mode != kind:
                    continue
            try:
                body = fetch_text(source["url"])
            except Exception as exc:
                discovered.append({"source": source["name"], "error": str(exc)})
                continue
            if source.get("kind") == "json":
                payload = json.loads(body)
                hits = payload.get("hits") or payload.get("items") or []
                parsed = [
                    {
                        "url": hit.get("url") or hit.get("objectID") or "",
                        "title": hit.get("title") or "",
                        "summary": (hit.get("story_text") or "")[:600],
                    }
                    for hit in hits[: int(source.get("max_items") or 15)]
                ]
            else:
                parsed = parse_rss(body, max_items=int(source.get("max_items") or 15))
            for item in parsed:
                item["source"] = source["name"]
                item["module_hint"] = source.get("module_hint") or ""
                raw_items.append(item)
    elif fixture_items is None:
        # Offline Discover item so CI can prove the watcher path without network.
        raw_items.append(
            {
                "url": "https://github.com/data-privacy-stack/presidio/releases/tag/2.2.360",
                "title": "Presidio 2.2.360 released (data-privacy-stack)",
                "summary": "PII recognizer updates; install from data-privacy-stack/presidio not microsoft/presidio.",
                "source": "Presidio releases",
                "module_hint": "cost/classification",
            }
        )

    new_items = []
    for item in raw_items:
        digest = url_digest(item.get("url") or "")
        if not digest or digest in known:
            continue
        verdict = classify_item(item, cost_context=COST_CONTEXT)
        record = {**item, "sha256": digest, **verdict}
        new_items.append(record)
        known.add(digest)
        seen.setdefault("items", {})[digest] = {
            "url": canonical_url(item.get("url") or ""),
            "title": item.get("title"),
            "verdict": verdict["verdict"],
        }
    save_seen(seen, seen_path)
    log_path = Path(os.environ.get("COST_ACCEPT_LOG", str(ACCEPT_LOG)))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        for item in new_items:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    return {
        "mode": mode,
        "new_count": len(new_items),
        "items": new_items,
        "seen": len(seen.get("items") or {}),
    }
