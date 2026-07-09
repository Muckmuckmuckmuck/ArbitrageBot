"""Unit tests for the rebalancer + SimBroker (pure logic, no network/broker)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quantbot.broker.base import Order  # noqa: E402
from quantbot.broker.sim import SimBroker  # noqa: E402
from quantbot.execution.rebalancer import compute_orders  # noqa: E402

PRICES = {"AAA": 100.0, "BBB": 50.0}


def test_buys_from_all_cash():
    target = pd.Series({"AAA": 0.5, "BBB": 0.5})
    orders = {o.symbol: o for o in compute_orders(target, 10_000, {}, PRICES, min_trade_usd=50)}
    assert orders["AAA"].side == "BUY" and orders["AAA"].shares == 50   # 5000/100
    assert orders["BBB"].shares == 100                                  # 5000/50


def test_no_trade_when_on_target():
    target = pd.Series({"AAA": 0.5})
    assert compute_orders(target, 10_000, {"AAA": 50.0}, PRICES, min_trade_usd=50) == []


def test_sell_down_to_zero():
    target = pd.Series({"AAA": 0.0})
    orders = compute_orders(target, 10_000, {"AAA": 50.0}, PRICES, min_trade_usd=50)
    assert len(orders) == 1 and orders[0].side == "SELL" and orders[0].shares == 50


def test_never_sells_more_than_held():
    target = pd.Series({"AAA": 0.0})
    orders = compute_orders(target, 10_000, {"AAA": 3.0}, PRICES, min_trade_usd=50)
    assert orders[0].shares == 3


def test_single_position_cap_applied():
    target = pd.Series({"AAA": 0.9})
    orders = compute_orders(target, 10_000, {}, PRICES, min_trade_usd=50, max_single_position_pct=0.20)
    assert orders[0].shares == 20   # capped 20% -> 2000/100


def test_sim_broker_roundtrip_costs():
    b = SimBroker(10_000, PRICES)
    b.submit(Order("AAA", "BUY", 50, 100, 5000))
    assert abs(b.positions()["AAA"] - 50) < 1e-9
    nlv = b.net_liquidation()
    assert 9_900 < nlv < 10_000   # lost only commission + slippage on the marked position
