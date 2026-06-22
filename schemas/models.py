"""Pydantic v2 schemas for Elliott Wave + Harmonic output."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HarmonicPattern(BaseModel):
  tf: str
  pattern: str
  prz_low: float
  prz_high: float
  ratios: Dict[str, float]
  bullish: bool


class WaveDetail(BaseModel):
  type: str
  magnitude: float
  start: float
  end: float


class HTFBias(BaseModel):
  tf: str
  state: str
  wave_A: WaveDetail
  wave_B_end: float
  wave_C_current: float
  bias: str


class KillZone(BaseModel):
  price_low: float
  price_high: float
  width_pct: float
  constituent_fibs: Dict[str, float] = Field(default_factory=dict)


class ExecutionValidation(BaseModel):
  in_zone: bool
  passes: bool
  bull_impulse_count: int = 0
  bear_impulse_count: int = 0
  violations_sample: List[str] = Field(default_factory=list)


class TradeSetup(BaseModel):
  action: str
  entry_zone: Optional[List[float]] = None
  stop_loss: Optional[float] = None
  take_profit_1: Optional[float] = None
  take_profit_2: Optional[float] = None
  risk_reward: Optional[float] = None
  confidence: Optional[float] = None
  reason: Optional[str] = None
  trigger_zone: Optional[List[float]] = None
  instruction: Optional[str] = None


class ExecutiveDecision(BaseModel):
  verdict: str  # GO | CONDITIONAL_GO | STANDBY_ORDERS | STAGED_GO
  conviction: str
  direction: str
  position_size_pct: int = 100
  playbook: str
  structural_gaps: List[str] = Field(default_factory=list)
  contingencies: List[Dict[str, str]] = Field(default_factory=list)
  position_model: Optional[str] = None
  scale_legs: Optional[List[Dict[str, Any]]] = None
  alternative_path: Optional[Dict[str, Any]] = None
  consensus_summary: Optional[Dict[str, Any]] = None


class EngineVote(BaseModel):
  engine: str
  source: str
  direction: str
  valid: bool
  confidence: float
  detail: str


class WaveConsensus(BaseModel):
  consensus_direction: str
  consensus_score: float
  agreement_pct: float
  conviction: str
  confidence_boost: float
  engines_run: int
  engines_valid: int
  votes: List[EngineVote]
  divergences: List[str] = Field(default_factory=list)
  github_tools_used: List[str] = Field(default_factory=list)


class ToolCall(BaseModel):
  tool: str
  args: str
  result_hash: str


class ElliottWaveOutput(BaseModel):
  symbol: str
  timestamp_utc: str
  status: str
  step1_htf_bias: HTFBias
  step2_adaptive_pivots: Dict[str, Dict[str, Any]]
  step3_kill_zone: KillZone
  step4_harmonic_overlap: List[HarmonicPattern]
  step5_execution_validation: ExecutionValidation
  step6_wave_consensus: WaveConsensus
  trade_setup: TradeSetup
  executive_decision: ExecutiveDecision
  honesty_audit: Dict[str, Any]
  tool_calls_log: List[ToolCall]
  reasoning_trace: str
  monte_carlo: Optional[Dict[str, Any]] = None
  cache_stats: Optional[Dict[str, Any]] = None
