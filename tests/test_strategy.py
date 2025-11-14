from decimal import Decimal
import time

from scalper.config import PairConfig, EngineSettings
from scalper.market_data import OrderBookSnapshot
from scalper.state import PairRuntimeState
from scalper.strategy import QuotePlanner


def make_snapshot(bid_price: Decimal, ask_price: Decimal) -> OrderBookSnapshot:
    bids = (
        (bid_price, Decimal('0.8')),
        (bid_price - Decimal('0.5'), Decimal('1.2')),
    )
    asks = (
        (ask_price, Decimal('0.8')),
        (ask_price + Decimal('0.5'), Decimal('1.2')),
    )
    bid_value = sum(price * qty for price, qty in bids)
    ask_value = sum(price * qty for price, qty in asks)
    top_bid_value = bids[0][0] * bids[0][1]
    top_ask_value = asks[0][0] * asks[0][1]
    return OrderBookSnapshot(
        best_bid=bid_price,
        best_ask=ask_price,
        bids=bids,
        asks=asks,
        bid_value_usd=bid_value,
        ask_value_usd=ask_value,
        top_bid_value_usd=top_bid_value,
        top_ask_value_usd=top_ask_value,
        timestamp=time.time(),
    )


def test_quote_planner_selects_premium_tier():
    cfg = PairConfig(
        exchange='gemini',
        symbol='TEST/USD',
        base='TEST',
        quote='USD',
        order_size_usd=Decimal('50'),
        min_notional_usd=Decimal('5'),
    )
    settings = EngineSettings()
    planner = QuotePlanner()
    state = PairRuntimeState()

    snapshot = make_snapshot(Decimal('100'), Decimal('101'))
    intent = planner.plan(cfg, state, snapshot, stable_balance=Decimal('200'), settings=settings)

    assert intent is not None, 'Planner should produce quotes when edge is healthy'
    assert state.current_tier == 'premium'
    assert intent.order_value >= Decimal('20')
    assert intent.buy_price < snapshot.best_ask
    assert intent.sell_price > snapshot.best_bid


def test_quote_planner_probe_tier_when_edge_small():
    cfg = PairConfig(
        exchange='gemini',
        symbol='TEST/USD',
        base='TEST',
        quote='USD',
        order_size_usd=Decimal('20'),
        min_notional_usd=Decimal('1'),
    )
    settings = EngineSettings()
    planner = QuotePlanner()
    state = PairRuntimeState()

    # Spread wide enough for probe but below standard tier threshold.
    snapshot = make_snapshot(Decimal('100'), Decimal('100.5'))
    intent = planner.plan(cfg, state, snapshot, stable_balance=Decimal('200'), settings=settings)

    assert intent is not None
    assert state.current_tier == 'probe'
    assert intent.order_value <= settings.tier_probe_size_usd
