from decimal import Decimal

import pytest

from scalper.edge_utils import estimate_slippage_bps
from scalper.config import EngineSettings


def test_estimate_slippage_bounds():
    settings = EngineSettings()
    # When order value exceeds available depth, slippage should cap at configured max.
    slippage_cap = estimate_slippage_bps(Decimal("100"), Decimal("10"), settings)
    assert slippage_cap == Decimal(settings.scanner_slippage_cap_bps)

    # When order value is tiny relative to depth, slippage approaches the floor.
    slippage_floor = estimate_slippage_bps(Decimal("0.1"), Decimal("1000"), settings)
    assert slippage_floor == pytest.approx(Decimal(settings.scanner_slippage_floor_bps), rel=Decimal("0.01"))

    # Intermediate values should lie between floor and cap.
    mid = estimate_slippage_bps(Decimal("5"), Decimal("100"), settings)
    assert Decimal(settings.scanner_slippage_floor_bps) <= mid <= Decimal(settings.scanner_slippage_cap_bps)
