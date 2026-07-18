#!/usr/bin/env python3
"""Elliott Wave + Harmonic confluence trading analysis CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

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
    help="Consult Claude + GPT on critical decisions (GO/CONDITIONAL_GO/executable); needs API keys",
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
  parser.add_argument("--e2e-batch", type=int, default=50, metavar="N", help="With --e2e-cycle: top N pairs")
  parser.add_argument("--e2e-status", action="store_true", help="E2E pipeline status")
  parser.add_argument("--health", action="store_true", help="System health checks")
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

  if args.pr_approve is not None or args.pr_approve_all:
    from engine.pr_agent import run_pr_agent

    result = run_pr_agent(
      pr_number=args.pr_approve,
      dry_run=args.pr_dry_run,
      approve_all=args.pr_approve_all,
    )
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
    import os
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
