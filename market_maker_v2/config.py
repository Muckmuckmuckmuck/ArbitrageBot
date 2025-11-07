from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(slots=True)
class PairConfig:
    """Per-trading-pair configuration."""

    symbol: str
    max_position_usd: Decimal = Decimal("25.0")
    min_order_usd: Decimal = Decimal("1.0")
    base_spread_bps: Decimal = Decimal("25")  # expressed in basis points
    min_spread_bps: Decimal = Decimal("18")
    max_spread_bps: Decimal = Decimal("120")
    order_refresh_seconds: int = 20
    order_expiry_seconds: int = 45


@dataclass(slots=True)
class RiskConfig:
    """Risk guardrails."""

    daily_loss_limit_pct: Decimal = Decimal("0.05")
    per_trade_loss_limit_pct: Decimal = Decimal("0.03")
    max_inventory_imbalance_pct: Decimal = Decimal("0.20")
    soft_inventory_imbalance_pct: Decimal = Decimal("0.12")
    volatility_pause_threshold_pct: Decimal = Decimal("0.035")
    volatility_resume_threshold_pct: Decimal = Decimal("0.02")


@dataclass(slots=True)
class StrategyToggles:
    """Feature toggles to simplify experimentation."""

    enable_inventory_skew: bool = True
    enable_post_only: bool = True
    enable_rebate_tracking: bool = True
    simulate_mode: bool = False  # live trading by default; enable for paper mode when needed


@dataclass(slots=True)
class ExchangeRuntimeConfig:
    """Runtime exchange settings."""

    name: str
    ccxt_id: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    rate_limit_private_rps: float = 10.0
    rate_limit_public_rps: float = 5.0
    min_order_usd: Decimal = Decimal("1.0")
    maker_fee_bps: Decimal = Decimal("0")  # basis points
    taker_fee_bps: Decimal = Decimal("40")  # basis points
    markets: List[PairConfig] = field(default_factory=list)

    def is_live_trading_enabled(self) -> bool:
        return self.api_key is not None and self.api_secret is not None


@dataclass(slots=True)
class PathsConfig:
    """Filesystem locations."""

    base_dir: Path = Path(".").resolve()
    db_path: Path = Path("state/market_maker_v2.sqlite3")
    log_path: Path = Path("logs/market_maker_v2.log")

    def ensure_directories(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class LoggingConfig:
    log_level: str = "INFO"
    metrics_interval_seconds: int = 10
    alert_webhook_url: Optional[str] = None


@dataclass(slots=True)
class BotConfig:
    """Top-level configuration consumed by the bot."""

    starting_capital_usd: Decimal = Decimal("40.0")
    capital_per_exchange: Dict[str, Decimal] = field(
        default_factory=lambda: {"coinbase": Decimal("25.0"), "gemini": Decimal("15.0")}
    )
    exchanges: Dict[str, ExchangeRuntimeConfig] = field(default_factory=dict)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyToggles = field(default_factory=StrategyToggles)
    paths: PathsConfig = field(default_factory=PathsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def get_exchange(self, name: str) -> ExchangeRuntimeConfig:
        try:
            return self.exchanges[name]
        except KeyError as exc:
            raise KeyError(f"Exchange '{name}' not configured") from exc

    @classmethod
    def default(cls) -> "BotConfig":
        """Bootstrap default configuration using environment variables where possible."""
        coinbase = ExchangeRuntimeConfig(
            name="coinbase",
            ccxt_id="coinbaseadvanced",
            api_key=os.getenv("COINBASE_API_KEY"),
            api_secret=os.getenv("COINBASE_API_SECRET"),
            passphrase=os.getenv("COINBASE_API_PASSPHRASE"),
            rate_limit_private_rps=10,
            rate_limit_public_rps=5,
            min_order_usd=Decimal("1.0"),
            maker_fee_bps=Decimal("0"),
            taker_fee_bps=Decimal("40"),
            markets=[
                PairConfig(symbol="BTC-USD", base_spread_bps=Decimal("22")),
                PairConfig(symbol="ETH-USD", base_spread_bps=Decimal("26"), min_order_usd=Decimal("2.0")),
            ],
        )

        gemini = ExchangeRuntimeConfig(
            name="gemini",
            ccxt_id="gemini",
            api_key=os.getenv("GEMINI_API_KEY"),
            api_secret=os.getenv("GEMINI_API_SECRET"),
            rate_limit_private_rps=8,
            rate_limit_public_rps=2,
            min_order_usd=Decimal("5.0"),
            maker_fee_bps=Decimal("-10"),  # rebate
            taker_fee_bps=Decimal("35"),
            markets=[
                PairConfig(symbol="BTC/USD", base_spread_bps=Decimal("28"), min_order_usd=Decimal("5.0")),
            ],
        )

        cfg = cls(
            exchanges={
                coinbase.name: coinbase,
                gemini.name: gemini,
            }
        )
        cfg.paths.ensure_directories()
        return cfg

