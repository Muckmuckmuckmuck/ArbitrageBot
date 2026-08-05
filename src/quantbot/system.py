"""Assemble the full system once, so every script evaluates the exact same book.

AGGRESSION PROFILES
-------------------
The original book was structurally under-risked: `apply_vol_target` was capped at
max_leverage=1.0, so vol targeting could only ever CUT exposure, never restore it
when realized vol sat below target. Applied twice (sleeve + portfolio) and stacked
with regime tilt and hard caps, that left ~34% average cash and used only ~62% of
the vol budget — i.e. the book was hedging its own upside.

A Profile makes that a deliberate dial instead of an accident. Each profile carries
its own risk envelope (position/gross/drawdown caps) so a more aggressive setting is
an explicit choice, never a silent bypass of the risk engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import pandas as pd

from quantbot import universe
from quantbot.allocator import Allocator, Sleeve
from quantbot.backtest.engine import BacktestResult, buy_and_hold, run_backtest
from quantbot.config import RiskLimits
from quantbot.data.history import get_volume
from quantbot.risk.engine import drawdown_kill_switch, enforce_caps
from quantbot.strategies import common
from quantbot.strategies.global_rotation import GlobalRotation
from quantbot.strategies.trend_momentum import TrendMomentum

HIGH = universe.SLEEVES["high_growth"]
MID = universe.SLEEVES["mid_growth"]
SAFE = universe.SLEEVES["safe_growth"]
CASH = universe.CASH_PROXY

# Ablation-validated signal: blended 3/6/12-month momentum, monthly cadence,
# confirmed by volume trend. (Multi-horizon robustly lifted Sharpe on every sleeve;
# vol-normalization was a wash and biweekly cadence hurt.)
SIGNAL = dict(lookbacks=(63, 126, 252), vol_normalize=False, rebalance="M")


@dataclass(frozen=True)
class Profile:
    """A complete risk/return operating point."""
    name: str
    base_weights: Dict[str, float]      # sleeve capital split
    vol_target: Dict[str, float]        # per-sleeve vol target
    portfolio_vol_target: float
    max_leverage: float                 # >1 => vol targeting may scale UP
    max_single_position_pct: float
    max_gross_exposure_pct: float
    max_drawdown_pct: float             # kill-switch threshold
    high_top_n: int = 2

    def limits(self) -> RiskLimits:
        return RiskLimits(
            max_single_position_pct=self.max_single_position_pct,
            max_sleeve_pct=0.90,
            max_gross_exposure_pct=self.max_gross_exposure_pct,
            max_daily_loss_pct=0.03,
            max_drawdown_pct=self.max_drawdown_pct,
        )


PROFILES: Dict[str, Profile] = {
    # Original shipped behaviour — kept as the reference point.
    "balanced": Profile(
        name="balanced",
        base_weights={"high_growth": 0.50, "mid_growth": 0.30, "safe_growth": 0.20},
        vol_target={"high_growth": 0.24, "mid_growth": 0.16, "safe_growth": 0.12},
        portfolio_vol_target=0.16, max_leverage=1.0,
        max_single_position_pct=0.20, max_gross_exposure_pct=1.00, max_drawdown_pct=0.20,
    ),
    # Fixes the cash drag: two-sided vol targeting, still unlevered overall.
    "growth": Profile(
        name="growth",
        base_weights={"high_growth": 0.62, "mid_growth": 0.25, "safe_growth": 0.13},
        vol_target={"high_growth": 0.28, "mid_growth": 0.18, "safe_growth": 0.13},
        portfolio_vol_target=0.20, max_leverage=1.35,
        max_single_position_pct=0.30, max_gross_exposure_pct=1.35, max_drawdown_pct=0.28,
    ),
    # Momentum-led, meaningfully risk-on.
    "aggressive": Profile(
        name="aggressive",
        base_weights={"high_growth": 0.75, "mid_growth": 0.17, "safe_growth": 0.08},
        vol_target={"high_growth": 0.32, "mid_growth": 0.20, "safe_growth": 0.14},
        portfolio_vol_target=0.26, max_leverage=1.8,
        max_single_position_pct=0.38, max_gross_exposure_pct=1.80, max_drawdown_pct=0.35,
        high_top_n=3,
    ),
    "max_growth": Profile(
        name="max_growth",
        base_weights={"high_growth": 0.86, "mid_growth": 0.10, "safe_growth": 0.04},
        vol_target={"high_growth": 0.38, "mid_growth": 0.22, "safe_growth": 0.15},
        portfolio_vol_target=0.32, max_leverage=2.2,
        max_single_position_pct=0.45, max_gross_exposure_pct=2.20, max_drawdown_pct=0.42,
        high_top_n=3,
    ),
    # The ~30% CAGR operating point: essentially the pure high-growth momentum sleeve.
    # Downside protection comes from the REGIME GATE (high_growth is cut to 0.15x in
    # bear_volatile, i.e. it goes to cash) rather than from permanently holding
    # risk-off ETFs — which is what was capping the upside. Expect ~-35% drawdowns.
    "momentum_max": Profile(
        name="momentum_max",
        base_weights={"high_growth": 0.94, "mid_growth": 0.04, "safe_growth": 0.02},
        vol_target={"high_growth": 0.34, "mid_growth": 0.20, "safe_growth": 0.14},
        portfolio_vol_target=0.34, max_leverage=2.0,
        max_single_position_pct=0.50, max_gross_exposure_pct=2.00, max_drawdown_pct=0.40,
        high_top_n=3,
    ),
}

DEFAULT_PROFILE = "balanced"

# Back-compat aliases (older scripts import these directly).
VOL_TARGET = PROFILES[DEFAULT_PROFILE].vol_target
PORTFOLIO_VOL_TARGET = PROFILES[DEFAULT_PROFILE].portfolio_vol_target


def get_profile(profile: Optional[str | Profile] = None) -> Profile:
    """Resolve a profile: explicit arg > QUANTBOT_PROFILE env > default."""
    if isinstance(profile, Profile):
        return profile
    if profile is None:
        from quantbot.config import settings as _s
        profile = getattr(_s, "profile", None) or DEFAULT_PROFILE
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; choose from {sorted(PROFILES)}")
    return PROFILES[profile]


def build_sleeves(profile: Optional[Profile] = None):
    p = get_profile(profile)
    high = TrendMomentum(top_n=p.high_top_n, weighting="momentum", **SIGNAL)
    mid = GlobalRotation(MID, CASH, top_n=3, weighting="momentum", **SIGNAL)
    safe = GlobalRotation(SAFE, CASH, top_n=3, weighting="equal", **SIGNAL)
    return high, mid, safe


def build_results(
    px: pd.DataFrame,
    regime: pd.DataFrame,
    settings,
    base_weights=None,
    profile: Optional[str | Profile] = None,
) -> Tuple[Dict[str, BacktestResult], pd.DataFrame]:
    p = get_profile(profile)
    cols = px.columns
    base_weights = base_weights or p.base_weights
    cost, cash = settings.backtest.cost_bps, settings.backtest.cash_annual_rate
    high, mid, safe = build_sleeves(p)
    vol = get_volume(list(cols), start=str(px.index[0].date())).reindex(px.index).reindex(columns=cols)

    def vt(w: pd.DataFrame, target: float) -> pd.DataFrame:
        return common.apply_vol_target(
            w.reindex(columns=cols).fillna(0.0), px, target, max_leverage=p.max_leverage
        )

    r_high = run_backtest(px, vt(high.target_weights(px[HIGH], regime, vol[HIGH]), p.vol_target["high_growth"]), cost, cash)
    r_mid = run_backtest(px, vt(mid.target_weights(px[MID + [CASH]], regime, vol[MID + [CASH]]), p.vol_target["mid_growth"]), cost, cash)
    r_safe = run_backtest(px, vt(safe.target_weights(px[SAFE + [CASH]], regime, vol[SAFE + [CASH]]), p.vol_target["safe_growth"]), cost, cash)

    alloc = Allocator(
        sleeves=[
            Sleeve("high_growth", high, HIGH),
            Sleeve("mid_growth", mid, MID + [CASH]),
            Sleeve("safe_growth", safe, SAFE + [CASH]),
        ],
        base_weights=base_weights,
        portfolio_vol_target=p.portfolio_vol_target,
        regime_tilt=True,
        max_leverage=p.max_leverage,
    )
    book, _ = alloc.combined_weights(px, regime, vol)
    book = enforce_caps(book, p.limits())
    book = drawdown_kill_switch(book, px, p.max_drawdown_pct)
    r_comb = run_backtest(px, book, cost, cash)
    r_spy = buy_and_hold(px, universe.BENCHMARK)

    return {
        "high_growth": r_high,
        "mid_growth": r_mid,
        "safe_growth": r_safe,
        "combined": r_comb,
        "spy": r_spy,
    }, book
