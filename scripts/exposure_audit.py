#!/usr/bin/env python3
"""Diagnose WHERE portfolio exposure is being lost.

Hypothesis: the book is structurally under-risked. Vol targeting is applied twice
(sleeve + portfolio) and each pass is capped at max_leverage=1.0, so it can only
ever CUT exposure — never add it back when realized vol sits below target. Layered
on top of regime tilt + caps + kill-switch, the result is a persistent cash drag.

Reports gross exposure and realized vol (overall and by regime) so we can see how
far under the vol budget the book actually runs.

    python scripts/exposure_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from quantbot import system, universe  # noqa: E402
from quantbot.config import settings  # noqa: E402
from quantbot.data.history import get_prices  # noqa: E402
from quantbot.regime.classifier import classify  # noqa: E402

TD = 252


def main() -> int:
    px = get_prices(universe.all_symbols(), start=settings.data.start)
    regime = classify(px[universe.BENCHMARK])
    results, book = system.build_results(px, regime, settings)

    gross = book.sum(axis=1)
    rets = results["combined"].returns
    rvol = rets.rolling(60).std() * np.sqrt(TD)
    reg = regime["regime"].reindex(book.index).ffill()

    print("=" * 74)
    print("EXPOSURE AUDIT — is the book under-risked?")
    print("=" * 74)
    print(f"Portfolio vol TARGET      : {system.PORTFOLIO_VOL_TARGET:.0%}")
    print(f"Realized vol (full)       : {rets.std() * np.sqrt(TD):.2%}")
    print(f"Vol budget actually used  : {(rets.std() * np.sqrt(TD)) / system.PORTFOLIO_VOL_TARGET:.0%}")
    print()
    print(f"Gross exposure  mean={gross.mean():.1%}  median={gross.median():.1%}  "
          f"min={gross.min():.1%}  max={gross.max():.1%}")
    print(f"Days at >90% invested     : {(gross > 0.90).mean():.1%} of sample")
    print(f"Days at <60% invested     : {(gross < 0.60).mean():.1%} of sample")
    print(f"Average cash (undeployed) : {1 - gross.mean():.1%}")

    print("\n--- by regime (where is the drag worst?) ---")
    print(f"  {'regime':<15}{'days':>7}{'avg gross':>12}{'realized vol':>14}{'ann return':>12}")
    for r, idx in book.groupby(reg).groups.items():
        g = gross.loc[idx]
        rr = rets.loc[idx]
        ann = (1 + rr.mean()) ** TD - 1
        print(f"  {r:<15}{len(idx):>7}{g.mean():>11.1%}{rr.std() * np.sqrt(TD):>13.1%}{ann:>12.1%}")

    print("\n--- the cost: unused vol budget by regime ---")
    for r, idx in book.groupby(reg).groups.items():
        rr = rets.loc[idx]
        v = rr.std() * np.sqrt(TD)
        head = system.PORTFOLIO_VOL_TARGET / v if v > 0 else float("nan")
        print(f"  {r:<15} realized {v:>6.1%} vs target {system.PORTFOLIO_VOL_TARGET:.0%} "
              f"-> {head:.2f}x headroom unused")

    print("\n--- risk-off / defensive holdings share ---")
    defensive = [s for s in ["TLT", "IEF", "GLD", "DBC", "USMV", "BIL"] if s in book.columns]
    dgross = book[defensive].sum(axis=1)
    print(f"  defensive ETFs avg weight : {dgross.mean():.1%} of equity")
    print(f"  as share of invested book : {(dgross / gross.replace(0, np.nan)).mean():.1%}")
    print(f"  CASH avg weight           : {1 - gross.mean():.1%} of equity  <-- the real 'risk-off' position")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
