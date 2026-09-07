"""5-stage loop: reuse forum-watcher, classify unused seats, monthly rollup.

Discover = watcher + SDK releases. Evaluate >= 7. Integrate Monday.
Validate pytest (hash emails). Compound = monthly unused-seat $ trend.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

from licensespend.constants import COMMERCIAL_SKIP, ROOT
from licensespend.loop.models import ClassifyResult, MonthlyRollup
from licensespend.usage.service import load_pricebook, unused_seats

WATCH_PATH = ROOT / "forum-watcher" / "scripts" / "watch.py"
MONTHLY_PATH = ROOT / "monthly" / "license-spend.md"
STATE_DIR = Path(__file__).resolve().parent.parent / "state"
DISCOVER_THRESHOLD = 7

CLASSIFY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
CLASSIFY_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{CLASSIFY_MODEL}:generateContent"


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def skip_commercial(title: str, summary: str = "") -> bool:
    blob = f"{title} {summary}".lower()
    return any(name in blob for name in COMMERCIAL_SKIP)


def load_watcher():
    spec = importlib.util.spec_from_file_location("forum_watch", WATCH_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("forum-watcher/scripts/watch.py missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def watch() -> dict:
    """Delegate Discover to the existing forum-watcher. Do not reimplement it."""
    watcher = load_watcher()
    code = watcher.run()
    return {"ok": code == 0, "reused": "forum-watcher/scripts/watch.py"}


def classify_finding(
    *,
    sku: str,
    idle_days: int,
    user_id_hash: str,
    finding_id: str | None = None,
) -> ClassifyResult:
    """Gemini Flash optional. Input is sku + idle_days + hashed user id. No raw email."""
    if "@" in user_id_hash:
        raise ValueError("do not send unhashed emails to an LLM")
    prices = load_pricebook()
    fid = finding_id or f"ls-{user_id_hash[:12]}"
    if sku not in prices:
        return ClassifyResult(
            finding_id=fid,
            client_summary="Unknown SKU; abstain from reclaim dollar estimate.",
            reclaim_aud=None,
            confidence="low",
            abstain=True,
            reason="sku unknown in pricebook",
        )
    monthly = float(prices[sku].monthly_aud)
    summary = (
        f"Hashed seat {user_id_hash[:12]} idle {idle_days}d on {prices[sku].name}; draft reclaim A${monthly:.0f}/mo."
    )
    result = ClassifyResult(
        finding_id=fid,
        client_summary=summary[:400],
        reclaim_aud=monthly,
        confidence="high" if idle_days >= 90 else "medium",
    )
    if not os.environ.get("GEMINI_API_KEY"):
        return result
    try:
        import httpx

        prompt = (
            "Return ONLY JSON with keys finding_id, client_summary (<=40 words), "
            "reclaim_aud, confidence (low|medium|high), human_action. "
            f"sku={sku} idle_days={idle_days} user_id_hash={user_id_hash} "
            f"monthly_aud={monthly}. human_action must be 'draft email to manager, do not revoke'."
        )
        response = httpx.post(
            CLASSIFY_URL,
            params={"key": os.environ["GEMINI_API_KEY"]},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        parsed = json.loads(cleaned)
        conf = parsed.get("confidence")
        allowed = conf if conf in {"low", "medium", "high"} else "medium"
        return ClassifyResult(
            finding_id=str(parsed.get("finding_id") or fid),
            client_summary=str(parsed.get("client_summary") or summary)[:400],
            reclaim_aud=float(parsed.get("reclaim_aud") or monthly),
            confidence=allowed,
            human_action=str(parsed.get("human_action") or result.human_action),
        )
    except Exception as exc:  # noqa: BLE001 — classify must abstain, not crash
        result.reason = f"classifier fallback: {exc}"
        result.confidence = "medium"
        return result


def is_mechanical_issue(title: str, body: str, labels: list[str]) -> dict:
    blob = f"{title}\n{body}".lower()
    if "good first issue" not in [label.lower() for label in labels]:
        return {"eligible": False, "reason": "not good first issue"}
    if "graph" in blob and "permission" in blob:
        return {"eligible": False, "reason": "Graph permission changes are operator-owned"}
    if "pricebook" in blob and ("aud" in blob or "price" in blob):
        return {"eligible": False, "reason": "pricebook AUD amounts are operator-owned"}
    return {"eligible": True, "reason": "mechanical"}


def monthly(*, as_of: date | None = None, fixture_root: Path | None = None) -> MonthlyRollup:
    as_of = as_of or date(2026, 9, 7)
    unused = unused_seats(fixture_root=fixture_root, idle_days=90, as_of=as_of)
    rollup = MonthlyRollup(
        as_of=as_of.isoformat(),
        reclaim_monthly_aud=unused.reclaim_monthly_aud,
        unused_count=unused.unused_count,
        trend=[{"as_of": as_of.isoformat(), "reclaim_monthly_aud": unused.reclaim_monthly_aud}],
    )
    MONTHLY_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# License spend — {as_of.isoformat()}",
        "",
        f"Unused seats: **{unused.unused_count}**. Monthly reclaim: **A${unused.reclaim_monthly_aud:.2f}**.",
        "",
        "Compound metric: unused-seat dollar trend (fixture path).",
        "",
        f"Generated {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}.",
        "",
    ]
    MONTHLY_PATH.write_text("\n".join(lines), encoding="utf-8")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "monthly.json").write_text(
        json.dumps(rollup.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return rollup
