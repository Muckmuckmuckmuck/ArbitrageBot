#!/usr/bin/env python3
"""Ablation: does volume confirmation (the transferable idea from Kronos/OHLCV models)
beat plain momentum — out-of-sample, not just full-sample?

Tests on the high-growth universe: plain multi-horizon momentum vs. the same signal
tilted/gated by volume trend. Reports CAGR / Sharpe / MaxDD / monthly win-rate for the
full sample AND the 2020+ out-of-sample block. We keep volume only if it helps OOS.

    python scripts/kronos_volume_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from quantbot import universe  # noqa: E402
from quantbot.config import settings  # noqa: E402
from quantbot.data.history import get_prices, get_volume  # noqa: E402
from quantbot.strategies import common  # noqa: E402
from quantbot.backtest.engine import run_backtest  # noqa: E402

OOS = "2020-01-01"


def win_rate(returns: pd.Series) -> float:
    monthly = (1 + returns).groupby([returns.index.year, returns.index.month]).prod() - 1
    return float((monthly > 0).mean())


def sub(res_returns: pd.Series, lo=None, hi=None):
    r = res_returns
    if lo:
        r = r[r.index >= lo]
    if hi:
        r = r[r.index < hi]
    eq = (1 + r).cumprod()
    from quantbot.backtest import metrics
    return metrics.cagr(eq), metrics.sharpe(r, settings.backtest.cash_annual_rate), metrics.max_drawdown(eq), win_rate(r)


def backtest_signal(signal: pd.DataFrame, px: pd.DataFrame, top_n=2, vt=0.24):
    def decide(dt):
        m = signal.loc[dt].dropna()
        winners = m[m > 0].sort_values(ascending=False).head(top_n)
        w = pd.Series(0.0, index=px.columns)
        for s in winners.index:
            w[s] = 1.0 / top_n
        return w
    W = common.periodic_rebalance(px, decide, "M")
    W = common.apply_vol_target(W, px, vt)
    return run_backtest(px, W, settings.backtest.cost_bps, settings.backtest.cash_annual_rate)


def main() -> int:
    syms = universe.SLEEVES["high_growth"]
    px = get_prices(syms, start=settings.data.start)[syms]
    vol = get_volume(syms, start=settings.data.start).reindex(px.index).reindex(columns=px.columns)

    mom = common.signal_momentum(px, (63, 126, 252), vol_normalize=False)
    vt_ratio = common.volume_trend(vol).reindex_like(mom)

    variants = {
        "plain momentum":            mom,
        "x volume_trend":            mom * vt_ratio,
        "x sqrt(volume_trend)":      mom * np.sqrt(vt_ratio.clip(lower=0)),
        "gated (vol_trend>1)":       mom.where(vt_ratio > 1.0, other=-1.0),  # demote falling-volume names
    }

    print(f"High-growth universe {syms}\n")
    hdr = f"{'variant':<22}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>9}{'Win%':>7}   |  OOS(2020+): {'CAGR':>7}{'Sharpe':>8}{'Win%':>7}"
    print(hdr + "\n" + "-" * len(hdr))
    for name, sig in variants.items():
        res = backtest_signal(sig, px)
        fc, fs, fdd, fw = sub(res.returns)
        oc, os_, ow = sub(res.returns, lo=OOS)[0], sub(res.returns, lo=OOS)[1], sub(res.returns, lo=OOS)[3]
        print(f"{name:<22}{fc:>7.1%}{fs:>8.2f}{fdd:>9.1%}{fw:>7.0%}   |          {oc:>7.1%}{os_:>8.2f}{ow:>7.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
