"""Portfolio allocator — blends the three sleeves, tilts by regime, then vol-targets.

1. Each sleeve produces target weights on its own symbols.
2. Sleeve capital is tilted by the current regime (more momentum in calm bull markets,
   more defense in bear/volatile ones).
3. The blended book is scaled to a constant portfolio vol target (Moreira-Muir),
   which can only *reduce* gross exposure (long-only) — the top-level crash brake.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd

from quantbot.strategies import common
from quantbot.strategies.base import Strategy

# Regime -> per-sleeve multiplier applied to the base capital split.
REGIME_TILT: Dict[str, Dict[str, float]] = {
    "bull_calm":     {"high_growth": 1.5, "mid_growth": 1.0, "safe_growth": 0.4},
    "bull_volatile": {"high_growth": 1.0, "mid_growth": 1.0, "safe_growth": 0.8},
    "bear_calm":     {"high_growth": 0.4, "mid_growth": 0.8, "safe_growth": 1.5},
    "bear_volatile": {"high_growth": 0.15, "mid_growth": 0.5, "safe_growth": 1.8},
    "unknown":       {"high_growth": 1.0, "mid_growth": 1.0, "safe_growth": 1.0},
}


@dataclass
class Sleeve:
    name: str
    strategy: Strategy
    symbols: List[str]


class Allocator:
    def __init__(
        self,
        sleeves: List[Sleeve],
        base_weights: Dict[str, float],
        portfolio_vol_target: float = 0.10,
        regime_tilt: bool = True,
        vol_window: int = 60,
    ):
        self.sleeves = sleeves
        self.base_weights = base_weights
        self.portfolio_vol_target = portfolio_vol_target
        self.regime_tilt = regime_tilt
        self.vol_window = vol_window

    def _sleeve_allocations(self, index: pd.DatetimeIndex, regime: pd.DataFrame) -> pd.DataFrame:
        """Time-varying capital fraction per sleeve (rows sum to 1)."""
        names = [s.name for s in self.sleeves]
        if not self.regime_tilt or regime is None:
            alloc = pd.DataFrame(
                {n: self.base_weights.get(n, 0.0) for n in names}, index=index
            )
        else:
            reg = regime["regime"].reindex(index).ffill().fillna("unknown")
            rows = []
            for r in reg:
                tilt = REGIME_TILT.get(r, REGIME_TILT["unknown"])
                rows.append({n: self.base_weights.get(n, 0.0) * tilt.get(n, 1.0) for n in names})
            alloc = pd.DataFrame(rows, index=index)
        return alloc.div(alloc.sum(axis=1).replace(0.0, 1.0), axis=0)  # normalize to 1

    def combined_weights(
        self, prices: pd.DataFrame, regime: pd.DataFrame, volume: pd.DataFrame = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Return (portfolio weights on all columns, sleeve allocation panel)."""
        alloc = self._sleeve_allocations(prices.index, regime)
        book = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        for s in self.sleeves:
            syms = [c for c in s.symbols if c in prices.columns]
            vol_sub = volume[[c for c in syms if c in volume.columns]] if volume is not None else None
            w = s.strategy.target_weights(prices[syms], regime, vol_sub)
            w = w.reindex(index=prices.index, columns=prices.columns).fillna(0.0)
            book = book + w.mul(alloc[s.name], axis=0)
        book = common.apply_vol_target(
            book, prices, self.portfolio_vol_target, self.vol_window, max_leverage=1.0
        )
        return book, alloc
