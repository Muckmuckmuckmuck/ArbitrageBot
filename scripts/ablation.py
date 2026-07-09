#!/usr/bin/env python3
"""Ablation study: which signal changes actually raise risk-adjusted return?

Tests each change on the high-growth (TrendMomentum) and mid (GlobalRotation) sleeves,
reporting Sharpe/CAGR/MaxDD AND per-year robustness (positive years, worst year) so we
keep only improvements that hold up across periods — not full-sample curve fits.

    python scripts/ablation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from quantbot import universe  # noqa: E402
from quantbot.config import settings  # noqa: E402
from quantbot.data.history import get_prices  # noqa: E402
from quantbot.regime.classifier import classify  # noqa: E402
from quantbot.strategies import common  # noqa: E402
from quantbot.strategies.trend_momentum import TrendMomentum  # noqa: E402
from quantbot.strategies.global_rotation import GlobalRotation  # noqa: E402
from quantbot.backtest.engine import run_backtest, buy_and_hold  # noqa: E402

VARIANTS = {
    "baseline 12-1 monthly": dict(lookbacks=(252,), vol_normalize=False, rebalance="M"),
    "+multi-horizon":        dict(lookbacks=(63, 126, 252), vol_normalize=False, rebalance="M"),
    "+vol-normalized":       dict(lookbacks=(63, 126, 252), vol_normalize=True, rebalance="M"),
    "+biweekly cadence":     dict(lookbacks=(63, 126, 252), vol_normalize=True, rebalance="2W"),
}


def robustness(returns: pd.Series):
    yr = (1.0 + returns).groupby(returns.index.year).prod() - 1.0
    return int((yr > 0).sum()), len(yr), float(yr.min())


def evaluate(title, make_strat, sub_cols, px, regime, vt_target, cost, cash):
    print(f"\n{title}   (vol target {vt_target:.0%})")
    print(f"  {'variant':<24}{'CAGR':>8}{'Vol':>8}{'Sharpe':>8}{'MaxDD':>9}{'posYrs':>8}{'worstYr':>9}")
    for name, cfg in VARIANTS.items():
        strat = make_strat(cfg)
        w = strat.target_weights(px[sub_cols], regime).reindex(columns=px.columns).fillna(0.0)
        w = common.apply_vol_target(w, px, vt_target)
        res = run_backtest(px, w, cost, cash)
        pos, tot, worst = robustness(res.returns)
        s = res.stats
        print(f"  {name:<24}{s['CAGR']:>7.2%}{s['AnnVol']:>8.2%}{s['Sharpe']:>8.2f}"
              f"{s['MaxDD']:>9.2%}{pos:>5}/{tot:<2}{worst:>9.1%}")


def main() -> int:
    px = get_prices(universe.all_symbols(), start=settings.data.start)
    regime = classify(px[universe.BENCHMARK])
    cost, cash = settings.backtest.cost_bps, settings.backtest.cash_annual_rate

    HIGH = universe.SLEEVES["high_growth"]
    MID = universe.SLEEVES["mid_growth"]
    CASH = universe.CASH_PROXY

    evaluate(
        "HIGH-GROWTH  (TrendMomentum)",
        lambda cfg: TrendMomentum(top_n=2, weighting="momentum", **cfg),
        HIGH, px, regime, 0.24, cost, cash,
    )
    evaluate(
        "MID  (GlobalRotation)",
        lambda cfg: GlobalRotation(MID, CASH, top_n=3, weighting="momentum", **cfg),
        MID + [CASH], px, regime, 0.16, cost, cash,
    )

    spy = buy_and_hold(px, universe.BENCHMARK)
    pos, tot, worst = robustness(spy.returns)
    print(f"\n  reference: Buy&Hold SPY  CAGR {spy.stats['CAGR']:.2%}  Sharpe {spy.stats['Sharpe']:.2f}  "
          f"MaxDD {spy.stats['MaxDD']:.2%}  posYrs {pos}/{tot}  worstYr {worst:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
