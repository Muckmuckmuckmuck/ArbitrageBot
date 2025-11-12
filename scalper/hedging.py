from __future__ import annotations

from decimal import Decimal


def compute_hedge_price(entry_price: Decimal, side: str, fee_guard_bps: int, buffer_bps: int = 0) -> Decimal:
    """Return a breakeven+fee hedge price for the opposite side."""

    total_bps = fee_guard_bps + buffer_bps
    cushion = Decimal(total_bps) / Decimal("10000")
    if side.lower() == "buy":
        return entry_price * (Decimal("1") + cushion)
    return entry_price * (Decimal("1") - cushion)
