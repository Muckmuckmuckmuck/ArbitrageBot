#!/usr/bin/env python3
"""Prove the historical-data pipeline works on real stock data (no broker needed).

Fetches the full universe, prints coverage, and a 12-1 momentum ranking snapshot —
a preview of what the high-growth trend/momentum sleeve will act on.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quantbot import universe  # noqa: E402
from quantbot.data.history import get_prices  # noqa: E402


def main() -> int:
    syms = universe.all_symbols()
    print(f"Fetching {len(syms)} symbols: {syms}\n")
    px = get_prices(syms, start="2010-01-01")
    print(f"Panel shape: {px.shape[0]} trading days x {px.shape[1]} symbols")
    print(f"Date range : {px.index.min().date()} -> {px.index.max().date()}")
    got = list(px.columns)
    missing = [s for s in syms if s not in got]
    print(f"Got data for {len(got)} symbols" + (f"; MISSING: {missing}" if missing else "; none missing"))

    # 12-month-minus-1-month momentum (classic trend signal), latest snapshot.
    lookback, skip = 252, 21
    if len(px) > lookback:
        mom = (px.shift(skip) / px.shift(lookback) - 1.0).iloc[-1].dropna().sort_values(ascending=False)
        print("\n12-1 momentum ranking (latest):")
        for sym, m in mom.items():
            flag = "  <- positive" if m > 0 else ""
            print(f"  {sym:<6}{m:+7.1%}{flag}")
    print("\nData pipeline OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
