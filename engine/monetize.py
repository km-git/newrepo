"""
Monetization Strategy Services — optional broker layer.

License tagging, access control, and royalty reporting for analysis
artifacts and discovery-portfolio bets. Deterministic; no LLM; no money movement.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


LEDGER_PATH = Path(os.environ.get("EW_MONETIZE_LEDGER", "output/system/monetize_ledger.json"))
REPORT_PATH = Path(os.environ.get("EW_MONETIZE_REPORT", "output/system/monetize_latest.json"))
DISCOVERY_PATH = Path(os.environ.get("EW_DISCOVERY_PATH", "discovery-output.md"))

LICENSE_RESEARCH = "research"
LICENSE_PAPER = "paper"
LICENSE_INTERNAL = "internal"
LICENSE_ADVISORY = "advisory"
LICENSE_COMMERCIAL = "commercial"

LICENSE_IDS = (
  LICENSE_RESEARCH,
  LICENSE_PAPER,
  LICENSE_INTERNAL,
  LICENSE_ADVISORY,
  LICENSE_COMMERCIAL,
)

ACTIONS = (
  "view",
  "export",
  "paper_sim",
  "live_exec",
  "third_party_license",
)

VERDICT_BUILD = "BUILD"
VERDICT_HOLD = "HOLD"
VERDICT_CUT = "CUT"

MAX_ACTIVE_BETS = 55
MIN_ACTIVE_BETS = 50
CUT_VALIDATION = 0.25
BUILD_VALIDATION = 0.30

_RANK_RE = re.compile(r"^### Rank (\d+)\s+[—–-]\s+(.+?)\s*$")
_FIELD_RE = re.compile(r"^- \*\*(.+?):\*\*\s+(.*)$")
_MONEY_RE = re.compile(r"(-?[\d,]+(?:\.\d+)?)")
_PCT_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*%")


def monetize_enabled() -> bool:
  return os.environ.get("EW_MONETIZE", "1").lower() not in ("0", "false", "no")


def _utc_now() -> str:
  return datetime.now(timezone.utc).isoformat()


def _env_float(name: str, default: float) -> float:
  raw = os.environ.get(name)
  if raw is None or raw == "":
    return default
  try:
    return float(raw)
  except ValueError:
    return default


def royalty_rate(license_id: str) -> float:
  rates = {
    LICENSE_RESEARCH: _env_float("EW_ROYALTY_RESEARCH", 0.0),
    LICENSE_PAPER: _env_float("EW_ROYALTY_PAPER", 0.0),
    LICENSE_INTERNAL: _env_float("EW_ROYALTY_INTERNAL", 0.0),
    LICENSE_ADVISORY: _env_float("EW_ROYALTY_ADVISORY", 0.05),
    LICENSE_COMMERCIAL: _env_float("EW_ROYALTY_COMMERCIAL", 0.15),
  }
  return float(rates.get(str(license_id or "").lower(), 0.0))


def license_catalog() -> List[Dict[str, Any]]:
  return [
    {
      "id": LICENSE_RESEARCH,
      "label": "Research only",
      "royalty_rate": royalty_rate(LICENSE_RESEARCH),
      "allows": ["view"],
      "notes": "Internal study; no export, paper, live, or third-party reuse",
    },
    {
      "id": LICENSE_PAPER,
      "label": "Paper / simulation",
      "royalty_rate": royalty_rate(LICENSE_PAPER),
      "allows": ["view", "paper_sim"],
      "notes": "Paper and structural proof only; no live or third-party license",
    },
    {
      "id": LICENSE_INTERNAL,
      "label": "Operator internal",
      "royalty_rate": royalty_rate(LICENSE_INTERNAL),
      "allows": ["view", "export", "paper_sim", "live_exec"],
      "notes": "Operator-owned commercial use; live still requires EW_EXECUTE_CONFIRM",
    },
    {
      "id": LICENSE_ADVISORY,
      "label": "Advisory draft",
      "royalty_rate": royalty_rate(LICENSE_ADVISORY),
      "allows": ["view", "export", "paper_sim"],
      "notes": "Human-reviewed drafts; not a live or third-party license",
    },
    {
      "id": LICENSE_COMMERCIAL,
      "label": "Commercial license",
      "royalty_rate": royalty_rate(LICENSE_COMMERCIAL),
      "allows": list(ACTIONS),
      "notes": "Licensed reuse with royalty reporting; live still requires confirm",
    },
  ]


def _allowed_actions(license_id: str) -> Tuple[str, ...]:
  for row in license_catalog():
    if row["id"] == license_id:
      return tuple(row["allows"])
  return ()


def normalize_license(license_id: Any) -> str:
  lid = str(license_id or "").strip().lower()
  return lid if lid in LICENSE_IDS else LICENSE_RESEARCH


def live_confirm_on() -> bool:
  return os.environ.get("EW_EXECUTE_CONFIRM", "0").lower() in ("1", "true", "yes")


def tag_setup_license(artifact: Dict[str, Any]) -> str:
  explicit = str(artifact.get("license") or artifact.get("license_id") or "").strip().lower()
  if explicit in LICENSE_IDS:
    return explicit
  gtc = str(artifact.get("gtc_tier") or "").lower()
  honest = str(artifact.get("honest_execution_tier") or "").lower()
  verdict = str(artifact.get("executive_verdict") or artifact.get("verdict") or "").upper()
  if gtc == "executable" and verdict in {"GO", "CONDITIONAL_GO", "STAGED_GO"}:
    return LICENSE_INTERNAL
  if honest == "probe" or gtc in {"monitor", "watch"}:
    return LICENSE_PAPER
  return LICENSE_RESEARCH


def _category_is_compliance(category: str) -> bool:
  cat = (category or "").lower()
  return "compliance" in cat or "ndis" in cat or "whs" in cat or "legal" in cat


def tag_idea_license(idea: Dict[str, Any]) -> str:
  explicit = str(idea.get("license") or idea.get("license_id") or "").strip().lower()
  if explicit in LICENSE_IDS:
    return explicit
  if _category_is_compliance(str(idea.get("category") or "")):
    return LICENSE_RESEARCH
  verdict = str(idea.get("verdict") or "").upper()
  if verdict == VERDICT_BUILD:
    return LICENSE_COMMERCIAL
  if verdict == VERDICT_HOLD:
    return LICENSE_ADVISORY
  return LICENSE_RESEARCH


def tag_license(artifact: Dict[str, Any]) -> Dict[str, Any]:
  kind = str(artifact.get("kind") or artifact.get("type") or "setup").lower()
  if kind in {"idea", "portfolio", "saas"}:
    license_id = tag_idea_license(artifact)
  else:
    license_id = tag_setup_license(artifact)
  return {
    "artifact_id": artifact.get("id") or artifact.get("name") or artifact.get("symbol") or "unknown",
    "kind": "idea" if kind in {"idea", "portfolio", "saas"} else "setup",
    "license_id": license_id,
    "royalty_rate": royalty_rate(license_id),
    "allows": list(_allowed_actions(license_id)),
  }


def check_access(
  principal: str,
  action: str,
  license_id: str,
  *,
  confirm_live: Optional[bool] = None,
) -> Dict[str, Any]:
  """Deterministic access decision. Does not execute trades or move funds."""
  lid = normalize_license(license_id)
  act = str(action or "").strip().lower()
  who = str(principal or "operator").strip().lower() or "operator"
  allowed = _allowed_actions(lid)
  if act not in ACTIONS:
    return {
      "allow": False,
      "principal": who,
      "action": act,
      "license_id": lid,
      "reason": f"unknown_action:{act}",
    }
  if act not in allowed:
    return {
      "allow": False,
      "principal": who,
      "action": act,
      "license_id": lid,
      "reason": f"license_{lid}_forbids_{act}",
    }
  if act == "live_exec":
    confirmed = live_confirm_on() if confirm_live is None else bool(confirm_live)
    if not confirmed:
      return {
        "allow": False,
        "principal": who,
        "action": act,
        "license_id": lid,
        "reason": "live_exec_requires_EW_EXECUTE_CONFIRM",
      }
  if who == "third_party" and act != "third_party_license" and lid != LICENSE_COMMERCIAL:
    return {
      "allow": False,
      "principal": who,
      "action": act,
      "license_id": lid,
      "reason": "third_party_requires_commercial",
    }
  return {
    "allow": True,
    "principal": who,
    "action": act,
    "license_id": lid,
    "reason": "ok",
  }


def access_matrix() -> List[Dict[str, Any]]:
  rows: List[Dict[str, Any]] = []
  for lic in LICENSE_IDS:
    for action in ACTIONS:
      decision = check_access("operator", action, lic, confirm_live=True)
      rows.append(
        {
          "license_id": lic,
          "action": action,
          "allow": decision["allow"],
          "reason": decision["reason"],
        }
      )
  return rows


def _empty_ledger() -> Dict[str, Any]:
  return {"version": 1, "events": []}


def load_ledger(path: Optional[Path] = None) -> Dict[str, Any]:
  p = path or LEDGER_PATH
  if not p.exists():
    return _empty_ledger()
  try:
    data = json.loads(p.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return _empty_ledger()
  if not isinstance(data, dict):
    return _empty_ledger()
  events = data.get("events")
  if not isinstance(events, list):
    data["events"] = []
  data.setdefault("version", 1)
  return data


def save_ledger(ledger: Dict[str, Any], path: Optional[Path] = None) -> Path:
  p = path or LEDGER_PATH
  p.parent.mkdir(parents=True, exist_ok=True)
  p.write_text(json.dumps(ledger, indent=2, default=str), encoding="utf-8")
  return p


def record_usage(
  artifact_id: str,
  action: str,
  *,
  license_id: str = LICENSE_ADVISORY,
  notional: float = 0.0,
  principal: str = "operator",
  path: Optional[Path] = None,
) -> Dict[str, Any]:
  lid = normalize_license(license_id)
  try:
    notion = float(notional)
  except (TypeError, ValueError):
    notion = 0.0
  if notion < 0:
    notion = 0.0
  rate = royalty_rate(lid)
  event = {
    "timestamp_utc": _utc_now(),
    "artifact_id": str(artifact_id or "unknown"),
    "action": str(action or "view"),
    "license_id": lid,
    "principal": str(principal or "operator"),
    "notional": round(notion, 6),
    "royalty_rate": rate,
    "royalty_due": round(notion * rate, 6),
  }
  ledger = load_ledger(path)
  ledger.setdefault("events", []).append(event)
  save_ledger(ledger, path)
  return event


def royalty_report(ledger: Optional[Dict[str, Any]] = None, path: Optional[Path] = None) -> Dict[str, Any]:
  data = ledger if ledger is not None else load_ledger(path)
  events = list(data.get("events") or [])
  by_license: Dict[str, Dict[str, Any]] = {}
  by_artifact: Dict[str, Dict[str, Any]] = {}
  total_notional = 0.0
  total_royalty = 0.0
  for ev in events:
    lid = normalize_license(ev.get("license_id"))
    aid = str(ev.get("artifact_id") or "unknown")
    notion = float(ev.get("notional") or 0.0)
    due = float(ev.get("royalty_due") or 0.0)
    total_notional += notion
    total_royalty += due
    bucket = by_license.setdefault(lid, {"events": 0, "notional": 0.0, "royalty_due": 0.0})
    bucket["events"] += 1
    bucket["notional"] = round(bucket["notional"] + notion, 6)
    bucket["royalty_due"] = round(bucket["royalty_due"] + due, 6)
    art = by_artifact.setdefault(aid, {"events": 0, "notional": 0.0, "royalty_due": 0.0, "license_id": lid})
    art["events"] += 1
    art["notional"] = round(art["notional"] + notion, 6)
    art["royalty_due"] = round(art["royalty_due"] + due, 6)
  return {
    "event_count": len(events),
    "total_notional": round(total_notional, 6),
    "total_royalty_due": round(total_royalty, 6),
    "by_license": by_license,
    "by_artifact": by_artifact,
  }


def _parse_money(text: str) -> Optional[float]:
  m = _MONEY_RE.search(text.replace(" ", ""))
  if not m:
    return None
  try:
    return float(m.group(1).replace(",", ""))
  except ValueError:
    return None


def _parse_pct(text: str) -> Optional[float]:
  m = _PCT_RE.search(text)
  if not m:
    return None
  try:
    return float(m.group(1)) / 100.0
  except ValueError:
    return None


def _parse_days(text: str) -> Optional[int]:
  m = re.search(r"(\d+)", text)
  if not m:
    return None
  return int(m.group(1))


def parse_discovery_ideas(text: str) -> List[Dict[str, Any]]:
  """Parse ranked ideas from discovery-output.md. Planning estimates only."""
  ideas: List[Dict[str, Any]] = []
  current: Optional[Dict[str, Any]] = None
  for line in text.splitlines():
    header = _RANK_RE.match(line)
    if header:
      if current:
        ideas.append(current)
      current = {
        "kind": "idea",
        "rank": int(header.group(1)),
        "name": header.group(2).strip(),
        "id": header.group(2).strip(),
      }
      continue
    if current is None:
      continue
    field = _FIELD_RE.match(line)
    if not field:
      continue
    key = field.group(1).strip().lower()
    val = field.group(2).strip()
    if key == "category":
      current["category"] = val
    elif key == "pricing aud":
      current["pricing"] = val
    elif key == "conservative y1 midpoint revenue aud":
      current["y1_revenue"] = _parse_money(val)
    elif key == "validation probability":
      current["validation_prob"] = _parse_pct(val)
    elif key == "build days":
      current["build_days"] = _parse_days(val)
    elif key == "first-customer route":
      current["first_customer_route"] = val
    elif key == "risk":
      current["risk"] = val
    elif key == "setup aud":
      current["setup_aud"] = _parse_money(val)
  if current:
    ideas.append(current)
  return ideas


def load_discovery_ideas(path: Optional[Path] = None) -> List[Dict[str, Any]]:
  p = path or DISCOVERY_PATH
  if not p.exists():
    return []
  try:
    return parse_discovery_ideas(p.read_text(encoding="utf-8"))
  except OSError:
    return []


def idea_score(idea: Dict[str, Any]) -> float:
  prob = float(idea.get("validation_prob") or 0.0)
  revenue = float(idea.get("y1_revenue") or 0.0)
  days = max(int(idea.get("build_days") or 1), 1)
  return round((prob * revenue) / days, 4)


def classify_bet(idea: Dict[str, Any]) -> str:
  route = str(idea.get("first_customer_route") or "").strip()
  prob = float(idea.get("validation_prob") or 0.0)
  score = idea_score(idea)
  if not route or prob < CUT_VALIDATION or score <= 0:
    return VERDICT_CUT
  if prob >= BUILD_VALIDATION and score >= 150.0:
    return VERDICT_BUILD
  return VERDICT_HOLD


def _score_key(row: Dict[str, Any]) -> Tuple[float, int]:
  return (float(row.get("score") or 0.0), -int(row.get("rank") or 999))


def recommend_bets(ideas: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
  """Score portfolio ideas and apply 50–55 bet / 7-day cut rules."""
  scored: List[Dict[str, Any]] = []
  for raw in ideas:
    row = dict(raw)
    row["score"] = idea_score(row)
    row["verdict"] = classify_bet(row)
    row["license_id"] = tag_idea_license(row)
    scored.append(row)
  scored.sort(key=lambda r: (-float(r.get("score") or 0.0), int(r.get("rank") or 999)))
  builds = [r for r in scored if r["verdict"] == VERDICT_BUILD]
  if len(builds) > MAX_ACTIVE_BETS:
    for extra in builds[MAX_ACTIVE_BETS:]:
      extra["verdict"] = VERDICT_HOLD
      extra["license_id"] = tag_idea_license(extra)
      extra["cap_reason"] = f"over_{MAX_ACTIVE_BETS}_build_cap"
  active = [r for r in scored if r["verdict"] in {VERDICT_BUILD, VERDICT_HOLD}]
  overflow = len(active) - MAX_ACTIVE_BETS
  if overflow > 0:
    # 7-day cut: drop the weakest active bets first (HOLD before BUILD).
    holds = sorted(
      [r for r in active if r["verdict"] == VERDICT_HOLD],
      key=_score_key,
    )
    extras = sorted(
      [r for r in active if r["verdict"] == VERDICT_BUILD],
      key=_score_key,
    )
    for extra in (holds + extras)[:overflow]:
      extra["verdict"] = VERDICT_CUT
      extra["license_id"] = tag_idea_license(extra)
      extra["cap_reason"] = extra.get("cap_reason") or "7-day_cut_over_55_bets"
  return scored


def friday_review(ideas: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
  ranked = recommend_bets(ideas)
  by_verdict = {VERDICT_BUILD: 0, VERDICT_HOLD: 0, VERDICT_CUT: 0}
  for row in ranked:
    by_verdict[row["verdict"]] = by_verdict.get(row["verdict"], 0) + 1
  cuts = [r for r in ranked if r["verdict"] == VERDICT_CUT]
  builds = [r for r in ranked if r["verdict"] == VERDICT_BUILD]
  return {
    "rule": "50-55 bets | 7-day cut | Friday review | BUILD not just plan",
    "idea_count": len(ranked),
    "by_verdict": by_verdict,
    "active_bets": by_verdict[VERDICT_BUILD] + by_verdict[VERDICT_HOLD],
    "within_bet_band": MIN_ACTIVE_BETS <= (by_verdict[VERDICT_BUILD] + by_verdict[VERDICT_HOLD]) <= MAX_ACTIVE_BETS
    if ranked
    else True,
    "top_builds": [
      {"name": r.get("name"), "rank": r.get("rank"), "score": r.get("score"), "license_id": r.get("license_id")}
      for r in builds[:10]
    ],
    "cut_queue": [
      {"name": r.get("name"), "rank": r.get("rank"), "score": r.get("score"), "reason": "7-day cut review"}
      for r in cuts[:15]
    ],
  }


def tag_artifacts(artifacts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
  return [tag_license(a) for a in artifacts]


def run_monetize_report(
  *,
  persist: bool = True,
  discovery_path: Optional[Path] = None,
  ledger_path: Optional[Path] = None,
  artifacts: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
  if not monetize_enabled():
    return {"skipped": True, "reason": "EW_MONETIZE disabled"}
  ideas = load_discovery_ideas(discovery_path)
  review = friday_review(ideas)
  tagged_ideas = tag_artifacts([{**i, "kind": "idea"} for i in recommend_bets(ideas)])
  tagged_setups = tag_artifacts(artifacts or [])
  royalties = royalty_report(path=ledger_path)
  report = {
    "module": "monetize",
    "label": "Monetization Strategy Services",
    "timestamp_utc": _utc_now(),
    "enabled": True,
    "money_movement": False,
    "licenses": license_catalog(),
    "access_matrix": access_matrix(),
    "royalties": royalties,
    "portfolio": review,
    "tagged_ideas": tagged_ideas[:20],
    "tagged_setups": tagged_setups,
    "discovery_ideas": len(ideas),
  }
  if persist:
    save_monetize_report(report)
  return report


def save_monetize_report(report: dict, path: Optional[Path] = None) -> Path:
  p = path or REPORT_PATH
  p.parent.mkdir(parents=True, exist_ok=True)
  p.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
  return p
