"""Central configuration for the IBKR multi-strategy paper-trading system.

Dependency-light on purpose (dataclasses + os.environ). Risk limits are HARD caps:
nothing downstream (strategy, allocator, or Claude-proposed change) may raise them
at runtime. Live trading is a deliberate opt-in behind PAPER-by-default.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"


class Mode(str, Enum):
    PAPER = "PAPER"  # IBKR paper account (default, safe)
    LIVE = "LIVE"    # real money — requires explicit opt-in + a live account


def _f(key: str, default: float) -> float:
    return float(os.getenv(key, default))


def _i(key: str, default: int) -> int:
    return int(os.getenv(key, default))


@dataclass(frozen=True)
class RiskLimits:
    """Hard risk caps. The allocator sizes to the *binding* constraint — a lesson
    carried from the predecessor bot (which once used max() of constraints, not min())."""
    max_single_position_pct: float = field(default_factory=lambda: _f("RISK_MAX_SINGLE_POSITION_PCT", 0.20))
    max_sleeve_pct: float = field(default_factory=lambda: _f("RISK_MAX_SLEEVE_PCT", 0.60))
    max_gross_exposure_pct: float = field(default_factory=lambda: _f("RISK_MAX_GROSS_EXPOSURE_PCT", 1.00))
    max_daily_loss_pct: float = field(default_factory=lambda: _f("RISK_MAX_DAILY_LOSS_PCT", 0.03))
    max_drawdown_pct: float = field(default_factory=lambda: _f("RISK_MAX_DRAWDOWN_PCT", 0.20))


@dataclass(frozen=True)
class IBKRConfig:
    """Connection to IB Gateway / TWS. Ports: 7497 paper-TWS, 4002 paper-Gateway,
    7496 live-TWS, 4001 live-Gateway."""
    host: str = field(default_factory=lambda: os.getenv("IBKR_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _i("IBKR_PORT", 4002))  # paper gateway
    client_id: int = field(default_factory=lambda: _i("IBKR_CLIENT_ID", 1))
    account: Optional[str] = field(default_factory=lambda: os.getenv("IBKR_ACCOUNT") or None)
    readonly: bool = field(default_factory=lambda: os.getenv("IBKR_READONLY", "false").lower() == "true")


@dataclass(frozen=True)
class DataConfig:
    provider: str = field(default_factory=lambda: os.getenv("DATA_PROVIDER", "yfinance"))  # yfinance|stooq
    start: str = field(default_factory=lambda: os.getenv("DATA_START", "2010-01-01"))
    cache_dir: Path = CACHE_DIR


@dataclass(frozen=True)
class BacktestConfig:
    cost_bps: float = field(default_factory=lambda: _f("BT_COST_BPS", 5.0))     # round-turn slippage+commission
    cash_annual_rate: float = field(default_factory=lambda: _f("BT_CASH_RATE", 0.04))  # T-bill on idle cash


@dataclass(frozen=True)
class Settings:
    mode: Mode = field(default_factory=lambda: Mode(os.getenv("QUANTBOT_MODE", "PAPER").upper()))
    starting_equity_usd: float = field(default_factory=lambda: _f("STARTING_EQUITY_USD", 100_000.0))
    ibkr: IBKRConfig = field(default_factory=IBKRConfig)
    data: DataConfig = field(default_factory=DataConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    risk: RiskLimits = field(default_factory=RiskLimits)

    def require_live_ready(self) -> None:
        if self.mode is Mode.LIVE and (self.ibkr.port in (4002, 7497)):
            raise RuntimeError(
                "QUANTBOT_MODE=LIVE but IBKR_PORT is a paper port. Refusing to start. "
                "Point at a live port (4001/7496) intentionally, or switch to PAPER."
            )


settings = Settings()
