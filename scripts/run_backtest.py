#!/usr/bin/env python3
"""Run the full system on real data and report each sleeve against its OBJECTIVE.

    python scripts/run_backtest.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from quantbot import system, universe  # noqa: E402
from quantbot.config import DATA_DIR, settings  # noqa: E402
from quantbot.data.history import get_prices  # noqa: E402
from quantbot.regime.classifier import classify  # noqa: E402
from quantbot.backtest.engine import returns_by_regime  # noqa: E402

OBJECTIVE = {
    "high_growth": "beat SPY",
    "mid_growth": "~9-11% (SPY-lite)",
    "safe_growth": "~7% (> HYSA)",
    "combined": "blend",
    "spy": "benchmark",
}


def _fmt(s: dict) -> str:
    return (f"{s['CAGR']:+7.2%}{s['AnnVol']:8.2%}{s['Sharpe']:8.2f}{s['Sortino']:8.2f}"
            f"{s['MaxDD']:9.2%}{s['Calmar']:8.2f}{s['TotalReturn']:11.1%}")


def main() -> int:
    print(f"Fetching {len(universe.all_symbols())} symbols since {settings.data.start} ...")
    px = get_prices(universe.all_symbols(), start=settings.data.start)
    regime = classify(px[universe.BENCHMARK])
    results, book = system.build_results(px, regime, settings)

    hdr = f"{'Sleeve':<22}{'CAGR':>8}{'Vol':>8}{'Sharpe':>8}{'Sortino':>8}{'MaxDD':>9}{'Calmar':>8}{'Total':>11}   Objective"
    print("\n" + hdr + "\n" + "-" * len(hdr))
    order = ["high_growth", "mid_growth", "safe_growth", "combined", "spy"]
    for k in order:
        print(f"{k:<22}{_fmt(results[k].stats)}   {OBJECTIVE[k]}")

    print("\nPer-regime attribution (COMBINED):")
    rbr = returns_by_regime(results["combined"].returns, regime)
    print(f"  {'regime':<15}{'days':>7}{'ann_return':>13}{'ann_vol':>10}")
    for reg, row in rbr.iterrows():
        print(f"  {reg:<15}{int(row['days']):>7}{row['ann_return']:>12.1%}{row['ann_vol']:>10.1%}")

    latest = book.iloc[-1]
    live = latest[latest > 1e-4].sort_values(ascending=False)
    print(f"\nToday's target book ({regime['regime'].iloc[-1]}, gross {latest.sum():.0%}):")
    for s, w in live.items():
        print(f"  {s:<6}{w:6.1%}  [{universe.sleeve_of(s)}]")

    out = DATA_DIR / "backtests"
    out.mkdir(parents=True, exist_ok=True)
    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    (out / f"system_{stamp}.json").write_text(json.dumps({
        "run": stamp,
        "period": [str(px.index.min().date()), str(px.index.max().date())],
        "results": {k: results[k].stats for k in order},
        "combined_per_regime": rbr.reset_index().to_dict(orient="records"),
        "today_book": {s: float(w) for s, w in live.items()},
    }, indent=2, default=float))
    pd.DataFrame({k: results[k].equity for k in order}).to_csv(out / f"equity_{stamp}.csv")
    print(f"\nArtifacts -> {out}/system_{stamp}.json, equity_{stamp}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
