#!/usr/bin/env python3
"""End-to-end execution proof WITHOUT IB Gateway.

Builds today's target book, rebalances a fresh $100k SimBroker paper account into it,
then re-runs the rebalance to prove idempotency (an already-on-target book should
generate ~no new orders). This exercises the exact code path the live IBKR run uses.

    python scripts/sim_trade.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quantbot import system, universe  # noqa: E402
from quantbot.config import settings  # noqa: E402
from quantbot.data.history import get_prices  # noqa: E402
from quantbot.regime.classifier import classify  # noqa: E402
from quantbot.broker.sim import SimBroker  # noqa: E402
from quantbot.execution.rebalancer import compute_orders  # noqa: E402


def _rebalance(broker, target, prices):
    return compute_orders(
        target, broker.net_liquidation(), broker.positions(), prices,
        min_trade_usd=settings.execution.min_trade_usd,
        max_single_position_pct=settings.risk.max_single_position_pct,
    )


def main() -> int:
    px = get_prices(universe.all_symbols(), start=settings.data.start)
    regime = classify(px[universe.BENCHMARK])
    _, book = system.build_results(px, regime, settings)
    target = book.iloc[-1]
    prices = dict(px.iloc[-1])

    broker = SimBroker(100_000.0, prices)
    print(f"Start: equity ${broker.net_liquidation():,.0f}, all cash, regime {regime['regime'].iloc[-1]}")

    orders = _rebalance(broker, target, prices)
    print(f"\nRebalance #1: {len(orders)} orders")
    for o in orders:
        broker.submit(o)
        print(f"  {o.side:<4} {o.symbol:<6}{o.shares:8.0f} sh  ~${o.est_notional:>8,.0f}  [{o.status}]")

    eq = broker.net_liquidation()
    pos = broker.positions()
    invested = sum(sh * prices[s] for s, sh in pos.items())
    print(f"\nAfter #1: equity ${eq:,.0f} | invested ${invested:,.0f} ({invested/eq:.0%}) | cash ${eq-invested:,.0f}")
    print(f"  target gross was {target.sum():.0%}")

    print(f"\n  {'symbol':<8}{'target$':>10}{'actual$':>10}{'drift$':>9}")
    ok = True
    for s in sorted(set(target[target > 1e-4].index) | set(pos)):
        tgt = float(target.get(s, 0.0)) * eq
        act = pos.get(s, 0.0) * prices.get(s, 0.0)
        drift = act - tgt
        if abs(drift) > max(prices.get(s, 0.0), 0.01 * eq):  # within ~1 share or 1% of equity
            ok = False
        print(f"  {s:<8}{tgt:>10,.0f}{act:>10,.0f}{drift:>9,.0f}")

    orders2 = _rebalance(broker, target, prices)
    print(f"\nRebalance #2 (idempotency, should be ~0): {len(orders2)} orders")

    passed = ok and len(orders2) <= 1
    print(f"\n{'PASS' if passed else 'CHECK'}: rebalancer converges to target and is stable.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
