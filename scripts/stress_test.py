#!/usr/bin/env python3
"""Walk-forward / stress evaluation: does the system 'behave well in different
periods'? Reports per-calendar-year returns and performance through named crises,
combined & per-sleeve vs buy-and-hold SPY.

    python scripts/stress_test.py
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
from quantbot.backtest import metrics  # noqa: E402

LINES = ["high_growth", "mid_growth", "safe_growth", "combined", "spy"]

# Named stress windows to prove behavior across regimes.
STRESS_WINDOWS = {
    "2018 Q4 selloff":  ("2018-10-01", "2018-12-24"),
    "COVID crash 2020": ("2020-02-19", "2020-03-23"),
    "2022 bear market": ("2022-01-01", "2022-10-12"),
}


def year_returns(returns: pd.Series) -> pd.Series:
    return (1.0 + returns).groupby(returns.index.year).prod() - 1.0


def main() -> int:
    px = get_prices(universe.all_symbols(), start=settings.data.start)
    regime = classify(px[universe.BENCHMARK])
    results, _ = system.build_results(px, regime, settings)

    # --- per-year returns (the 'behaves well across periods' view) ---
    yr = pd.DataFrame({k: year_returns(results[k].returns) for k in LINES})
    print("Calendar-year returns:")
    print(f"  {'year':<6}" + "".join(f"{k.split('_')[0]:>11}" for k in LINES))
    for y, row in yr.iterrows():
        print(f"  {int(y):<6}" + "".join(f"{row[k]:>10.1%} " for k in LINES))

    # --- crisis windows: return + max drawdown inside each window ---
    print("\nStress windows (return / maxDD inside window):")
    print(f"  {'window':<20}" + "".join(f"{k.split('_')[0]:>16}" for k in ["combined", "spy"]))
    window_report = {}
    for name, (a, b) in STRESS_WINDOWS.items():
        cells = {}
        row = f"  {name:<20}"
        for k in ["combined", "spy"]:
            eq = results[k].equity.loc[a:b]
            if len(eq) < 2:
                row += f"{'n/a':>16}"
                continue
            tot = eq.iloc[-1] / eq.iloc[0] - 1.0
            mdd = metrics.max_drawdown(eq)
            cells[k] = {"return": float(tot), "maxDD": float(mdd)}
            row += f"{tot:>8.1%}/{mdd:>6.1%}"
        print(row)
        window_report[name] = cells

    # --- worst / best calendar years (robustness) ---
    print("\nRobustness (combined vs SPY):")
    for k in ["combined", "spy"]:
        s = yr[k]
        print(f"  {k:<10} worst yr {s.min():+.1%} ({int(s.idxmin())}), "
              f"best yr {s.max():+.1%} ({int(s.idxmax())}), "
              f"positive {int((s > 0).sum())}/{len(s)} yrs")

    out = DATA_DIR / "backtests"
    out.mkdir(parents=True, exist_ok=True)
    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    (out / f"stress_{stamp}.json").write_text(json.dumps({
        "year_returns": yr.round(4).reset_index().rename(columns={"index": "year"}).to_dict(orient="records"),
        "stress_windows": window_report,
    }, indent=2, default=float))
    print(f"\nArtifacts -> {out}/stress_{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
