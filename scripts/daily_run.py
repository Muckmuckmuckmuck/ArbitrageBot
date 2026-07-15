#!/usr/bin/env python3
"""Headless daily run for the cloud VM (systemd timer / cron).

Pipeline: fetch data -> classify regime -> build target book -> connect broker ->
compute rebalance orders -> place them (or dry-run) -> log + write JSON artifact.

Safety:
  - PAPER mode by default; require_live_ready() refuses LIVE on a paper port.
  - execution.execute=False -> DRY-RUN (orders computed + logged, nothing placed).
  - No IBKR reachable -> falls back to an in-memory SimBroker dry-run so the VM still
    produces a daily target book before IB Gateway is set up.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quantbot import system, universe  # noqa: E402
from quantbot.config import DATA_DIR, settings  # noqa: E402
from quantbot.data.history import get_prices  # noqa: E402
from quantbot.regime.classifier import classify  # noqa: E402
from quantbot.broker.base import Broker  # noqa: E402
from quantbot.broker.sim import SimBroker  # noqa: E402
from quantbot.execution.rebalancer import compute_orders  # noqa: E402


def _setup_logging() -> logging.Logger:
    logdir = DATA_DIR / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(logdir / "quantbot.log"), logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("quantbot")


def _select_broker(prices_last, log) -> tuple[Broker, str]:
    """IBKR when execution is enabled and reachable; otherwise a SimBroker dry-run."""
    if settings.execution.execute:
        try:
            from quantbot.broker.ibkr import IBKRBroker

            broker = IBKRBroker(settings.ibkr, order_type=settings.execution.order_type)
            broker.connect()
            return broker, "ibkr"
        except Exception as exc:  # gateway down / ib_async missing -> safe fallback
            log.error("IBKR connect failed (%s); falling back to SimBroker dry-run", exc)
    broker = SimBroker(settings.starting_equity_usd, dict(prices_last))
    broker.connect()
    return broker, "sim"


def main() -> int:
    log = _setup_logging()
    log.info(f"=== daily run start | mode={settings.mode.value} execute={settings.execution.execute} ===")
    try:
        settings.require_live_ready()  # refuse LIVE on a paper port

        px = get_prices(universe.all_symbols(), start=settings.data.start)
        regime = classify(px[universe.BENCHMARK])
        _, book = system.build_results(px, regime, settings)

        asof = px.index[-1].date()
        reg = str(regime["regime"].iloc[-1])
        target = book.iloc[-1]
        prices_last = px.iloc[-1]
        holdings = target[target > 1e-4].sort_values(ascending=False)

        log.info(f"data asof {asof} | regime {reg} | gross {target.sum():.0%}")
        for sym, w in holdings.items():
            log.info(f"  TARGET {sym:<6}{w:6.1%}  [{universe.sleeve_of(sym)}]")

        broker, kind = _select_broker(prices_last, log)
        do_execute = settings.execution.execute and kind == "ibkr"
        # Execution was requested but we could not reach IBKR -> we are NOT trading.
        # Make this loud: log CRITICAL and exit non-zero so systemd marks the unit failed
        # instead of silently "succeeding" while placing nothing.
        degraded = settings.execution.execute and kind != "ibkr"
        if degraded:
            log.critical("NOT TRADING — execution is enabled but IB Gateway is unreachable; "
                         "fell back to dry-run. Fix the Gateway (systemctl restart ibc).")
        placed = []
        try:
            equity = broker.net_liquidation()
            positions = broker.positions()
            log.info(f"broker={kind} equity=${equity:,.0f} positions={len(positions)}")
            orders = compute_orders(
                target, equity, positions, prices_last,
                min_trade_usd=settings.execution.min_trade_usd,
                allow_fractional=settings.execution.allow_fractional,
                max_single_position_pct=settings.risk.max_single_position_pct,
            )
            log.info(f"{len(orders)} orders ({'EXECUTING' if do_execute else 'DRY-RUN'})")
            for o in orders:
                if do_execute:
                    o = broker.submit(o)
                log.info(f"  {o.side:<4} {o.symbol:<6}{o.shares:9.2f} sh  ~${o.est_notional:,.0f}  [{o.status}]")
                placed.append(o)
        finally:
            broker.disconnect()

        live = DATA_DIR / "live"
        live.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        (live / f"target_{stamp}.json").write_text(json.dumps({
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "data_asof": str(asof),
            "regime": reg,
            "gross_exposure": float(target.sum()),
            "mode": settings.mode.value,
            "broker": kind,
            "executed": do_execute,
            "target_book": {s: float(w) for s, w in holdings.items()},
            "orders": [
                {"symbol": o.symbol, "side": o.side, "shares": o.shares,
                 "est_notional": o.est_notional, "status": o.status}
                for o in placed
            ],
        }, indent=2))
        if degraded:
            log.error("=== daily run DEGRADED (no orders placed) ===")
            return 2
        log.info("=== daily run ok ===")
        return 0
    except Exception:
        logging.getLogger("quantbot").exception("daily run FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
