from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal

from .config import EngineSettings, PairConfig
from .pnl import PnLTracker
from .state import PairRuntimeState

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    allowed: bool
    reason: str


class RiskManager:
    """Evaluates whether a pair is allowed to quote given current risk."""

    def __init__(self, settings: EngineSettings, pnl: PnLTracker) -> None:
        self._settings = settings
        self._pnl = pnl

    def evaluate(self, cfg: PairConfig, state: PairRuntimeState, stable_balance: Decimal) -> RiskAssessment:
        now = time.time()
        if now < state.cooldown_until:
            return RiskAssessment(False, f"cooldown {state.cooldown_until - now:.1f}s")

        if stable_balance < cfg.min_notional_usd:
            logger.info(
                "[RISK] %s %s insufficient_balance: have=%s need=%s",
                cfg.exchange.upper(),
                cfg.symbol,
                stable_balance.quantize(Decimal("0.01")),
                cfg.min_notional_usd,
            )
            return RiskAssessment(False, "insufficient_balance")
        
        # Additional check: ensure we have enough balance for at least a probe order
        # This prevents trying to place orders that will fail
        min_required = max(cfg.min_notional_usd, self._settings.tier_probe_size_usd)
        if stable_balance < min_required:
            logger.info(
                "[RISK] %s %s balance too low for trading: have=%s need=%s (min_notional=%s probe_size=%s)",
                cfg.exchange.upper(),
                cfg.symbol,
                stable_balance.quantize(Decimal("0.01")),
                min_required.quantize(Decimal("0.01")),
                cfg.min_notional_usd,
                self._settings.tier_probe_size_usd,
            )
            return RiskAssessment(False, "insufficient_balance")

        stats = self._pnl.get_stats(self._pair_key(cfg))
        if stats.realized <= -self._settings.max_pair_loss_usd:
            return RiskAssessment(False, "pair_drawdown")

        if self._pnl.total_realized <= -self._settings.max_total_loss_usd:
            return RiskAssessment(False, "global_drawdown")

        if len(state.recent_realized) >= self._settings.negative_fill_lookback:
            window = list(state.recent_realized)[-self._settings.negative_fill_lookback:]
            if window and all(value <= 0 for value in window):
                return RiskAssessment(False, "pnl_negative")

        if state.hedge_failure_ts:
            elapsed = time.time() - state.hedge_failure_ts
            if elapsed < self._settings.hedge_force_flat_seconds:
                return RiskAssessment(False, "hedge_recovering")

        if state.inventory:
            while state.inventory and (state.inventory[0].amount * state.inventory[0].price) < cfg.min_notional_usd:
                state.inventory.popleft()
            if state.inventory:
                oldest = state.inventory[0]
                age = now - oldest.timestamp
                if age > self._settings.max_inventory_age_s:
                    return RiskAssessment(False, f"inventory_age {age:.1f}s")

        return RiskAssessment(True, "ok")

    def register_fill_result(self, state: PairRuntimeState, result: str, realized: Decimal) -> None:
        now = time.time()
        if result == "win":
            cooldown = self._settings.win_cooldown_s
        elif result == "loss":
            loss_amount = abs(realized)
            threshold = self._settings.loss_cooldown_threshold_usd
            if loss_amount < threshold:
                cooldown = self._settings.neutral_cooldown_s
                logger.debug(
                    "Applying short cooldown (%.2fs) after small loss %.4f",
                    cooldown,
                    float(loss_amount),
                )
            else:
                cooldown = self._settings.loss_cooldown_s
        elif result == "flat":
            cooldown = self._settings.neutral_cooldown_s
        else:
            cooldown = 0.0
        if cooldown > 0:
            state.cooldown_until = max(state.cooldown_until, now + cooldown)

    @staticmethod
    def _pair_key(cfg: PairConfig) -> str:
        return f"{cfg.exchange}:{cfg.symbol}"
