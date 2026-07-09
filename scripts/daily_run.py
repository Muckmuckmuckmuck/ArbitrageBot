#!/usr/bin/env python3
"""Headless daily run for the cloud VM (driven by systemd timer / cron).

Computes the current market regime + target portfolio book and logs it. Order
execution via IBKR is a TODO seam (the paper adapter isn't wired yet) — for now this
records exactly what the system would hold so it can be audited/acted on, and
auto-execution drops in at the marked spot later. Non-interactive; logs to
data/logs/quantbot.log and writes a dated target-book artifact.
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


def _setup_logging() -> logging.Logger:
    logdir = DATA_DIR / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(logdir / "quantbot.log"), logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("quantbot")


def main() -> int:
    log = _setup_logging()
    log.info("=== daily run start | mode=%s ===", settings.mode.value)
    try:
        px = get_prices(universe.all_symbols(), start=settings.data.start)
        regime = classify(px[universe.BENCHMARK])
        _, book = system.build_results(px, regime, settings)

        asof = px.index[-1].date()
        reg = str(regime["regime"].iloc[-1])
        target = book.iloc[-1]
        holdings = target[target > 1e-4].sort_values(ascending=False)

        log.info("data asof %s | regime %s | gross %.0f%%", asof, reg, 100 * target.sum())
        for sym, w in holdings.items():
            log.info("  TARGET %-6s %5.1f%%  [%s]", sym, 100 * w, universe.sleeve_of(sym))

        live = DATA_DIR / "live"
        live.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        (live / f"target_{stamp}.json").write_text(json.dumps({
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "data_asof": str(asof),
            "regime": reg,
            "gross_exposure": float(target.sum()),
            "mode": settings.mode.value,
            "target_book": {s: float(w) for s, w in holdings.items()},
        }, indent=2))

        # --- execution seam (IBKR paper adapter to be wired here) ---
        if settings.mode.value == "LIVE":
            log.warning("LIVE mode set but IBKR execution adapter not wired yet — "
                        "no orders placed; target book logged only.")
        # else: PAPER — record only.

        log.info("=== daily run ok ===")
        return 0
    except Exception:
        log.exception("daily run FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
