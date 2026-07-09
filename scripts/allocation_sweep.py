#!/usr/bin/env python3
"""The return-vs-protection dial: what does the combined book do at different sleeve
mixes? Higher high-growth weight -> more return, less downturn protection. No leverage.

    python scripts/allocation_sweep.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from quantbot import system, universe  # noqa: E402
from quantbot.config import settings  # noqa: E402
from quantbot.data.history import get_prices  # noqa: E402
from quantbot.regime.classifier import classify  # noqa: E402

MIXES = {
    "balanced   50/30/20": {"high_growth": 0.50, "mid_growth": 0.30, "safe_growth": 0.20},
    "growth     65/20/15": {"high_growth": 0.65, "mid_growth": 0.20, "safe_growth": 0.15},
    "aggressive 80/12/8":  {"high_growth": 0.80, "mid_growth": 0.12, "safe_growth": 0.08},
    "max-growth 90/6/4":   {"high_growth": 0.90, "mid_growth": 0.06, "safe_growth": 0.04},
}


def yr_return(returns: pd.Series, year: int) -> float:
    s = returns[returns.index.year == year]
    return float((1.0 + s).prod() - 1.0) if len(s) else float("nan")


def main() -> int:
    px = get_prices(universe.all_symbols(), start=settings.data.start)
    regime = classify(px[universe.BENCHMARK])

    hdr = f"{'mix (high/mid/safe)':<22}{'CAGR':>8}{'Vol':>8}{'Sharpe':>8}{'MaxDD':>9}{'2020':>8}{'2022':>8}{'worstYr':>9}"
    print(hdr + "\n" + "-" * len(hdr))
    for name, bw in MIXES.items():
        results, _ = system.build_results(px, regime, settings, base_weights=bw)
        r = results["combined"]
        yr = (1.0 + r.returns).groupby(r.returns.index.year).prod() - 1.0
        s = r.stats
        print(f"{name:<22}{s['CAGR']:>7.2%}{s['AnnVol']:>8.2%}{s['Sharpe']:>8.2f}{s['MaxDD']:>9.2%}"
              f"{yr_return(r.returns, 2020):>8.1%}{yr_return(r.returns, 2022):>8.1%}{yr.min():>9.1%}")

    spy = system.build_results(px, regime, settings)[0]["spy"]
    s = spy.stats
    print(f"{'Buy & Hold SPY':<22}{s['CAGR']:>7.2%}{s['AnnVol']:>8.2%}{s['Sharpe']:>8.2f}{s['MaxDD']:>9.2%}"
          f"{yr_return(spy.returns, 2020):>8.1%}{yr_return(spy.returns, 2022):>8.1%}"
          f"{((1.0 + spy.returns).groupby(spy.returns.index.year).prod() - 1.0).min():>9.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
