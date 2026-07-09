"""Tradeable universe, organized into risk-tiered sleeves.

Liquid US ETFs. The mid/safe sleeves are multi-asset ROTATION universes (equities +
bonds + gold + commodities) so a trend engine can move between assets and earn in
downturns without shorting. MTUM (momentum factor) and DBC (broad commodities) were
added for extra momentum juice and crisis diversification respectively.
"""
from __future__ import annotations

from typing import Dict, List

BENCHMARK = "SPY"
CASH_PROXY = "BIL"  # T-bill ETF, the risk-off bucket

SLEEVES: Dict[str, List[str]] = {
    # High growth: aggressive equity momentum (growth/tech + momentum factor).
    "high_growth": ["QQQ", "XLK", "SMH", "XLY", "XLC", "MTUM"],
    # Mid growth: broad global tactical rotation across asset classes.
    "mid_growth": ["SPY", "QQQ", "EFA", "IWM", "TLT", "IEF", "GLD", "DBC"],
    # Safe growth: conservative rotation — low-vol equity, gold, duration, commodities.
    "safe_growth": ["USMV", "GLD", "IEF", "TLT", "DBC", "SPY"],
}

# Default capital split (regime engine tilts this at runtime). Leans to growth.
SLEEVE_TARGET_WEIGHTS: Dict[str, float] = {
    "high_growth": 0.50,
    "mid_growth": 0.30,
    "safe_growth": 0.20,
}


def all_symbols() -> List[str]:
    syms = {BENCHMARK, CASH_PROXY}
    for members in SLEEVES.values():
        syms.update(members)
    return sorted(syms)


def sleeve_of(symbol: str) -> str:
    for name, members in SLEEVES.items():
        if symbol in members:
            return name
    return "unassigned"
