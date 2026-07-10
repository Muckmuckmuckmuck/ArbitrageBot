#!/usr/bin/env python3
"""Daily report + research-paper generator.

Produces two artifacts under reports/ from the tracked data:
  - report_<date>.md   : performance snapshot (live account if IBKR reachable +
                         backtest scorecard + regime + today's target book)
  - RESEARCH_LOG.md     : an accumulating research paper — dated findings, what's
                         working / weak, and hypotheses to test next

Runs anywhere: on the VM it adds live IBKR P&L; elsewhere it uses backtest + the
latest target-book artifact. Prints a concise summary to stdout for the scheduler.
"""
from __future__ import annotations

import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quantbot import system, universe  # noqa: E402
from quantbot.config import DATA_DIR, REPO_ROOT, settings  # noqa: E402
from quantbot.data.history import get_prices  # noqa: E402
from quantbot.regime.classifier import classify  # noqa: E402
from quantbot.backtest.engine import returns_by_regime  # noqa: E402

REPORTS = REPO_ROOT / "reports"


def live_account():
    """Live IBKR paper P&L if the Gateway is reachable, else None."""
    try:
        from quantbot.broker.ibkr import IBKRBroker
        from quantbot.config import IBKRConfig
        b = IBKRBroker(IBKRConfig(client_id=11))
        b.connect()
        try:
            eq = b.net_liquidation()
            pos = b.positions()
            return {"equity": eq, "positions": pos}
        finally:
            b.disconnect()
    except Exception:
        return None


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    px = get_prices(universe.all_symbols(), start=settings.data.start)
    regime = classify(px[universe.BENCHMARK])
    results, book = system.build_results(px, regime, settings)
    comb, spy = results["combined"].stats, results["spy"].stats
    reg = str(regime["regime"].iloc[-1])
    target = book.iloc[-1]
    holdings = target[target > 1e-4].sort_values(ascending=False)
    rbr = returns_by_regime(results["combined"].returns, regime)
    live = live_account()

    # -- daily report --
    L = [f"# quantbot daily report — {day}", ""]
    L.append(f"**Regime:** {reg}  ·  **Target gross:** {target.sum():.0%}  ·  **Mode:** {settings.mode.value}")
    L.append("")
    if live:
        start_eq = 1_000_000.0
        pnl = live["equity"] - start_eq
        L += ["## Live paper account", "",
              f"- Net liquidation: **${live['equity']:,.0f}**  (P&L since start: {pnl:+,.0f}, {pnl/start_eq:+.2%})",
              f"- Open positions: {len(live['positions'])}", ""]
        for s, q in sorted(live["positions"].items()):
            L.append(f"  - {s}: {q:.0f} sh")
        L.append("")
    else:
        L += ["## Live paper account", "", "_Gateway not reachable from here — run on the VM for live P&L._", ""]
    L += ["## Strategy scorecard (backtest, 2010→now)", "",
          "| | CAGR | Sharpe | MaxDD |", "|---|---|---|---|",
          f"| Combined | {comb['CAGR']:.1%} | {comb['Sharpe']:.2f} | {comb['MaxDD']:.1%} |",
          f"| High-growth | {results['high_growth'].stats['CAGR']:.1%} | {results['high_growth'].stats['Sharpe']:.2f} | {results['high_growth'].stats['MaxDD']:.1%} |",
          f"| Buy&Hold SPY | {spy['CAGR']:.1%} | {spy['Sharpe']:.2f} | {spy['MaxDD']:.1%} |", ""]
    L += ["## Per-regime attribution (combined)", "", "| regime | days | ann.return | ann.vol |", "|---|---|---|---|"]
    for r, row in rbr.iterrows():
        L.append(f"| {r} | {int(row['days'])} | {row['ann_return']:.1%} | {row['ann_vol']:.1%} |")
    L += ["", "## Today's target book", ""]
    for s, w in holdings.items():
        L.append(f"- {s}: {w:.1%}  [{universe.sleeve_of(s)}]")
    report_path = REPORTS / f"report_{day}.md"
    report_path.write_text("\n".join(L) + "\n")

    # -- append to the research paper --
    worst_reg = rbr["ann_return"].idxmin()
    entry = [
        f"\n## {day}",
        f"- Combined (backtest): {comb['CAGR']:.1%} CAGR, Sharpe {comb['Sharpe']:.2f}, MaxDD {comb['MaxDD']:.1%} "
        f"(vs SPY {spy['CAGR']:.1%}/{spy['Sharpe']:.2f}/{spy['MaxDD']:.1%}).",
        f"- Current regime: {reg}. Weakest historical regime: **{worst_reg}** "
        f"({rbr.loc[worst_reg, 'ann_return']:.1%} ann) — the standing research target.",
        f"- Live: {'$%.0f NLV' % live['equity'] if live else 'n/a (not on VM)'}.",
        "- Next hypothesis to test: see scripts/ablation.py / kronos_volume_test.py for the search space "
        "(signal horizons, vol targets, sleeve mix). Deploy only if it beats current OOS.",
    ]
    paper = REPORTS / "RESEARCH_LOG.md"
    header = "" if paper.exists() else "# quantbot research log\n\nAccumulating daily findings. Newest at the bottom.\n"
    with paper.open("a") as f:
        if header:
            f.write(header)
        f.write("\n".join(entry) + "\n")

    print(f"[report] {report_path.relative_to(REPO_ROOT)}")
    print(f"[paper]  {paper.relative_to(REPO_ROOT)} (appended {day})")
    print(f"SUMMARY {day}: regime={reg} gross={target.sum():.0%} "
          f"combined_backtest={comb['CAGR']:.1%}/{comb['Sharpe']:.2f} "
          f"live={'$%.0f' % live['equity'] if live else 'n/a'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
