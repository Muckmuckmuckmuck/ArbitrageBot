"""Assemble the full system once, so every script evaluates the exact same book.

Configured for the return objective (aggressive) with downturn protection coming
from multi-asset trend rotation rather than shorting:
  high  aggressive equity momentum (beat SPY)      -> loose 24% vol target
  mid   broad global trend rotation (~SPY, earns in downturns) -> 16% target
  safe  conservative rotation (> HYSA, earns in downturns)     -> 12% target
"""
from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from quantbot import universe
from quantbot.allocator import Allocator, Sleeve
from quantbot.backtest.engine import BacktestResult, buy_and_hold, run_backtest
from quantbot.risk.engine import drawdown_kill_switch, enforce_caps
from quantbot.strategies import common
from quantbot.strategies.global_rotation import GlobalRotation
from quantbot.strategies.trend_momentum import TrendMomentum

HIGH = universe.SLEEVES["high_growth"]
MID = universe.SLEEVES["mid_growth"]
SAFE = universe.SLEEVES["safe_growth"]
CASH = universe.CASH_PROXY
VOL_TARGET = {"high_growth": 0.24, "mid_growth": 0.16, "safe_growth": 0.12}
PORTFOLIO_VOL_TARGET = 0.16


# Ablation-validated signal: blended 3/6/12-month momentum, monthly cadence.
# (Multi-horizon robustly lifted Sharpe on every sleeve; vol-normalization was a wash
#  and biweekly cadence hurt — so neither is used.)
SIGNAL = dict(lookbacks=(63, 126, 252), vol_normalize=False, rebalance="M")


def build_sleeves():
    high = TrendMomentum(top_n=2, weighting="momentum", **SIGNAL)             # concentrate in leaders
    mid = GlobalRotation(MID, CASH, top_n=3, weighting="momentum", **SIGNAL)  # go-anywhere trend
    safe = GlobalRotation(SAFE, CASH, top_n=3, weighting="equal", **SIGNAL)   # conservative rotation
    return high, mid, safe


def build_results(px: pd.DataFrame, regime: pd.DataFrame, settings, base_weights=None) -> Tuple[Dict[str, BacktestResult], pd.DataFrame]:
    cols = px.columns
    base_weights = base_weights or universe.SLEEVE_TARGET_WEIGHTS
    cost, cash = settings.backtest.cost_bps, settings.backtest.cash_annual_rate
    high, mid, safe = build_sleeves()

    def vt(w: pd.DataFrame, target: float) -> pd.DataFrame:
        return common.apply_vol_target(w.reindex(columns=cols).fillna(0.0), px, target)

    r_high = run_backtest(px, vt(high.target_weights(px[HIGH], regime), VOL_TARGET["high_growth"]), cost, cash)
    r_mid = run_backtest(px, vt(mid.target_weights(px[MID + [CASH]], regime), VOL_TARGET["mid_growth"]), cost, cash)
    r_safe = run_backtest(px, vt(safe.target_weights(px[SAFE + [CASH]], regime), VOL_TARGET["safe_growth"]), cost, cash)

    alloc = Allocator(
        sleeves=[
            Sleeve("high_growth", high, HIGH),
            Sleeve("mid_growth", mid, MID + [CASH]),
            Sleeve("safe_growth", safe, SAFE + [CASH]),
        ],
        base_weights=base_weights,
        portfolio_vol_target=PORTFOLIO_VOL_TARGET,
        regime_tilt=True,
    )
    book, _ = alloc.combined_weights(px, regime)
    book = enforce_caps(book, settings.risk)
    book = drawdown_kill_switch(book, px, settings.risk.max_drawdown_pct)
    r_comb = run_backtest(px, book, cost, cash)
    r_spy = buy_and_hold(px, universe.BENCHMARK)

    return {
        "high_growth": r_high,
        "mid_growth": r_mid,
        "safe_growth": r_safe,
        "combined": r_comb,
        "spy": r_spy,
    }, book
