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
    order_size_usd: Decimal = Decimal("6")
    min_notional_usd: Decimal = Decimal("3")
    target_edge_bps: int = 100  # Increased from 80 to account for potential taker fees
    min_edge_bps: int = 80  # Increased from 60 to account for potential taker fees
    probe_edge_bps: int = 60  # Increased from 40 to account for potential taker fees
    max_edge_bps: int = 140
    slippage_buffer_bps: int = 8
    maker_fee_bps: int = 12
    taker_fee_bps: int = 35
    depth_clip_fraction: Decimal = Decimal("0.2")
    max_spread_bps: int = 400
    min_spread_bps: int = 10
    volatility_floor_bps: int = 30
    volatility_ceiling_bps: int = 400
    inventory_pressure_bps: int = 10
    base_probe_size_usd: Decimal = Decimal("3")
    max_probe_size_usd: Decimal = Decimal("9")
    probe_step_usd: Decimal = Decimal("1")
    probe_cooldown_s: float = 30.0


@dataclass
class EngineSettings:
    """Global controls for the scalper engine."""

    poll_interval_s: float = 0.4
    hedge_check_interval_s: float = 0.6
    stale_order_seconds: float = 10.0
    inventory_cap_multiple: Decimal = Decimal("0.9")
    max_inventory_age_s: float = 90.0
    loss_cooldown_s: float = 6.0
    win_cooldown_s: float = 1.8
    neutral_cooldown_s: float = 2.5
    loss_cooldown_threshold_usd: Decimal = Decimal("0.20")
    max_active_pairs: int = 2
    equity_fraction_per_pair: Decimal = Decimal("0.4")
    min_equity_allocation_usd: Decimal = Decimal("10")
    max_pair_loss_usd: Decimal = Decimal("6")
    max_total_loss_usd: Decimal = Decimal("20")
    hedge_fee_guard_bps: int = 35
    hedge_buffer_bps: int = 15
    hedge_balance_buffer_bps: int = 25
    hedge_stale_seconds: float = 30.0  # legacy alias for stage one
    hedge_stage_one_seconds: float = 30.0  # Increased from 10s - hedges need more time to fill
    hedge_stage_two_seconds: float = 60.0  # Increased from 18s - give hedges more time before forcing taker
    hedge_stage_partial_ratio: Decimal = Decimal("0.5")
    hedge_force_flat_seconds: float = 18.0
    fast_fill_latency_ms: float = 450.0
    fast_fill_clip_bps: int = 3
    slow_fill_clip_bps: int = 1
    minimum_target_edge_bps: int = 80  # Increased from 60 to account for potential taker fees
    scanner_interval_s: float = 45.0
    scanner_quote_currencies: Sequence[str] = field(default_factory=lambda: ["USD", "USDC", "USDT", "GUSD"])
    scanner_max_markets: int = 400
    scanner_depth_clip_fraction: Decimal = Decimal("0.2")
    negative_fill_lookback: int = 5
    insufficient_balance_cooldown_s: float = 6.0
    scanner_min_spread_bps: int = 40
    scanner_min_net_edge_bps: int = 100  # Increased from 80 to account for potential taker fees
    coinbase_min_net_edge_bps: int = 140  # Increased from 120 to account for potential taker fees
    scanner_min_depth_usd: Decimal = Decimal("25")
    scanner_min_volume_usd: Decimal = Decimal("2500")
    dynamic_order_usd_min: Decimal = Decimal("3")
    dynamic_order_usd_max: Decimal = Decimal("9")
    max_dynamic_pairs: int = 10
    scanner_max_depth_levels: int = 5
    scanner_slippage_floor_bps: int = 10
    scanner_slippage_cap_bps: int = 35
    scanner_slippage_impact_exponent: Decimal = Decimal("1.3")
    tier_premium_edge_bps: int = 40  # Increased from 30 to account for potential taker fees
    tier_standard_edge_bps: int = 25  # Increased from 18 to account for potential taker fees
    tier_probe_edge_bps: int = 15  # Increased from 10 to account for potential taker fees
    tier_premium_size_mult: Decimal = Decimal("1.0")
    tier_standard_size_mult: Decimal = Decimal("0.65")
    tier_probe_size_usd: Decimal = Decimal("3")
    tier_min_profit_bps: int = 10
    max_bid_improve_bps: int = 10
    max_sell_reduce_bps: int = 10


@dataclass
class ScalperConfig:
    """Top-level configuration container."""

    venue_keys: Dict[str, Dict[str, str]]
    pairs: Sequence[PairConfig] = field(default_factory=list)
    settings: EngineSettings = field(default_factory=EngineSettings)


def build_default_config(venue_keys: Dict[str, Dict[str, str]]) -> ScalperConfig:
    """Helper to produce a conservative default configuration."""

    default_pairs: List[PairConfig] = [
        PairConfig(exchange="coinbase", symbol="BTC/USD", base="BTC", quote="USD", target_edge_bps=110, min_edge_bps=90, probe_edge_bps=70, maker_fee_bps=40, taker_fee_bps=60),
        PairConfig(exchange="coinbase", symbol="ETH/USD", base="ETH", quote="USD", target_edge_bps=110, min_edge_bps=90, probe_edge_bps=70, maker_fee_bps=40, taker_fee_bps=60),
        PairConfig(exchange="gemini", symbol="BTC/USD", base="BTC", quote="USD", target_edge_bps=105, min_edge_bps=85, probe_edge_bps=65, maker_fee_bps=10, taker_fee_bps=35),
        PairConfig(exchange="gemini", symbol="ETH/USD", base="ETH", quote="USD", target_edge_bps=105, min_edge_bps=85, probe_edge_bps=65, maker_fee_bps=10, taker_fee_bps=40),
    ]
    return ScalperConfig(venue_keys=venue_keys, pairs=default_pairs)
