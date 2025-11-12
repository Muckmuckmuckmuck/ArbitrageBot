from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class PairConfig:
    """Static configuration for a traded pair."""

    exchange: str
    symbol: str
    base: str
    quote: str
    order_size_usd: Decimal = Decimal("5")
    min_notional_usd: Decimal = Decimal("3")
    target_edge_bps: int = 12
    probe_edge_bps: int = 4
    slippage_buffer_bps: int = 2
    maker_fee_bps: int = 12
    taker_fee_bps: int = 25
    depth_clip_fraction: Decimal = Decimal("0.2")
    max_spread_bps: int = 150
    min_spread_bps: int = 6
    volatility_floor_bps: int = 25
    volatility_ceiling_bps: int = 250


@dataclass
class EngineSettings:
    """Global controls for the scalper engine."""

    poll_interval_s: float = 0.6
    hedge_check_interval_s: float = 0.7
    stale_order_seconds: float = 12.0
    inventory_cap_multiple: Decimal = Decimal("1.0")
    max_inventory_age_s: float = 120.0
    loss_cooldown_s: float = 4.0
    win_cooldown_s: float = 1.5
    neutral_cooldown_s: float = 2.0
    max_active_pairs: int = 2
    equity_fraction_per_pair: Decimal = Decimal("0.4")
    min_equity_allocation_usd: Decimal = Decimal("10")
    max_pair_loss_usd: Decimal = Decimal("6")
    max_total_loss_usd: Decimal = Decimal("20")


@dataclass
class ScalperConfig:
    """Top-level configuration container."""

    venue_keys: Dict[str, Dict[str, str]]
    pairs: Sequence[PairConfig] = field(default_factory=list)
    settings: EngineSettings = field(default_factory=EngineSettings)


def build_default_config(venue_keys: Dict[str, Dict[str, str]]) -> ScalperConfig:
    """Helper to produce a conservative default configuration."""

    default_pairs: List[PairConfig] = [
        PairConfig(exchange="coinbase", symbol="BTC/USD", base="BTC", quote="USD", target_edge_bps=18),
        PairConfig(exchange="coinbase", symbol="ETH/USD", base="ETH", quote="USD", target_edge_bps=20),
        PairConfig(exchange="gemini", symbol="BTC/USD", base="BTC", quote="USD", target_edge_bps=20, maker_fee_bps=15),
        PairConfig(exchange="gemini", symbol="ETH/USD", base="ETH", quote="USD", target_edge_bps=22, maker_fee_bps=18),
    ]
    return ScalperConfig(venue_keys=venue_keys, pairs=default_pairs)
