"""Fast momentum sub-strategy: breakout / acceleration.

The core sleeves rank on 3/6/12-month momentum and rebalance monthly — deliberately
slow. This sleeve is the fast complement: it buys assets making new N-day highs while
in a confirmed uptrend, and rebalances weekly, so it enters emerging leaders long
before a monthly momentum rank would promote them (and exits them faster too).

Why this is a distinct edge rather than "the same signal, traded faster": the prior
ablation showed that simply rebalancing the *slow* signal biweekly HURT (whipsaw on a
signal built for monthly holding). This is a different signal — breakout + short-horizon
acceleration — whose natural holding period genuinely is shorter.

Evidence base: Donchian channel breakouts; Jegadeesh-Titman 3-12mo momentum;
Moskowitz-Ooi-Pedersen time-series momentum. Long-only, trend-gated (Faber).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from quantbot.strategies import common
from quantbot.strategies.base import Strategy


class BreakoutMomentum(Strategy):
    name = "breakout_momentum"
    sleeve = "high_growth"

    def __init__(
        self,
        breakout_window: int = 50,
        trend_window: int = 200,
        accel_window: int = 42,
        top_n: int = 2,
        vol_window: int = 60,
        rebalance: str = "W",
        weighting: str = "momentum",
        proximity: float = 0.97,
    ):
        self.breakout_window = breakout_window
        self.trend_window = trend_window
        self.accel_window = accel_window
        self.top_n = top_n
        self.vol_window = vol_window
        self.rebalance = rebalance
        self.weighting = weighting
        # How close to the N-day high counts as "breaking out" (1.0 = new high only).
        self.proximity = proximity

    def target_weights(
        self, prices: pd.DataFrame, regime: Optional[pd.DataFrame] = None,
        volume: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        px = prices.sort_index()
        # Rolling high excluding today, so "new high" is not trivially true.
        roll_max = px.rolling(self.breakout_window, min_periods=self.breakout_window // 2).max().shift(1)
        nearness = px / roll_max                       # >= 1.0 => new N-day high
        up = common.trend_up(px, self.trend_window)     # Faber regime filter
        accel = px.pct_change(self.accel_window)        # short-horizon acceleration
        vol = common.realized_vol(px, self.vol_window)

        if volume is not None:  # volume confirmation (same idea as the core sleeves)
            vt = common.volume_trend(volume).reindex(index=accel.index, columns=accel.columns).fillna(1.0)
            accel = accel * vt

        def decide(dt: pd.Timestamp) -> pd.Series:
            out = pd.Series(0.0, index=px.columns)
            near = nearness.loc[dt]
            cand = [
                s for s in px.columns
                if pd.notna(near.get(s)) and near[s] >= self.proximity
                and bool(up.loc[dt, s]) and float(accel.loc[dt, s] or 0) > 0
            ]
            if not cand:
                return out                              # nothing breaking out -> cash
            cand = sorted(cand, key=lambda s: float(accel.loc[dt, s]), reverse=True)[: self.top_n]
            w = common.combine_weights(cand, self.weighting, vol.loc[dt], accel.loc[dt])
            fill = len(cand) / self.top_n               # thin breadth keeps cash
            for s in cand:
                out[s] = w[s] * fill
            return out

        return common.periodic_rebalance(px, decide, self.rebalance)
