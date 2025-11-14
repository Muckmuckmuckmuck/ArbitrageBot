from __future__ import annotations

from decimal import Decimal

from .config import EngineSettings


def estimate_slippage_bps(
    order_value_usd: Decimal,
    available_depth_usd: Decimal,
    settings: EngineSettings,
) -> Decimal:
    """Return estimated slippage in basis points for a proposed order value."""

    if order_value_usd <= 0 or available_depth_usd <= 0:
        return Decimal(settings.scanner_slippage_cap_bps)

    fill_ratio = order_value_usd / available_depth_usd
    if fill_ratio < Decimal("0"):
        fill_ratio = Decimal("0")
    elif fill_ratio > Decimal("1"):
        fill_ratio = Decimal("1")

    exponent = settings.scanner_slippage_impact_exponent
    try:
        impact = fill_ratio ** exponent
    except Exception:
        impact = fill_ratio

    floor = Decimal(settings.scanner_slippage_floor_bps)
    cap = Decimal(settings.scanner_slippage_cap_bps)
    slippage = floor + (cap - floor) * impact

    if slippage < floor:
        slippage = floor
    if slippage > cap:
        slippage = cap
    return slippage

