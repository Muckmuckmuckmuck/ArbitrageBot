#!/usr/bin/env python3
"""The risk/return frontier: what does each aggression profile actually buy?

Reports full-sample AND out-of-sample (2020+) metrics for every profile, plus the
crisis windows, so the cost of chasing return is explicit rather than implied.

    python scripts/profile_sweep.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from quantbot import system, universe  # noqa: E402
from quantbot.backtest import metrics  # noqa: E402
from quantbot.config import settings  # noqa: E402
from quantbot.data.history import get_prices  # noqa: E402
from quantbot.regime.classifier import classify  # noqa: E402

OOS = "2020-01-01"
WINDOWS = {
    "COVID 2020": ("2020-02-19", "2020-03-23"),
    "2022 bear": ("2022-01-01", "2022-10-12"),
}


def block(returns: pd.Series, lo=None):
    r = returns[returns.index >= lo] if lo else returns
    eq = (1 + r).cumprod()
    return metrics.cagr(eq), metrics.sharpe(r, settings.backtest.cash_annual_rate), metrics.max_drawdown(eq)


def main() -> int:
    px = get_prices(universe.all_symbols(), start=settings.data.start)
    regime = classify(px[universe.BENCHMARK])

    hdr = (f"{'profile':<12}{'CAGR':>8}{'Vol':>7}{'Sharpe':>8}{'MaxDD':>9}{'Calmar':>8}"
           f"{'gross':>7}  |{'OOS CAGR':>10}{'OOS Shrp':>9}{'OOS DD':>8}  |{'COVID':>8}{'2022':>8}")
    print(hdr + "\n" + "-" * len(hdr))

    rows = {}
    for name in ["balanced", "growth", "aggressive", "max_growth", "momentum_max"]:
        res, book = system.build_results(px, regime, settings, profile=name)
        c = res["combined"]
        s = c.stats
        oc, osh, odd = block(c.returns, OOS)
        wins = []
        for _, (a, b) in WINDOWS.items():
            eq = c.equity.loc[a:b]
            wins.append(eq.iloc[-1] / eq.iloc[0] - 1 if len(eq) > 1 else float("nan"))
        print(f"{name:<12}{s['CAGR']:>7.1%}{s['AnnVol']:>7.1%}{s['Sharpe']:>8.2f}{s['MaxDD']:>9.1%}"
              f"{s['Calmar']:>8.2f}{book.sum(axis=1).mean():>7.0%}  |{oc:>10.1%}{osh:>9.2f}{odd:>8.1%}"
              f"  |{wins[0]:>8.1%}{wins[1]:>8.1%}")
        rows[name] = res

    spy = rows["balanced"]["spy"]
    s = spy.stats
    oc, osh, odd = block(spy.returns, OOS)
    wins = []
    for _, (a, b) in WINDOWS.items():
        eq = spy.equity.loc[a:b]
        wins.append(eq.iloc[-1] / eq.iloc[0] - 1)
    print(f"{'SPY b&h':<12}{s['CAGR']:>7.1%}{s['AnnVol']:>7.1%}{s['Sharpe']:>8.2f}{s['MaxDD']:>9.1%}"
          f"{s['Calmar']:>8.2f}{'100%':>7}  |{oc:>10.1%}{osh:>9.2f}{odd:>8.1%}  |{wins[0]:>8.1%}{wins[1]:>8.1%}")

    print("\nPer-year returns by profile:")
    yrs = {n: (1 + rows[n]["combined"].returns).groupby(rows[n]["combined"].returns.index.year).prod() - 1
           for n in rows}
    yrs["SPY"] = (1 + spy.returns).groupby(spy.returns.index.year).prod() - 1
    names = list(yrs)
    print("  year " + "".join(f"{n:>12}" for n in names))
    for y in yrs["SPY"].index:
        print(f"  {int(y)} " + "".join(f"{yrs[n].get(y, float('nan')):>11.1%} " for n in names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
