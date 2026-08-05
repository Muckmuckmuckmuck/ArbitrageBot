#!/usr/bin/env python3
"""Search for genuine return upgrades in the high-growth sleeve.

Two independent levers, both judged on full-sample AND out-of-sample (2020+):
  1. UNIVERSE  — is the current 6-ETF basket capping upside? Test wider high-beta
                 and leveraged-ETF baskets.
  2. SIGNAL    — does a fast breakout/acceleration sleeve (weekly) add anything on
                 top of the slow monthly momentum core, and does blending help?

Also reports annualized turnover, since "trade more often" is an explicit goal —
but frequency is only worth having if risk-adjusted return survives it.

    python scripts/substrategy_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from quantbot import universe  # noqa: E402
from quantbot.backtest import metrics  # noqa: E402
from quantbot.backtest.engine import run_backtest  # noqa: E402
from quantbot.config import settings  # noqa: E402
from quantbot.data.history import get_prices, get_volume  # noqa: E402
from quantbot.regime.classifier import classify  # noqa: E402
from quantbot.strategies import common  # noqa: E402
from quantbot.strategies.breakout import BreakoutMomentum  # noqa: E402
from quantbot.strategies.trend_momentum import TrendMomentum  # noqa: E402

OOS = "2020-01-01"
SIGNAL = dict(lookbacks=(63, 126, 252), vol_normalize=False, rebalance="M")

UNIVERSES = {
    "current  (6 ETF)": ["QQQ", "XLK", "SMH", "XLY", "XLC", "MTUM"],
    "wide hi-beta":     ["QQQ", "XLK", "SMH", "XLY", "MTUM", "SOXX", "IGV", "FDN", "VGT", "XBI"],
    "levered 2x/3x":    ["QQQ", "XLK", "SMH", "MTUM", "QLD", "SSO", "TQQQ", "SOXL", "TECL"],
}
VOL_TARGET = 0.32   # aggressive-profile sleeve target
MAX_LEV = 1.8


def evaluate(w: pd.DataFrame, px: pd.DataFrame, label: str):
    w = common.apply_vol_target(w.reindex(columns=px.columns).fillna(0.0), px, VOL_TARGET, max_leverage=MAX_LEV)
    res = run_backtest(px, w, settings.backtest.cost_bps, settings.backtest.cash_annual_rate)
    s = res.stats
    r_oos = res.returns[res.returns.index >= OOS]
    eq_oos = (1 + r_oos).cumprod()
    turnover = res.turnover.sum() / ((px.index[-1] - px.index[0]).days / 365.25)
    print(f"  {label:<26}{s['CAGR']:>7.1%}{s['Sharpe']:>8.2f}{s['MaxDD']:>9.1%}"
          f"{metrics.cagr(eq_oos):>11.1%}{metrics.sharpe(r_oos, settings.backtest.cash_annual_rate):>9.2f}"
          f"{metrics.max_drawdown(eq_oos):>9.1%}{turnover:>10.1f}x")
    return res


def main() -> int:
    hdr = f"  {'variant':<26}{'CAGR':>7}{'Sharpe':>8}{'MaxDD':>9}{'OOS CAGR':>11}{'OOS Shrp':>9}{'OOS DD':>9}{'turnover':>11}"

    print("=" * 96)
    print("1) UNIVERSE — core monthly momentum, top_n=3")
    print("=" * 96)
    print(hdr)
    for name, syms in UNIVERSES.items():
        px = get_prices(sorted(set(syms + [universe.BENCHMARK])), start=settings.data.start)
        vol = get_volume(sorted(set(syms)), start=settings.data.start).reindex(px.index)
        syms_ok = [s for s in syms if s in px.columns]
        sub = px[syms_ok]
        strat = TrendMomentum(top_n=3, weighting="momentum", **SIGNAL)
        evaluate(strat.target_weights(sub, None, vol[syms_ok]), sub, name)

    print("\n" + "=" * 96)
    print("2) SIGNAL — fast breakout sleeve vs slow core, on the best universe")
    print("=" * 96)
    print(hdr)
    for name, syms in UNIVERSES.items():
        px = get_prices(sorted(set(syms + [universe.BENCHMARK])), start=settings.data.start)
        vol = get_volume(sorted(set(syms)), start=settings.data.start).reindex(px.index)
        syms_ok = [s for s in syms if s in px.columns]
        sub = px[syms_ok]
        v = vol[syms_ok]
        core = TrendMomentum(top_n=3, weighting="momentum", **SIGNAL).target_weights(sub, None, v)
        brk = BreakoutMomentum(top_n=3, rebalance="W").target_weights(sub, None, v)
        print(f"  -- {name} --")
        evaluate(brk, sub, "breakout only (weekly)")
        evaluate(0.5 * core + 0.5 * brk, sub, "50/50 core+breakout")
        evaluate(0.7 * core + 0.3 * brk, sub, "70/30 core+breakout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
