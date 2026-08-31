#!/usr/bin/env python3
"""Elliott Wave + Harmonic confluence trading analysis CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from engine.llm_backend import bootstrap_llm_env

bootstrap_llm_env()

from schemas.models import ElliottWaveOutput


def main() -> None:
  parser = argparse.ArgumentParser(description="Elliott Wave + Harmonic confluence tool")
  parser.add_argument("--symbol", help="e.g., BTC/USDT, ES=F, EURUSD=X")
  parser.add_argument("--tfs", default="1w,1d,4h,1h,15m", help="Comma-separated timeframes")
  parser.add_argument("--crypto", action="store_true", help="Use ccxt instead of yfinance")
  parser.add_argument("--save", default=None, help="Path to save JSON output")
  parser.add_argument("--batch", default=None, help="Path to CSV with symbols for batch run")
  parser.add_argument("--top", type=int, default=None, help="Run top N crypto USDT pairs (e.g. 50)")
  parser.add_argument("--quote", default="USDT", help="Quote for --top (default USDT)")
  parser.add_argument("--output-dir", default="output", help="Output dir for --top batch")
  parser.add_argument("--outcomes-only", action="store_true", help="Print step8 outcomes JSON only")
  parser.add_argument("--cache-stats", action="store_true", help="Print cache stats after run")
  parser.add_argument("--clear-cache", action="store_true", help="Clear cache before run")
  parser.add_argument("--gateway-stats", action="store_true", help="Print semantic gateway cache stats")
  parser.add_argument(
    "--llm-advisory",
    action="store_true",
    help="Consult multi-model AI panel on critical decisions (Cursor Pro via CURSOR_API_KEY)",
  )
  parser.add_argument(
    "--llm-cost",
    action="store_true",
    help="Print typical critical-advisory cost comparison and exit",
  )
  parser.add_argument(
    "--llm-tasks",
    action="store_true",
    help="Print task→model→token routing matrix and exit",
  )
  parser.add_argument(
    "--llm-savers",
    action="store_true",
    help="Print token-saving playbook (per-model budget, cache, libraries) and exit",
  )
  parser.add_argument(
    "--install-token-savers",
    action="store_true",
    help="pip install missing token-saving libraries (tiktoken, llm-token-optimizer, etc.)",
  )
  parser.add_argument(
    "--setup",
    action="store_true",
    help="Auto-install Python libs, GitHub EW tools, token savers, and gh CLI",
  )
  parser.add_argument(
    "--pr-approve",
    type=int,
    metavar="N",
    help="Run multi-model executive consensus on PR N — auto-approve/merge when GO",
  )
  parser.add_argument(
    "--pr-dry-run",
    action="store_true",
    help="With --pr-approve: decision only, no GitHub approve/merge",
  )
  parser.add_argument(
    "--pr-approve-all",
    action="store_true",
    help="Run executive consensus on all open PRs",
  )
  parser.add_argument(
    "--pr-resolve-conflicts",
    type=int,
    nargs="?",
    const=0,
    metavar="N",
    help="Auto-resolve merge conflicts for PR N (omit N with flag alone for all open PRs)",
  )
  parser.add_argument(
    "--resolve-conflicts",
    type=int,
    metavar="N",
    help="Alias for --pr-resolve-conflicts N",
  )
  parser.add_argument(
    "--resolve-conflicts-all",
    action="store_true",
    help="Alias for --pr-resolve-conflicts (all open PRs)",
  )
  parser.add_argument(
    "--brain-ask",
    metavar="QUESTION",
    help="Query OKF secondary brain with multi-model consensus",
  )
  parser.add_argument(
    "--brain-search",
    metavar="QUERY",
    help="Search OKF brain concepts",
  )
  parser.add_argument(
    "--brain-status",
    action="store_true",
    help="Show OKF secondary brain index and concept counts",
  )
  parser.add_argument(
    "--execute",
    action="store_true",
    help="Execute executable limit orders from export CSV (paper default)",
  )
  parser.add_argument(
    "--execute-live",
    action="store_true",
    help="Live execution (requires EW_EXECUTE_CONFIRM=1 + API keys)",
  )
  parser.add_argument(
    "--execution-status",
    action="store_true",
    help="Show broker, proxy, WS, risk halt status",
  )
  parser.add_argument(
    "--portfolio-risk",
    action="store_true",
    help="Show portfolio heat, cluster exposure, and hedge status",
  )
  parser.add_argument(
    "--effectiveness",
    action="store_true",
    help="Run full effectiveness validation (win rate, paper P&L, fitness gates)",
  )
  parser.add_argument(
    "--data-intel",
    metavar="SYMBOL",
    help="Fetch WS + web intel snapshot for symbol",
  )
  parser.add_argument(
    "--social-validate",
    nargs="?",
    const="",
    metavar="SYMBOL",
    help="Validate forum/social strategies via executive consensus (optional symbol)",
  )
  parser.add_argument(
    "--social-validate-llm",
    action="store_true",
    help="With --social-validate: use multi-AI brain panel (requires API keys)",
  )
  parser.add_argument(
    "--tv-oss",
    action="store_true",
    help="Run TV OSS complementary stack executive consensus",
  )
  parser.add_argument(
    "--tv-oss-llm",
    action="store_true",
    help="With --tv-oss: use multi-AI brain panel",
  )
  parser.add_argument(
    "--tv-oss-explore",
    action="store_true",
    help="Explore new dynamic-value TV OSS indicators + fine-tune",
  )
  parser.add_argument(
    "--emergency-flatten",
    action="store_true",
    help="Cancel all orders and halt (dry-run unless --execute-live)",
  )
  parser.add_argument(
    "--e2e-cycle",
    action="store_true",
    help="Full E2E: learn → analyze → export → improve",
  )
  parser.add_argument("--e2e-batch", type=int, default=50, metavar="N", help="With --e2e-cycle / --goal-mode: top N pairs")
  parser.add_argument("--e2e-status", action="store_true", help="E2E pipeline status")
  parser.add_argument(
    "--goal-mode",
    action="store_true",
    help="Autonomous swarm loop: research → fitness → validate → paper deploy (live gated)",
  )
  parser.add_argument(
    "--goal-mode-agents",
    action="store_true",
    help="Print EW multi-agent role map (Swarm Trader / goal-mode analogy)",
  )
  parser.add_argument(
    "--autoresearch",
    action="store_true",
    help="Log baseline fitness + proposed env experiments (human promote only)",
  )
  parser.add_argument(
    "--autoresearch-eval",
    action="store_true",
    help="Evaluate env proposals on newest cached analysis JSON (overnight-style)",
  )
  parser.add_argument(
    "--autoresearch-analysis",
    default=None,
    metavar="PATH",
    help="Analysis JSON for --autoresearch-eval",
  )
  parser.add_argument(
    "--effectiveness-audit",
    action="store_true",
    help="GOAT validation: walk-forward OOS, PSR gates, regime analysis, deployment verdict",
  )
  parser.add_argument(
    "--effectiveness-paper",
    action="store_true",
    help="Include OHLC paper simulation in --effectiveness-audit (network)",
  )
  parser.add_argument(
    "--paper-forward",
    action="store_true",
    help="LLM-free paper proof tick: OHLC sim + 30-day forward ledger (no AI models)",
  )
  parser.add_argument(
    "--paper-forward-no-fetch",
    action="store_true",
    help="With --paper-forward: skip OHLC network fetch (structural test only)",
  )
  parser.add_argument(
    "--paper-forward-backfill",
    action="store_true",
    help="Backfill missing days in the 30-day paper-forward proof window (point-in-time OHLC)",
  )
  parser.add_argument(
    "--paper-forward-backfill-force",
    action="store_true",
    help="With --paper-forward-backfill: rerun all window days (replaces existing snapshots)",
  )
  parser.add_argument(
    "--paper-forward-days",
    type=int,
    default=0,
    help="Proof window length in days (default EW_PAPER_PROOF_DAYS or 30)",
  )
  parser.add_argument(
    "--continuous-proof",
    action="store_true",
    help="LLM-free learn→policy→paper-forward cycle (continuous improvement)",
  )
  parser.add_argument(
    "--daily-trading-tick",
    action="store_true",
    help="LLM-free composite tick: proof + GOAT audit + tactical posture + health readiness",
  )
  parser.add_argument(
    "--daily-trading-tick-fetch",
    action="store_true",
    help="With --daily-trading-tick: include OHLC network fetch for paper sim",
  )
  parser.add_argument(
    "--daily-trading-tick-resolve",
    choices=("skip", "incremental", "full"),
    default=None,
    help="Outcome resolve mode for --daily-trading-tick (default: skip via cron script, incremental otherwise)",
  )
  parser.add_argument(
    "--goal-mode-quick",
    action="store_true",
    help="Goal mode without batch/monitor fetch; optional --execute for paper",
  )
  parser.add_argument(
    "--autonomous-daily",
    action="store_true",
    help="Run full daily autonomous loop (test → learn → research → PR merge)",
  )
  parser.add_argument(
    "--v6-scan",
    action="store_true",
    help="V6 chunk scan: up to 1000 pairs × 6 TFs (15m,1h,4h,12h,1d,1w), rank best trades",
  )
  parser.add_argument(
    "--v6-scan-full",
    action="store_true",
    help="V6 full universe scan (slow — all pairs in one run)",
  )
  parser.add_argument("--goal-text", default=None, help="Custom goal string for --goal-mode")
  parser.add_argument("--health", action="store_true", help="System health checks")
  parser.add_argument(
    "--gap-audit",
    action="store_true",
    help="Audit missing free data, TV OSS, GitHub tools, Python libs — challenge gaps",
  )
  parser.add_argument(
    "--profit-lab",
    action="store_true",
    help="Run profit laboratory: fee expectancy, CPCV, quantstats, vectorbt sweep",
  )
  parser.add_argument(
    "--profit-lab-sweep",
    action="store_true",
    help="With --profit-lab: run vectorbt parameter sweep (slower)",
  )
  parser.add_argument(
    "--freqtrade-export",
    action="store_true",
    help="Export gated executable rows to Freqtrade signal JSON",
  )
  parser.add_argument(
    "--freqtrade-export-max",
    type=int,
    default=0,
    help="Max rows for --freqtrade-export (0 = all)",
  )
  parser.add_argument("--repomix", action="store_true", help="Export RepoMix-style code pack and exit")
  parser.add_argument("--repomix-out", default="output/repomix_pack.xml", help="RepoMix output path")
  parser.add_argument(
    "--monitor",
    action="store_true",
    help="Serve browser monitor dashboard (http://127.0.0.1:8765)",
  )
  parser.add_argument("--monitor-port", type=int, default=8765, help="Port for --monitor")
  args = parser.parse_args()

  if args.monitor:
    from scripts.serve_monitor import run as run_monitor

    run(host="127.0.0.1", port=args.monitor_port, output_dir=args.output_dir)
    return

  if args.llm_cost:
    from engine.llm_cost import advisory_scenario_comparison

    comp = advisory_scenario_comparison()
    print(json.dumps(comp, indent=2))
    return

  if args.llm_tasks:
    from engine.llm_task_router import routing_matrix

    print(json.dumps(routing_matrix(), indent=2))
    return

  if args.llm_savers:
    from engine.llm_task_router import routing_matrix
    from engine.llm_token_saver import token_saver_summary

    print(json.dumps({"savers": token_saver_summary(), "routing": routing_matrix()}, indent=2))
    return

  if args.install_token_savers:
    from engine.token_saver_registry import install_missing_libraries, registry_summary

    result = install_missing_libraries()
    print(json.dumps({"install": result, "registry": registry_summary()}, indent=2))
    return

  if args.setup:
    from engine.setup_environment import setup_environment

    result = setup_environment()
    print(json.dumps(result, indent=2))
    if not result.get("ok"):
      sys.exit(1)
    return

  if args.pr_resolve_conflicts is not None:
    from engine.pr_merge_conflict import resolve_open_pr_conflicts, resolve_pr_conflicts

    if args.pr_resolve_conflicts == 0:
      result = resolve_open_pr_conflicts(dry_run=args.pr_dry_run)
    else:
      result = resolve_pr_conflicts(args.pr_resolve_conflicts, dry_run=args.pr_dry_run)
    print(json.dumps(result, indent=2, default=str))
    return

  if args.pr_approve is not None or args.pr_approve_all:
    from engine.pr_agent import run_pr_agent

    result = run_pr_agent(
      pr_number=args.pr_approve,
      dry_run=args.pr_dry_run,
      approve_all=args.pr_approve_all,
    )
    print(json.dumps(result, indent=2, default=str))
    return

  if args.resolve_conflicts is not None or args.resolve_conflicts_all:
    from engine.pr_merge_conflict import resolve_open_pr_conflicts, resolve_pr_conflicts

    if args.resolve_conflicts_all:
      result = resolve_open_pr_conflicts(dry_run=args.pr_dry_run)
    else:
      result = resolve_pr_conflicts(args.resolve_conflicts, dry_run=args.pr_dry_run)
    print(json.dumps(result, indent=2, default=str))
    return

  if args.brain_ask:
    from engine.brain_consensus import ask_brain

    result = ask_brain(args.brain_ask, use_llm=False)
    print(json.dumps(result, indent=2, default=str))
    return

  if args.brain_search:
    from engine.okf_brain import search_concepts

    hits = search_concepts(args.brain_search, limit=20)
    print(json.dumps(hits, indent=2, default=str))
    return

  if args.brain_status:
    from engine.brain_consensus import brain_status
    from engine.brain_self_improve import improvement_summary

    print(json.dumps({
      "brain": brain_status(),
      "self_improve": improvement_summary(),
    }, indent=2, default=str))
    return

  if args.execution_status:
    from engine.execution_agent import execution_status
    print(json.dumps(execution_status(), indent=2, default=str))
    return

  if args.portfolio_risk:
    from engine.portfolio_risk import portfolio_risk_status
    print(json.dumps(portfolio_risk_status(), indent=2, default=str))
    return

  if args.effectiveness:
    from engine.effectiveness_validation import run_effectiveness_validation
    report = run_effectiveness_validation()
    print(json.dumps(report.to_dict(), indent=2, default=str))
    sys.exit(0 if report.ok else 1)

  if args.data_intel:
    from gateway.data_hub import live_market_state
    print(json.dumps(live_market_state(args.data_intel), indent=2, default=str))
    return

  if args.social_validate is not None:
    from engine.social_strategy_validation import run_social_strategy_validation

    result = run_social_strategy_validation(
      symbol=args.social_validate or "",
      use_llm=args.social_validate_llm,
    )
    print(json.dumps(result, indent=2, default=str))
    return

  if args.tv_oss:
    from engine.tv_oss_consensus import run_tv_oss_consensus

    result = run_tv_oss_consensus(use_llm=args.tv_oss_llm)
    print(json.dumps(result, indent=2, default=str))
    return

  if args.tv_oss_explore:
    from engine.tv_oss_discovery import run_tv_oss_discovery

    result = run_tv_oss_discovery(use_llm=args.tv_oss_llm)
    print(json.dumps(result, indent=2, default=str))
    return

  if args.emergency_flatten:
    from engine.risk_ops import emergency_flatten
    dry = not args.execute_live
    print(json.dumps(emergency_flatten(dry_run=dry), indent=2, default=str))
    return

  if args.execute or args.execute_live:
    from engine.execution_agent import execute_from_csv
    if args.execute_live:
      os.environ["EW_EXECUTION_MODE"] = "live"
    result = execute_from_csv(dry_run=not args.execute_live)
    print(json.dumps(result, indent=2, default=str))
    return

  if args.gap_audit:
    from engine.resource_gap_audit import run_resource_gap_audit, save_gap_audit

    result = run_resource_gap_audit(persist=True, persist_okf=False)
    path = save_gap_audit(result)
    print(json.dumps(result, indent=2, default=str))
    print(f"[gap-audit] saved {path}", file=sys.stderr)
    return

  if args.profit_lab:
    from engine.profit_lab.runner import run_profit_lab

    if args.profit_lab_sweep:
      os.environ["EW_PROFIT_LAB_SWEEP"] = "1"
    print(json.dumps(run_profit_lab(run_sweep=args.profit_lab_sweep), indent=2, default=str))
    return

  if args.freqtrade_export:
    from engine.freqtrade_export import export_freqtrade_signals

    print(json.dumps(
      export_freqtrade_signals(max_rows=args.freqtrade_export_max or 0),
      indent=2,
      default=str,
    ))
    return

  if args.health:
    from engine.system_health import run_health_checks, save_health
    h = run_health_checks()
    print(json.dumps(h, indent=2, default=str))
    print(f"[health] saved {save_health(h)}", file=sys.stderr)
    return

  if args.e2e_status:
    from engine.e2e_pipeline import e2e_status
    print(json.dumps(e2e_status(), indent=2, default=str))
    return

  if args.autonomous_daily:
    import subprocess

    env = os.environ.copy()
    if args.pr_dry_run:
      env["EW_PR_AUTO_MERGE"] = "0"
      env["EW_PR_AUTO_APPROVE"] = "0"
    proc = subprocess.run(["bash", "scripts/run_autonomous_daily.sh"], env=env)
    sys.exit(proc.returncode)

  if args.v6_scan or args.v6_scan_full:
    from engine.v6_scanner import run_v6_chunk_scan, run_v6_full_batch

    os.environ.setdefault("EW_V6_SETUP", "1")
    if args.v6_scan_full:
      result = run_v6_full_batch()
    else:
      result = run_v6_chunk_scan()
    print(json.dumps(result, indent=2, default=str))
    return

  if args.goal_mode_agents:
    from engine.goal_mode import swarm_agent_map

    print(json.dumps(swarm_agent_map(), indent=2))
    return

  if args.autoresearch:
    from engine.autoresearch import run_autoresearch_batch

    print(json.dumps(run_autoresearch_batch(), indent=2, default=str))
    return

  if args.autoresearch_eval:
    from engine.autoresearch import run_autoresearch_eval_loop

    print(json.dumps(
      run_autoresearch_eval_loop(analysis_path=args.autoresearch_analysis),
      indent=2,
      default=str,
    ))
    return

  if args.effectiveness_audit:
    from engine.effectiveness_audit import run_full_effectiveness_audit

    print(json.dumps(
      run_full_effectiveness_audit(
        fetch_ohlc=args.effectiveness_paper,
        include_walk_forward=True,
      ),
      indent=2,
      default=str,
    ))
    return

  if args.paper_forward:
    from engine.autonomous_ops import run_paper_proof_tick

    print(json.dumps(
      run_paper_proof_tick(fetch_ohlc=not args.paper_forward_no_fetch),
      indent=2,
      default=str,
    ))
    return

  if args.paper_forward_backfill:
    from engine.autonomous_ops import run_paper_backfill_tick

    print(json.dumps(
      run_paper_backfill_tick(
        fetch_ohlc=not args.paper_forward_no_fetch,
        force=args.paper_forward_backfill_force,
        days=args.paper_forward_days or None,
      ),
      indent=2,
      default=str,
    ))
    return

  if getattr(args, "continuous_proof", False):
    from engine.autonomous_ops import run_continuous_proof_tick

    print(json.dumps(
      run_continuous_proof_tick(fetch_ohlc=not args.paper_forward_no_fetch),
      indent=2,
      default=str,
    ))
    return

  if args.daily_trading_tick:
    from engine.daily_trading_ops import run_daily_trading_tick

    resolve_mode = args.daily_trading_tick_resolve
    if resolve_mode == "skip":
      os.environ["EW_PAPER_FORWARD_SKIP_RESOLVE"] = "1"
    elif resolve_mode:
      os.environ["EW_PAPER_FORWARD_SKIP_RESOLVE"] = "0"
      os.environ["EW_RESOLVE_MODE"] = resolve_mode

    print(json.dumps(
      run_daily_trading_tick(
        fetch_ohlc=args.daily_trading_tick_fetch,
        resolve_mode=resolve_mode,
      ),
      indent=2,
      default=str,
    ))
    return

  if args.goal_mode or args.goal_mode_quick:
    from engine.goal_mode import run_goal_mode_cycle

    os.environ.setdefault("EW_GOAL_MODE", "1")
    paper = True
    if args.execute:
      paper = True
    elif args.execute_live:
      paper = False
    quick = args.goal_mode_quick
    result = run_goal_mode_cycle(
      goal=args.goal_text,
      batch_n=0 if quick else args.e2e_batch,
      llm_advisory=args.llm_advisory,
      execute_paper=paper if (args.execute or args.execute_live) else (False if quick else None),
      execute=args.execute,
      execute_live=args.execute_live,
      skip_batch=quick,
      skip_monitor=quick,
    )
    print(json.dumps(result, indent=2, default=str))
    return

  if args.e2e_cycle:
    from engine.e2e_pipeline import run_e2e_cycle
    result = run_e2e_cycle(
      batch_n=args.e2e_batch,
      execute=args.execute,
      execute_live=args.execute_live,
      llm_advisory=args.llm_advisory,
    )
    print(json.dumps(result, indent=2, default=str))
    return

  if args.repomix:
    from gateway.repomix_export import pack_repository

    packed = pack_repository(".")
    os.makedirs(os.path.dirname(args.repomix_out) or ".", exist_ok=True)
    with open(args.repomix_out, "w") as f:
      f.write(packed)
    print(f"[repomix] wrote {args.repomix_out} ({len(packed):,} chars)")
    return

  if args.clear_cache:
    from cache.disk_cache import get_cache

    import shutil

    cache_dir = get_cache().cache_dir
    if cache_dir.exists():
      shutil.rmtree(cache_dir)
      print(f"[cache] cleared {cache_dir}")

  tfs = [t.strip() for t in args.tfs.split(",")]
  t0 = time.time()

  if args.batch or args.top:
    if args.top:
      from engine.top50_batch import run_top_crypto_batch

      meta = run_top_crypto_batch(
        n=args.top,
        tfs=tfs,
        output_dir=args.output_dir,
        quote=args.quote,
        llm_advisory=args.llm_advisory,
      )
      if args.save:
        import shutil
        shutil.copy(meta["json"], args.save)
      elapsed = time.time() - t0
      print(f"\n[done] top {args.top} batch in {elapsed:.0f}s", file=sys.stderr)
      if args.cache_stats:
        from cache.disk_cache import get_cache
        print(f"[cache] {get_cache().stats()}", file=sys.stderr)
    else:
      from engine.batch import run_batch, save_batch_json

      results = run_batch(args.batch, tfs, args.crypto, llm_advisory=args.llm_advisory)
      if args.save:
        save_batch_json(results, args.save)
      else:
        print(json.dumps(results, indent=2, default=str))
  else:
    if not args.symbol:
      parser.error("--symbol is required unless --batch is used")
    from engine.adaptive import adaptive_pipeline

    result = adaptive_pipeline(args.symbol, tfs, args.crypto, llm_advisory=args.llm_advisory)
    validated = ElliottWaveOutput(**result)
    payload = validated.model_dump()
    elapsed = time.time() - t0
    print(f"\n[done] {args.symbol} status={validated.status} elapsed={elapsed:.1f}s", file=sys.stderr)
    if args.cache_stats and validated.cache_stats:
      print(f"[cache] {validated.cache_stats}", file=sys.stderr)
    if args.gateway_stats and args.crypto:
      from gateway.market_gateway import get_gateway
      print(f"[gateway] {get_gateway().stats()}", file=sys.stderr)
    if args.save:
      with open(args.save, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    elif args.outcomes_only:
      print(json.dumps(payload.get("step8_outcomes", {}), indent=2, default=str))
    else:
      print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
  main()
