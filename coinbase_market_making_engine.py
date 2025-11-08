#!/usr/bin/env python3
"""
Coinbase Market Making Engine
Implements passive market-making strategy on Coinbase exchange
Top pairs optimized for maximum profitability with dynamic adjustments

EXCHANGE: 🔵 COINBASE ONLY - This entire module is for Coinbase market making
"""

import asyncio
import logging
import random
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Core bases we want to quote on Coinbase (high-liquidity assets)
TOP_COINBASE_BASES = [
    'BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'UNI', 'DOGE', 'XRP',
    'ADA', 'DOT', 'MATIC', 'ATOM', 'ALGO', 'LTC', 'AAVE'
]

# Prioritize both USD and USDC quotes so we can trade when cash is held in either
TOP_COINBASE_QUOTES = ['USD', 'USDC']

# Generate the default pair universe (duplicates removed downstream during initialization)
TOP_COINBASE_PAIRS = [
    f"{base}/{quote}"
    for base in TOP_COINBASE_BASES
    for quote in TOP_COINBASE_QUOTES
]

@dataclass
class MarketMakingOrder:
    """Represents a market-making order"""
    pair: str
    side: str  # 'buy' or 'sell'
    order_id: Optional[str] = None
    price: float = 0.0
    amount: float = 0.0
    status: str = 'pending'  # 'pending', 'open', 'filled', 'canceled'
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    filled_amount: float = 0.0  # Track partial fills - amount that has been filled so far
    fees_paid: float = 0.0

@dataclass
class MarketMakingStats:
    """Statistics for market-making performance"""
    pair: str
    total_orders: int = 0
    filled_orders: int = 0
    total_profit_usd: float = 0.0
    total_fees_usd: float = 0.0
    net_profit_usd: float = 0.0
    avg_spread_captured: float = 0.0
    win_rate: float = 0.0
    wins: int = 0
    losses: int = 0

class CoinbaseMarketMakingEngine:
    """Market-making engine for Coinbase exchange"""
    
    def __init__(
        self,
        exchange_manager: CoinbaseGeminiExchangeManager,
        capital_per_pair: float = 75.0,  # $75 per pair to support larger quotes
        grid_spacing_percent: float = 0.20,  # 0.20% spacing
        order_size_percent: float = 0.12,  # 12% of capital per order (~$9)
        min_spread_percent: float = 0.95,  # Skip if effective spread < 0.95% (covers maker fees + buffer)
        max_inventory_percent: float = 0.25,  # Max 25% in one asset
        requote_interval_seconds: int = 15,  # Update orders every 15s
        stop_loss_percent: float = 0.02,  # -2% stop loss
        take_profit_interval_minutes: int = 60,  # Flatten every hour
        max_volatility_percent: float = 2.0,  # Skip if short-term volatility above this
        min_depth_usd: float = 500.0,  # Require at least this much depth on both sides
    ):
        self.exchange_manager = exchange_manager
        self.capital_per_pair = capital_per_pair
        self.grid_spacing_percent = grid_spacing_percent
        self.order_size_percent = order_size_percent
        self.maker_fee_percent = 0.35  # Estimated maker fee in percent
        self.taker_fee_percent = 0.35  # Estimated taker fee (fallback / crosses)
        self.min_order_value_usd = 5.00
        self.min_inventory_sell_value_usd = 5.00
        self.balance_buffer_multiplier = 1.05
        self.min_profit_buffer_percent = 0.25  # Additional cushion beyond fees
        self.min_spread_percent = max(
            min_spread_percent,
            self.maker_fee_percent + self.taker_fee_percent + self.min_profit_buffer_percent
        )
        self.max_inventory_percent = max_inventory_percent
        self.requote_interval_seconds = requote_interval_seconds
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_interval_minutes = take_profit_interval_minutes
        self.min_spacing_percent = 0.50  # Minimum spacing to ensure profitability (percent)
        self.max_spacing_percent = 1.50  # Cap spacing to avoid quoting too far away
        self.min_volume_usd = 150000.0
        self.max_volatility_percent = max_volatility_percent
        self.min_depth_usd = max(min_depth_usd, 7500.0)
        self.min_fill_rate_threshold = 0.12
        self.fill_rate_blacklist_minutes = 10
        self.max_pair_loss_usd = -8.0
        self.max_global_loss_usd = -25.0
        self.inside_quote_volume_threshold = 1200.0
        self.inside_quote_improve_bps = 2.0  # 0.02%
        self.micro_reprice_threshold = 0.12  # 0.12% drift triggers reprice
        self.inventory_max_age_minutes = 75

        # Active orders tracking
        self.active_orders: Dict[str, List[MarketMakingOrder]] = defaultdict(list)
        
        # Statistics
        self.stats: Dict[str, MarketMakingStats] = {}
        self.available_pairs: List[str] = []  # Will be set during initialization
        
        # 🔵 IMPROVEMENT: Track fill rates for pairs (focus on pairs that actually fill)
        self.pair_fill_rates: Dict[str, float] = {}  # pair -> fill_rate (0-1)
        self.last_buy_prices: Dict[str, float] = defaultdict(lambda: 0.0)
        self.pending_sell_queue: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # 🔵 IMPROVEMENT: Dynamic adjustment tracking
        self.pair_performance: Dict[str, Dict] = defaultdict(lambda: {
            'total_profit': 0.0,
            'total_trades': 0,
            'avg_spread': 0.0,
            'fill_rate': 0.5
        })
        self.pair_spread_overrides: Dict[str, float] = {}
        self.pair_skip_until: Dict[str, datetime] = {}
        self.pair_last_inventory_timestamp: Dict[str, datetime] = {}
        self.pair_failure_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.pair_cooldown_multipliers: Dict[str, int] = defaultdict(lambda: 1)
        self.pair_cooldowns: Dict[str, Tuple[datetime, str]] = {}
        self.failure_threshold = 3
        self.failure_cooldown_minutes = 5
        
        # Running state
        self.running = False
        self.last_flatten_time = datetime.now()
        self.net_profit_usd: float = 0.0
        self.total_fees_usd: float = 0.0
        self.position_tracker: Dict[str, List[Dict[str, float]]] = defaultdict(list)
        self.global_loss_pause_until: Optional[datetime] = None
        
    def _reset_failures(self, pair: str):
        if pair in self.pair_failure_counts:
            self.pair_failure_counts[pair].clear()
        if pair in self.pair_cooldowns and self.pair_cooldowns[pair][0] <= datetime.now():
            self.pair_cooldowns.pop(pair, None)
        if pair in self.pair_cooldown_multipliers:
            self.pair_cooldown_multipliers[pair] = 1

    def _register_failure(self, pair: str, failure_type: str, detail: str):
        counts = self.pair_failure_counts[pair]
        counts[failure_type] += 1
        logger.debug(f"   🔵 [COINBASE] {pair}: Failure '{failure_type}' count -> {counts[failure_type]} ({detail})")
        if counts[failure_type] >= self.failure_threshold:
            multiplier = min(4, self.pair_cooldown_multipliers[pair] + 1)
            self.pair_cooldown_multipliers[pair] = multiplier
            cooldown_minutes = self.failure_cooldown_minutes * multiplier
            cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
            self.pair_cooldowns[pair] = (cooldown_until, failure_type)
            counts[failure_type] = 0
            logger.warning(
                f"   🔵 [COINBASE] ⏸️ Cooling down {pair} for {cooldown_minutes}m after repeated '{failure_type}' failures ({detail})"
            )

    def _is_on_cooldown(self, pair: str) -> Optional[Tuple[datetime, str]]:
        cooldown_entry = self.pair_cooldowns.get(pair)
        if not cooldown_entry:
            return None
        cooldown_until, reason = cooldown_entry
        if cooldown_until <= datetime.now():
            self.pair_cooldowns.pop(pair, None)
            return None
        return cooldown_entry

    async def discover_suitable_pairs(
        self,
        min_volume_usd: Optional[float] = None,
        max_pairs: int = 50,  # Top 50 pairs
    ) -> List[Tuple[str, float, float, float]]:
        """
        Dynamically discover all suitable pairs for market making
        Returns: List of (pair, volume_24h, spread, score) tuples, sorted by score
        """
        logger.info("   🔵 [COINBASE] 🔍 DISCOVERING SUITABLE PAIRS...")
        exchange = self.exchange_manager.get_exchange('coinbase')
        suitable_pairs = []
        volume_threshold = max(self.min_volume_usd, min_volume_usd if min_volume_usd is not None else self.min_volume_usd)
        base_order_budget = self.capital_per_pair * self.order_size_percent
        
        # Scan all markets
        for symbol, market_info in exchange.markets.items():
            try:
                # Filter: Active spot markets only, USD/USDC/USDT quote
                if not market_info.get('active', True):
                    continue
                if market_info.get('future', False) or market_info.get('swap', False):
                    continue
                if ':' in symbol:  # Skip futures contracts
                    continue
                
                quote = market_info.get('quote', '').strip().upper()
                if quote not in ['USD', 'USDC', 'USDT']:
                    continue
                
                # Get ticker data (volume, spread)
                try:
                    ticker = await self.exchange_manager.fetch_ticker('coinbase', symbol)
                    
                    # Get volume
                    volume_24h = ticker.get('quoteVolume') or ticker.get('quote_volume')
                    if not volume_24h:
                        base_volume = ticker.get('volume') or ticker.get('baseVolume')
                        last_price = ticker.get('last') or ticker.get('close')
                        if base_volume and last_price:
                            volume_24h = base_volume * last_price
                    else:
                        last_price = ticker.get('last') or ticker.get('close')
                    
                    if not volume_24h or volume_24h < volume_threshold:
                        continue
                    if not last_price or last_price <= 0:
                        continue
                    
                    limits = market_info.get('limits', {})
                    min_cost = limits.get('cost', {}).get('min', 0) or 0
                    min_amount = limits.get('amount', {}).get('min', 0) or 0
                    est_order_value = base_order_budget
                    est_order_amount = est_order_value / last_price
                    if min_cost and est_order_value < min_cost * 1.1:
                        logger.debug(f"   🔵 [COINBASE] Skipping {symbol} - min order cost ${min_cost:.2f} > target order value ${est_order_value:.2f}")
                        continue
                    if min_amount and est_order_amount < min_amount * 1.1:
                        logger.debug(f"   🔵 [COINBASE] Skipping {symbol} - min order amount {min_amount:.6f} > target amount {est_order_amount:.6f}")
                        continue
                    
                    # Get spread
                    bid = ticker.get('bid', 0) or 0
                    ask = ticker.get('ask', 0) or 0
                    if bid <= 0 or ask <= 0:
                        continue
                    
                    mid = (bid + ask) / 2
                    if mid <= 0:
                        continue
                    
                    spread = ((ask - bid) / mid) * 100
                    if spread < self.min_spread_percent:
                        continue
                    
                    # Calculate suitability score
                    # Higher volume = better, wider spread = better (up to a point)
                    volume_score = min(volume_24h / 5000000.0, 1.0)  # Normalize to $5M
                    spread_score = min(spread / 2.0, 1.0)  # Normalize to 2% spread
                    score = (volume_score * 0.6) + (spread_score * 0.4)  # 60% volume, 40% spread
                    
                    suitable_pairs.append((symbol, volume_24h, spread, score))
                    
                except Exception as e:
                    logger.debug(f"   🔵 [COINBASE] Error analyzing {symbol}: {e}")
                    continue
                    
            except Exception as e:
                logger.debug(f"   🔵 [COINBASE] Error processing {symbol}: {e}")
                continue
        
        # Sort by score (best first)
        suitable_pairs.sort(key=lambda x: x[3], reverse=True)
        
        # Return top N pairs
        top_pairs = suitable_pairs[:max_pairs]
        logger.info(f"   🔵 [COINBASE] Found {len(suitable_pairs)} suitable pairs, selecting top {len(top_pairs)}")
        
        return top_pairs
    
    async def initialize(self):
        """Initialize the market-making engine"""
        logger.info("=" * 80)
        logger.info("🚀 INITIALIZING COINBASE MARKET-MAKING ENGINE")
        logger.info("=" * 80)
        logger.info(f"   Capital per pair: ${self.capital_per_pair:.2f}")
        logger.info(f"   Grid spacing: {self.grid_spacing_percent:.2f}%")
        logger.info(f"   Order size: {self.order_size_percent*100:.1f}% of capital")
        logger.info(f"   Min spread: {self.min_spread_percent:.2f}%")
        logger.info("=" * 80)
        
        # 🔵 DYNAMIC: Discover all suitable pairs
        discovered_pairs = await self.discover_suitable_pairs(
            min_volume_usd=self.min_volume_usd,
            max_pairs=50  # Top 50 pairs
        )
        
        # Combine with hardcoded top pairs (prioritize them)
        exchange = self.exchange_manager.get_exchange('coinbase')
        available_pairs = []
        pair_set = set()
        
        # First, add hardcoded top pairs if they exist
        for pair in TOP_COINBASE_PAIRS:
            if pair in exchange.markets:
                market_info = exchange.markets[pair]
                if market_info.get('active', True) and not market_info.get('future', False) and ':' not in pair:
                    available_pairs.append(pair)
                    pair_set.add(pair)
                    logger.info(f"   ✅ Top pair: {pair}")
        
        # Then add discovered pairs (avoid duplicates)
        for pair, volume, spread, score in discovered_pairs:
            if pair not in pair_set:
                available_pairs.append(pair)
                pair_set.add(pair)
                logger.info(f"   ✅ Discovered: {pair} | Volume: ${volume:,.0f} | Spread: {spread:.3f}% | Score: {score:.3f}")
        
        self.available_pairs = available_pairs
        
        # Initialize stats for available pairs only
        self.stats = {}
        for pair in available_pairs:
            self.stats[pair] = MarketMakingStats(pair=pair)
            self.pair_fill_rates[pair] = 0.5  # Default neutral fill rate
            self.pair_performance[pair] = {
                'total_profit': 0.0,
                'total_trades': 0,
                'avg_spread': 0.0,
                'fill_rate': 0.5,
            }
        
        logger.info(f"   ✅ Total available pairs: {len(available_pairs)}")
        if len(available_pairs) == 0:
            logger.error(f"   ❌ No pairs available on Coinbase! Market making will not work.")
        logger.info("=" * 80)
        
    async def get_current_price(self, pair: str) -> Optional[float]:
        """Get current market price for a pair"""
        try:
            ticker = await self.exchange_manager.fetch_ticker('coinbase', pair)
            bid = ticker.get('bid', 0) or 0
            ask = ticker.get('ask', 0) or 0
            
            # Calculate mid price
            if bid > 0 and ask > 0:
                mid_price = (bid + ask) / 2
                if mid_price > 0:
                    return mid_price
            
            # Fallback to last price
            last_price = ticker.get('last') or ticker.get('close') or 0
            if last_price > 0:
                return last_price
            
            return None
        except Exception as e:
            logger.debug(f"   🔵 [COINBASE] Error fetching price for {pair}: {e}")
            return None
    
    async def get_spread(self, pair: str) -> Optional[float]:
        """Get current spread percentage"""
        try:
            ticker = await self.exchange_manager.fetch_ticker('coinbase', pair)
            bid = ticker.get('bid', 0) or 0
            ask = ticker.get('ask', 0) or 0
            if bid > 0 and ask > 0:
                mid = (bid + ask) / 2
                if mid > 0:
                    spread = ((ask - bid) / mid) * 100
                    last_spread, last_mid = getattr(self, '_last_spreads', {}).get(pair, (spread, mid))
                    if spread > 0 and last_mid > 0:
                        spread_change = abs(spread - last_spread)
                        if spread_change > 0.15:
                            self.pair_anomaly_counters[pair]['spread_jump'] += 1
                    if not hasattr(self, '_last_spreads'):
                        self._last_spreads = {}
                    self._last_spreads[pair] = (spread, mid)
                    return spread
            return None
        except Exception as e:
            logger.debug(f"   🔵 [COINBASE] Error fetching spread for {pair}: {e}")
            return None

    async def _compute_short_term_volatility(self, pair: str, limit: int = 20) -> Optional[float]:
        """Calculate percentage volatility from recent 1-minute candles."""
        try:
            ohlcv = await self.exchange_manager.fetch_ohlcv('coinbase', pair, timeframe='1m', limit=limit)
            closes = [candle[4] for candle in ohlcv if candle and candle[4]]
            if len(closes) < 5:
                return None
            returns = []
            for i in range(1, len(closes)):
                prev = closes[i - 1]
                curr = closes[i]
                if prev and prev > 0 and curr:
                    returns.append((curr / prev - 1) * 100)
            if len(returns) < 4:
                return None
            volatility = statistics.pstdev(returns)
            return abs(volatility)
        except Exception as e:
            logger.debug(f"   🔵 [COINBASE] Unable to compute volatility for {pair}: {e}")
            return None

    async def _compute_order_book_depth(self, pair: str, depth_levels: int = 5) -> Optional[float]:
        """Approximate USD depth using top-of-book levels."""
        try:
            order_book = await self.exchange_manager.fetch_order_book('coinbase', pair, limit=depth_levels)
            bids = order_book.get('bids', []) or []
            asks = order_book.get('asks', []) or []
            if not bids or not asks:
                return None
            bid_depth = sum(price * amount for price, amount in bids[:depth_levels])
            ask_depth = sum(price * amount for price, amount in asks[:depth_levels])
            return min(bid_depth, ask_depth)
        except Exception as e:
            logger.debug(f"   🔵 [COINBASE] Unable to compute order book depth for {pair}: {e}")
            return None

    async def _evaluate_market_health(self, pair: str) -> Tuple[bool, Dict[str, Optional[float]], str]:
        metrics: Dict[str, Optional[float]] = {'volatility': None, 'depth_usd': None}
        volatility = await self._compute_short_term_volatility(pair)
        if volatility is not None:
            metrics['volatility'] = volatility
            if volatility > self.max_volatility_percent:
                return False, metrics, f"volatility {volatility:.2f}% > max {self.max_volatility_percent:.2f}%"

        depth_usd = await self._compute_order_book_depth(pair)
        if depth_usd is not None:
            metrics['depth_usd'] = depth_usd
            if depth_usd < self.min_depth_usd:
                return False, metrics, f"depth ${depth_usd:.0f} < minimum ${self.min_depth_usd:.0f}"

        return True, metrics, "market healthy"

    def _compute_required_spread(
        self,
        pair: str,
        market_metrics: Dict[str, Optional[float]],
        fill_rate: float
    ) -> float:
        base_requirement = (
            self.maker_fee_percent
            + self.taker_fee_percent
            + self.min_profit_buffer_percent
        )

        volatility = market_metrics.get('volatility') or 0.0
        volatility_component = min(volatility * 0.4, 1.0)

        fill_component = 0.0
        if fill_rate < 0.3:
            fill_component = (0.3 - fill_rate) * 0.6  # encourage better edge when fills are scarce

        override = self.pair_spread_overrides.get(pair)

        required = base_requirement + volatility_component + fill_component
        if override is not None:
            required = max(required, override)

        return max(self.min_spread_percent, required)
    
    async def get_inventory_balance(self, base_currency: str) -> float:
        """Get current inventory balance for a base currency"""
        try:
            balance = await self.exchange_manager.fetch_balance('coinbase')
            free_balance = balance.get('free', {})
            return free_balance.get(base_currency, 0)
        except Exception as e:
            logger.debug(f"   Error fetching balance: {e}")
            return 0.0
    
    def _get_min_profitable_sell_price(
        self,
        pair: str,
        fallback_buy_price: Optional[float] = None,
        include_buffer: bool = True,
    ) -> Optional[float]:
        """
        Calculate the minimum price that preserves a positive net PnL after fees.
        Uses tracked inventory lots when available, otherwise falls back to provided price.
        """
        lots = self.position_tracker.get(pair, [])
        total_amount = sum(lot.get('amount', 0.0) for lot in lots)
        total_cost = sum(lot.get('cost', 0.0) + lot.get('fees', 0.0) for lot in lots)

        used_fallback = False

        if total_amount > 1e-12 and total_cost > 0:
            avg_cost = total_cost / total_amount
        elif fallback_buy_price:
            avg_cost = fallback_buy_price
            total_amount = 1.0  # Normalise to avoid division by zero
            used_fallback = True
        else:
            return None

        if used_fallback:
            avg_cost *= (1 + self.maker_fee_percent / 100.0)

        sell_fee_factor = 1.0 - (self.maker_fee_percent / 100.0)
        if sell_fee_factor <= 0:
            sell_fee_factor = 0.999  # Safety to avoid division by zero

        breakeven_price = avg_cost / sell_fee_factor

        if include_buffer:
            breakeven_price *= (1 + self.min_profit_buffer_percent / 100.0)

        return breakeven_price

    async def sell_all_inventory(self):
        """Check ALL inventory and place sell orders for any crypto we have"""
        try:
            balance = await self.exchange_manager.fetch_balance('coinbase')
            free_balance = balance.get('free', {})
            exchange = self.exchange_manager.get_exchange('coinbase')
            logger.info("   🔵 [COINBASE] 🔁 Checking account inventory for outstanding positions...")
            
            # Check all currencies (not just trading pairs)
            tradable_found = False
            for currency, amount in free_balance.items():
                # Skip quote currencies (cash)
                if currency in ['USD', 'USDT', 'USDC', 'GUSD'] or amount <= 0:
                    continue
                tradable_found = True
                
                # Try to find a trading pair for this currency
                for quote in ['USD', 'USDC', 'USDT']:
                    pair = f"{currency}/{quote}"
                    if pair in exchange.markets:
                        market_info = exchange.markets[pair]
                        if not market_info.get('active', True):
                            continue
                        
                        # Get current price
                        ticker = await self.exchange_manager.fetch_ticker('coinbase', pair)
                        if not ticker:
                            continue
                        
                        bid = ticker.get('bid', 0) or 0
                        ask = ticker.get('ask', 0) or 0
                        if bid <= 0 or ask <= 0:
                            continue
                        
                        # Check if we already have an open sell order for this pair
                        existing_orders = self.active_orders.get(pair, [])
                        open_sell_orders = [o for o in existing_orders if o.side == 'sell' and o.status == 'open']
                        if open_sell_orders:
                            logger.info(
                                f"   🔵 [COINBASE] {pair}: Existing sell order already open (count={len(open_sell_orders)}), skipping forced sell"
                            )
                            break
                        
                        # Calculate sell amount (use all available inventory)
                        sell_amount = amount

                        last_buy_price = self.last_buy_prices.get(pair)
                        min_profitable_price = self._get_min_profitable_sell_price(
                            pair,
                            fallback_buy_price=last_buy_price or ask
                        )
                        baseline_price = bid * 0.999
                        buffer_price = ask * (1 + max(self.min_profit_buffer_percent / 100.0, 0.001))
                        if min_profitable_price:
                            sell_price = max(min_profitable_price, baseline_price)
                        else:
                            sell_price = baseline_price
                        
                        # Get market limits
                        limits = market_info.get('limits', {})
                        min_cost = limits.get('cost', {}).get('min', 1.0) or 1.0
                        
                        # Check minimum order size
                        order_value = sell_amount * bid
                        if order_value < min_cost:
                            logger.info(
                                f"   🔵 [COINBASE] {pair}: Inventory value ${order_value:.2f} below minimum ${min_cost:.2f}, keeping position"
                            )
                            break
                        
                        # Place sell order
                        try:
                            self.pair_last_inventory_timestamp[pair] = datetime.now()
                            logger.info(
                                f"   🔵 [COINBASE] 💰 SELLING INVENTORY: {pair} - {sell_amount:.6f} {currency} "
                                f"via market ~${sell_price:.6f} (bid ${bid:.6f}) => ${order_value:.2f}"
                            )
                            sell_order = await self.exchange_manager.create_order(
                                exchange_id='coinbase',
                                symbol=pair,
                                order_type='market',
                                side='sell',
                                amount=sell_amount
                            )
                            
                            if sell_order:
                                sell_status = str(sell_order.get('status', '')).lower()
                                sell_price_used = sell_order.get('price') or sell_price
                                sell_order_id = sell_order.get('id')
                                if sell_status in ('closed', 'filled', 'done'):
                                    logger.info(
                                        f"   🔵 [COINBASE] ✅ INVENTORY FLATTENED: {pair} filled immediately @ ${float(sell_price_used):.6f}"
                                    )
                                elif sell_order_id:
                                    sell_mm_order = MarketMakingOrder(
                                        pair=pair,
                                        side='sell',
                                        order_id=sell_order_id,
                                        price=float(sell_price_used),
                                        amount=sell_amount,
                                        status='open'
                                    )
                                    self.active_orders[pair].append(sell_mm_order)
                                    logger.info(
                                        f"   🔵 [COINBASE] ✅ INVENTORY SELL ORDER LIVE: {pair} "
                                        f"@ ${float(sell_price_used):.6f} for {sell_amount:.6f} | Order ID: {sell_order_id}"
                                    )
                        except Exception as e:
                            logger.error(f"   🔵 [COINBASE] ❌ Failed to sell inventory {pair}: {type(e).__name__}: {e}")
                        
                        break  # Found a working pair, move to next currency
            if not tradable_found:
                logger.info("   🔵 [COINBASE] No non-cash balances detected for forced selling.")
        except Exception as e:
            logger.error(f"   🔵 [COINBASE] ❌ Error selling all inventory: {type(e).__name__}: {e}")
    
    async def place_market_making_orders(self, pair: str) -> dict:
        """Place buy and sell limit orders for market making"""
        orders_placed = 0
        orders_filled = 0
        
        try:
            cooldown_entry = self._is_on_cooldown(pair)
            if cooldown_entry:
                cooldown_until, reason = cooldown_entry
                remaining = max((cooldown_until - datetime.now()).total_seconds(), 0)
                logger.info(
                    f"   🔵 [COINBASE] ⏭️ Skipping {pair} - on cooldown for {remaining:.0f}s (reason: {reason})"
                )
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'cooldown'}

            logger.info(f"   🔵 [COINBASE] 🔍 PROCESSING {pair}...")

            now = datetime.now()
            allow_new_buys = True

            if self.net_profit_usd <= self.max_global_loss_usd:
                if not self.global_loss_pause_until or self.global_loss_pause_until <= now:
                    self.global_loss_pause_until = now + timedelta(minutes=5)
                    logger.warning(
                        f"   🔵 [COINBASE] ⛔ Pausing new buys for 15 minutes - engine net ${self.net_profit_usd:.2f} <= max loss ${self.max_global_loss_usd:.2f}"
                    )
                allow_new_buys = False

            if self.global_loss_pause_until and now >= self.global_loss_pause_until and self.net_profit_usd > (self.max_global_loss_usd * 0.5):
                logger.info("   🔵 [COINBASE] ✅ Global loss pause lifted - profitability recovered")
                self.global_loss_pause_until = None

            skip_until = self.pair_skip_until.get(pair)
            if skip_until:
                if skip_until > now:
                    logger.info(
                        f"   🔵 [COINBASE] ⏭️ Skipping {pair} until {skip_until.strftime('%H:%M:%S')} (focus on higher quality pairs)"
                    )
                    return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'pair_blacklist'}
                self.pair_skip_until.pop(pair, None)
            
            # Get current price first (needed for volume calculation)
            current_price = await self.get_current_price(pair)
            if current_price is None or current_price <= 0:
                logger.warning(f"   🔵 [COINBASE] ⚠️ Skipping {pair} - invalid price: {current_price}")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'invalid_price'}

            # Check short-term volatility and depth before quoting
            market_ok, market_metrics, health_reason = await self._evaluate_market_health(pair)
            if not market_ok:
                logger.info(
                    f"   🔵 [COINBASE] ⏭️ Skipping {pair} - {health_reason}"
                    + (f" | metrics: {market_metrics}" if any(market_metrics.values()) else "")
                )
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'market_unhealthy'}
            
            # Check volume (optional - major pairs like BTC/USD always have volume)
            # Only skip if we can actually verify volume is too low
            try:
                ticker = await self.exchange_manager.fetch_ticker('coinbase', pair)
                # Try multiple ways to get volume
                volume_24h = ticker.get('quoteVolume') or ticker.get('quote_volume')
                if not volume_24h:
                    # Calculate from base volume
                    base_volume = ticker.get('volume') or ticker.get('baseVolume')
                    last_price = ticker.get('last') or ticker.get('close') or current_price
                    if base_volume and last_price:
                        volume_24h = base_volume * last_price
                
                # Only skip if we have volume data AND it's actually low
                # Major pairs (BTC, ETH, etc.) always have volume, so don't skip if volume is None/0
                if volume_24h and volume_24h > 0 and volume_24h < 10000:
                    logger.info(f"   🔵 [COINBASE] ⏭️ Skipping {pair} - low volume: ${volume_24h:.0f}")
                    return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'low_volume'}
            except Exception as e:
                logger.debug(f"   🔵 [COINBASE] Volume check failed for {pair}: {e} - continuing anyway")
                pass  # Continue if volume check fails - major pairs have volume
            
            fill_rate = self.pair_fill_rates.get(pair, 0.5)
            required_spread = self._compute_required_spread(pair, market_metrics, fill_rate)

            pair_stats = self.stats.get(pair)
            if pair_stats and pair_stats.net_profit_usd <= self.max_pair_loss_usd:
                allow_new_buys = False
                blacklist_until = datetime.now() + timedelta(minutes=self.fill_rate_blacklist_minutes)
                self.pair_skip_until[pair] = blacklist_until
                logger.warning(
                    f"   🔵 [COINBASE] ⚠️ Skipping new buys for {pair} (net ${pair_stats.net_profit_usd:.2f} <= max pair loss ${self.max_pair_loss_usd:.2f}) until {blacklist_until.strftime('%H:%M:%S')}"
                )

            # 🔵 CRITICAL: Check for existing orders FIRST before spread check
            # If we have open orders, check them for fills even if spread is low
            existing_orders = self.active_orders.get(pair, [])
            open_orders = [o for o in existing_orders if o.status == 'open']
            
            # Get spread
            spread = await self.get_spread(pair)
            
            # 🔵 DYNAMIC: Adjust grid spacing based on spread with hard floor/ceiling
            base_spacing = (spread * 0.5) if spread and spread > 0 else self.min_spacing_percent
            dynamic_spacing = max(self.min_spacing_percent, base_spacing)
            dynamic_spacing = min(dynamic_spacing, self.max_spacing_percent)

            effective_spread = (spread or 0) + (2 * dynamic_spacing)
            spread_msg = f"{spread:.3f}%" if spread is not None else "None"
            logger.info(
                f"   🔵 [COINBASE] {pair}: Spread snapshot | raw={spread_msg} | effective={effective_spread:.3f}% | threshold={required_spread:.2f}%"
            )
            
            if fill_rate < self.min_fill_rate_threshold and not open_orders:
                allow_new_buys = False
                blacklist_until = datetime.now() + timedelta(minutes=self.fill_rate_blacklist_minutes)
                self.pair_skip_until[pair] = blacklist_until
                logger.info(
                    f"   🔵 [COINBASE] ⏸️ {pair}: Fill rate {fill_rate:.2f} below {self.min_fill_rate_threshold:.2f} - pausing new buys until {blacklist_until.strftime('%H:%M:%S')}"
                )

            # If effective spread is too low BUT we have open orders, keep checking them for fills
            if (spread is None or spread <= 0 or effective_spread < required_spread) and open_orders:
                logger.info(f"   🔵 [COINBASE] {pair}: Effective spread {effective_spread:.3f}% (raw {spread_msg}) < minimum {required_spread:.2f}%, but keeping {len(open_orders)} open order(s) to check for fills")
                # Check existing orders for fills, don't cancel them
                filled = await self.check_and_update_orders(pair)
                return {'success': True, 'orders_placed': 0, 'orders_filled': filled, 'error': None}
            
            # If effective spread is too low and no open orders, skip entirely
            if spread is None or spread <= 0 or effective_spread < required_spread:
                logger.info(f"   🔵 [COINBASE] ⏭️ Skipping {pair} - effective spread {effective_spread:.3f}% (raw {spread_msg}) < minimum {required_spread:.2f}%")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'spread_too_tight'}
            
            # 🔵 SMART: Only cancel/update orders if prices have moved significantly
            # This prevents canceling orders that are about to fill
            should_update_orders, update_reason = await self.should_update_pair_orders(pair, dynamic_spacing)
            if should_update_orders:
                logger.info(f"   🔵 [COINBASE] {pair}: Updating existing orders - Reason: {update_reason}")
                await self.cancel_pair_orders(pair, reason=f"update_required: {update_reason}")
            else:
                logger.info(f"   🔵 [COINBASE] {pair}: Keeping existing orders - Reason: {update_reason}")
                # Check for fills on existing orders
                filled = await self.check_and_update_orders(pair)
                return {'success': True, 'orders_placed': 0, 'orders_filled': filled, 'error': None}
            
            # Avoid stacking additional inventory if we still have queued sells waiting to clear
            pending_entries = self.pending_sell_queue.get(pair, [])
            if pending_entries:
                pending_value = sum(
                    entry.get('amount', 0.0) * max(current_price, entry.get('buy_price', current_price))
                    for entry in pending_entries
                )
                if pending_value >= self.min_inventory_sell_value_usd:
                    logger.info(
                        f"   🔵 [COINBASE] ⏭️ Skipping {pair} - pending sell queue size {len(pending_entries)} (~${pending_value:.2f})"
                    )
                    self._register_failure(pair, 'pending_inventory', f"pending value ${pending_value:.2f}")
                    return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'pending_sell_queue'}
                else:
                    logger.info(
                        f"   🔵 [COINBASE] {pair}: Pending queue ${pending_value:.2f} below threshold, continuing to quote both sides"
                    )

            # Get market info
            exchange = self.exchange_manager.get_exchange('coinbase')
            market_info = exchange.markets.get(pair, {})
            precision_data = market_info.get('precision', {})
            
            # 🔵 CRITICAL: Ensure precision is never 0 (would cause rounding to $0.00)
            amount_precision_val = precision_data.get('amount', 8)
            if amount_precision_val:
                amount_precision = max(int(amount_precision_val), 1)  # At least 1 decimal place
            else:
                amount_precision = 8  # Default to 8
            
            price_precision_val = precision_data.get('price', 8)
            if price_precision_val:
                price_precision = max(int(price_precision_val), 2)  # At least 2 decimal places for prices
            else:
                price_precision = 8  # Default to 8
            
            limits = market_info.get('limits', {})
            min_amount = limits.get('amount', {}).get('min', 0) or 0
            exchange_min_cost = limits.get('cost', {}).get('min', 0) or 0
            min_cost = max(exchange_min_cost, 1.0) if exchange_min_cost > 0 else 1.0  # Exchange requirement (can be < $5)
            min_buy_cost = max(min_cost, self.min_order_value_usd)
            min_target_order_value = max(min_buy_cost * self.balance_buffer_multiplier, min_buy_cost)

            quote_currency = pair.split('/')[1]
            quote_balance_cached: Optional[float] = None
            if allow_new_buys and quote_currency in ['USD', 'USDC', 'USDT']:
                quote_balance_cached = await self.get_inventory_balance(quote_currency)
                if quote_balance_cached is None:
                    quote_balance_cached = 0.0
                if quote_balance_cached < min_target_order_value:
                    logger.info(
                        f"   🔵 [COINBASE] ⏭️ Skipping {pair} - soft insufficient {quote_currency} balance "
                        f"${quote_balance_cached:.2f} < soft floor ${min_target_order_value:.2f}"
                    )
                    return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'insufficient_balance_soft'}
            
            # 🔵 DYNAMIC: Adjust order size based on spread, fill quality, and profitability
            base_currency = pair.split('/')[0]
            spread_for_multiplier = spread if spread and spread > 0 else required_spread
            spread_multiplier = min(max(spread_for_multiplier / required_spread, 0.5), 2.0)

            fill_rate_multiplier = 0.6 + fill_rate  # 0.6x to 1.6x based on fill rate

            pair_perf = self.pair_performance[pair]
            total_profit = pair_perf.get('total_profit', 0.0)
            profit_multiplier = 1.0
            if total_profit > 5:
                profit_multiplier = min(1.6, 1.0 + (total_profit / 20.0))
            elif total_profit < -3:
                profit_multiplier = max(0.55, 1.0 + (total_profit / 20.0))

            order_value_usd = 0.0
            order_amount = 0.0

            if allow_new_buys:
                order_value_usd = (
                    self.capital_per_pair
                    * self.order_size_percent
                    * spread_multiplier
                    * fill_rate_multiplier
                    * profit_multiplier
                )
                order_value_usd = min(order_value_usd, self.capital_per_pair * 0.9)
                order_value_usd = max(order_value_usd, min_target_order_value)

                if order_value_usd < min_buy_cost:
                    logger.info(f"   🔵 [COINBASE] ⏭️ Skipping {pair} - order value ${order_value_usd:.2f} < minimum ${min_buy_cost:.2f}")
                    return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'order_value_too_small'}

                order_amount = order_value_usd / current_price
                order_amount = round(order_amount, amount_precision)
                if order_amount <= 0:
                    if min_amount > 0:
                        order_amount = min_amount
                        order_value_usd = order_amount * current_price
                        if order_value_usd < min_buy_cost:
                            logger.info(f"   🔵 [COINBASE] ⏭️ Skipping {pair} - min order amount still below floor (${order_value_usd:.2f} < ${min_buy_cost:.2f})")
                            return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'order_amount_too_small'}
                    else:
                        logger.info(f"   🔵 [COINBASE] ⏭️ Skipping {pair} - order amount too small after rounding")
                        return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'order_amount_too_small'}
            
            # 🔵 DYNAMIC PRICING: Get fresh bid/ask every time for real-time adjustment
            ticker = await self.exchange_manager.fetch_ticker('coinbase', pair)
            bid = ticker.get('bid', 0) or 0
            ask = ticker.get('ask', 0) or 0
            
            # 🔵 DYNAMIC: Prices adjust based on current market conditions
            if bid > 0 and ask > 0:
                # Calculate mid price for reference
                mid_price = (bid + ask) / 2
                current_spread = ((ask - bid) / mid_price) * 100 if mid_price > 0 else 0
                
                # 🔵 DYNAMIC: Adjust spacing based on actual market spread
                # If market spread is tight, use smaller spacing to stay competitive
                # If market spread is wide, use larger spacing to capture more profit
                if current_spread > 0:
                    # Use 30-70% of market spread as our spacing (adaptive)
                    if current_spread * 0.5 < dynamic_spacing * 0.5:
                        adaptive_spacing = max(current_spread * 0.5, dynamic_spacing * 0.5)
                    else:
                        adaptive_spacing = min(max(current_spread * 0.5, dynamic_spacing * 0.5), dynamic_spacing * 1.5)
                else:
                    adaptive_spacing = dynamic_spacing
                
                # Place buy order: Aggressively below bid to get filled quickly
                # Place sell order: Aggressively above ask to get filled quickly
                # This ensures we capture the spread while staying competitive
                buy_price = bid * (1 - adaptive_spacing / 100)
                sell_price = ask * (1 + adaptive_spacing / 100)
                
                # Ensure sell_price > buy_price (critical for profitability)
                if sell_price <= buy_price:
                    # If prices are inverted, use mid price with spacing
                    buy_price = mid_price * (1 - adaptive_spacing / 100)
                    sell_price = mid_price * (1 + adaptive_spacing / 100)
                    logger.warning(f"   🔵 [COINBASE] ⚠️ {pair}: Bid/ask inverted, using mid price with spacing")
            else:
                # Fallback: Use current_price with dynamic spacing
                buy_price = current_price * (1 - dynamic_spacing / 100)
                sell_price = current_price * (1 + dynamic_spacing / 100)
            
            # 🔵 NO ROUNDING: Use exact calculated prices (exchange will handle precision)
            # Prices are already calculated with proper precision from market data
            
            top_bid_price = top_bid_volume = top_ask_price = top_ask_volume = None
            try:
                order_book = await self.exchange_manager.fetch_order_book('coinbase', pair, limit=5)
                bids = order_book.get('bids', []) or []
                asks = order_book.get('asks', []) or []
                if bids:
                    top_bid_price, top_bid_volume = bids[0][0], bids[0][1]
                if asks:
                    top_ask_price, top_ask_volume = asks[0][0], asks[0][1]
            except Exception as depth_error:
                logger.debug(f"   🔵 [COINBASE] Depth fetch (inside quote adjust) failed for {pair}: {depth_error}")
                bids = asks = []

            inside_improve = self.inside_quote_improve_bps / 10000.0
            if top_ask_price and top_ask_volume and top_ask_volume < self.inside_quote_volume_threshold:
                min_sell_floor = current_price * (1 + required_spread / 100)
                candidate_sell = top_ask_price * (1 - inside_improve)
                adjusted_sell = max(min_sell_floor, min(sell_price, candidate_sell))
                if adjusted_sell > sell_price * 0.995:  # avoid huge drops
                    logger.debug(
                        f"   🔵 [COINBASE] {pair}: Inside-quote sell adjustment {sell_price:.6f} → {adjusted_sell:.6f} (top ask vol {top_ask_volume:.2f})"
                    )
                    sell_price = adjusted_sell

            if top_bid_price and top_bid_volume and top_bid_volume < self.inside_quote_volume_threshold:
                candidate_buy = top_bid_price * (1 + inside_improve)
                max_buy_ceiling = sell_price * (1 - max(dynamic_spacing / 100, 0.001))
                candidate_buy = min(candidate_buy, max_buy_ceiling)
                if candidate_buy > buy_price:
                    logger.debug(
                        f"   🔵 [COINBASE] {pair}: Inside-quote buy adjustment {buy_price:.6f} → {candidate_buy:.6f} (top bid vol {top_bid_volume:.2f})"
                    )
                    buy_price = candidate_buy

            if sell_price <= buy_price:
                sell_price = buy_price * (1 + max(dynamic_spacing / 100, 0.0015))

            # Get inventory
            inventory = await self.get_inventory_balance(base_currency)
            quote_currency = pair.split('/')[1]
            if quote_balance_cached is None:
                quote_balance = await self.get_inventory_balance(quote_currency)
            else:
                quote_balance = quote_balance_cached
            
            # Calculate max inventory
            inventory_value = (inventory * current_price) if inventory else 0
            total_balance_usd = inventory_value + quote_balance
            max_inventory = total_balance_usd * self.max_inventory_percent
            
            # Place buy order (if we have quote currency and haven't exceeded max inventory)
            # 🔵 CRITICAL: Check balance and dynamically size order
            if quote_balance is None:
                quote_balance = 0.0
            
            if quote_balance < min_buy_cost:
                logger.info(f"   🔵 [COINBASE] ⏭️ Skipping buy order for {pair} - insufficient {quote_currency} balance ${quote_balance:.2f} < minimum order cost ${min_buy_cost:.2f}")
                order_amount = 0
            elif max_inventory > 0 and inventory_value >= max_inventory:
                logger.info(f"   🔵 [COINBASE] ⏭️ Skipping buy order for {pair} - inventory ${inventory_value:.2f} >= max ${max_inventory:.2f}")
                order_amount = 0  # Skip order
            else:
                # Calculate maximum order amount based on available balance
                # Reserve 5% buffer for fees and price movement
                available_for_order = quote_balance / 1.05
                max_order_value = available_for_order
                max_order_amount = max_order_value / buy_price if buy_price > 0 else 0
                
                # Use the smaller of: desired order_amount or max_order_amount based on balance
                if max_order_amount > 0 and max_order_amount < order_amount:
                    # Adjust order amount to fit available balance
                    original_amount = order_amount
                    order_amount = max_order_amount
                    logger.info(f"   🔵 [COINBASE] {pair}: Adjusting order size to fit balance: {original_amount:.6f} → {order_amount:.6f} (Balance: ${quote_balance:.2f} {quote_currency})")
                    
                    # Re-check minimum order size after adjustment
                    min_order_value = order_amount * buy_price
                    if min_order_value < min_buy_cost:
                        logger.info(f"   🔵 [COINBASE] ⏭️ Skipping buy order for {pair} - adjusted order value ${min_order_value:.2f} < minimum ${min_buy_cost:.2f}")
                        order_amount = 0  # Skip order
                    else:
                        # Round to precision
                        order_amount = round(order_amount, amount_precision)
                        if order_amount <= 0:
                            logger.info(f"   🔵 [COINBASE] ⏭️ Skipping buy order for {pair} - order amount rounded to 0")
                        else:
                            logger.info(f"   🔵 [COINBASE] {pair}: 📝 ATTEMPTING TO PLACE BUY ORDER... (Balance: ${quote_balance:.2f} {quote_currency}, Order: ${order_amount * buy_price:.2f})")
                elif max_order_amount >= order_amount:
                    # Have enough balance for full order
                    logger.info(f"   🔵 [COINBASE] {pair}: 📝 ATTEMPTING TO PLACE BUY ORDER... (Balance: ${quote_balance:.2f} {quote_currency}, Required: ${order_amount * buy_price:.2f})")
                else:
                    required_value = order_amount * buy_price if order_amount and buy_price else min_buy_cost
                    logger.info(f"   🔵 [COINBASE] ⏭️ Skipping buy order for {pair} - insufficient {quote_currency} balance: ${quote_balance:.2f} < minimum required ${required_value:.2f}")
                    order_amount = 0  # Skip order
                
                if order_amount > 0:
                    try:
                        buy_order = await self.exchange_manager.create_order(
                            exchange_id='coinbase',
                            symbol=pair,
                            order_type='limit',
                            side='buy',
                            amount=order_amount,
                            price=buy_price
                        )
                        
                        if buy_order and buy_order.get('id'):
                            buy_order_id = buy_order.get('id')
                            buy_mm_order = MarketMakingOrder(
                                pair=pair,
                                side='buy',
                                order_id=buy_order_id,
                                price=buy_price,
                                amount=order_amount,
                                status='open'
                            )
                            self.active_orders[pair].append(buy_mm_order)
                            orders_placed += 1
                            self.last_buy_prices[pair] = buy_price
                            self._reset_failures(pair)
                            logger.info(f"   🔵 [COINBASE] ✅ BUY ORDER PLACED: {pair} @ ${buy_price:.4f} for {order_amount:.6f} | Order ID: {buy_order_id}")
                    except Exception as e:
                        logger.error(f"   🔵 [COINBASE] ❌ FAILED TO PLACE BUY ORDER: {e}")
            
            # Place sell order (if we have inventory)
            if inventory is not None and inventory > 0:
                min_amount_limit = market_info.get('limits', {}).get('amount', {}).get('min', 0) or 0
                required_amount_for_value = (min_cost / sell_price) if sell_price and sell_price > 0 else 0
                required_amount = max(min_amount_limit, required_amount_for_value)

                if inventory < required_amount:
                    logger.info(
                        f"   🔵 [COINBASE] {pair}: ⏭️ Skipping sell order - inventory {inventory:.6f} ({inventory * sell_price:.2f}) < minimum requirement {required_amount:.6f} ({min_cost:.2f})"
                    )
                else:
                    sell_amount = inventory
                    logger.info(f"   🔵 [COINBASE] {pair}: 📝 ATTEMPTING TO PLACE SELL ORDER... (Inventory: {inventory:.6f})")
                    try:
                        # 🔵 CRITICAL FIX: Validate sell order parameters
                        if sell_amount is None or sell_amount <= 0:
                            logger.error(f"   🔵 [COINBASE] ❌ Invalid sell_amount: {sell_amount}")
                            raise ValueError(f"Invalid sell_amount: {sell_amount}")
                        if sell_price is None or sell_price <= 0:
                            logger.error(f"   🔵 [COINBASE] ❌ Invalid sell_price: {sell_price}")
                            raise ValueError(f"Invalid sell_price: {sell_price}")
                        
                        last_buy_price = self.last_buy_prices.get(pair)
                        min_target_price = self._get_min_profitable_sell_price(
                            pair,
                            fallback_buy_price=last_buy_price or sell_price
                        )

                        if min_target_price and sell_price < min_target_price:
                            logger.info(
                                f"   🔵 [COINBASE] {pair}: Raising inventory sell price to maintain profit buffer ({sell_price:.6f} → {min_target_price:.6f})"
                            )
                            sell_price = min_target_price

                        logger.debug(f"   🔵 [COINBASE] {pair}: Creating sell order - amount={sell_amount:.6f}, price=${sell_price:.6f}")
                        sell_order = await self.exchange_manager.create_order(
                            exchange_id='coinbase',
                            symbol=pair,
                            order_type='limit',
                            side='sell',
                            amount=sell_amount,
                            price=sell_price
                        )
                        logger.debug(f"   🔵 [COINBASE] {pair}: Sell order response = {sell_order}")
                        
                        if sell_order and sell_order.get('id'):
                            sell_order_id = sell_order.get('id')
                            sell_mm_order = MarketMakingOrder(
                                pair=pair,
                                side='sell',
                                order_id=sell_order_id,
                                price=sell_price,
                                amount=sell_amount,
                                status='open'
                            )
                            self.active_orders[pair].append(sell_mm_order)
                            orders_placed += 1
                            logger.info(f"   🔵 [COINBASE] ✅✅✅ SELL ORDER PLACED SUCCESSFULLY: {pair} @ ${sell_price:.4f} for {sell_amount:.6f} (${sell_amount * sell_price:.2f}) | Order ID: {sell_order_id}")
                            self._reset_failures(pair)
                            self.pair_performance[pair]['total_trades'] += 1
                        else:
                            logger.warning(f"   🔵 [COINBASE] ⚠️ Sell order creation returned no ID: {sell_order}")
                    except Exception as e:
                        logger.error(f"   🔵 [COINBASE] ❌ FAILED TO PLACE SELL ORDER for {pair}: {type(e).__name__}: {e}")
            
            # Check for filled orders
            orders_filled = await self.check_and_update_orders(pair)
            
            return {'success': orders_placed > 0, 'orders_placed': orders_placed, 'orders_filled': orders_filled, 'error': None}
            
        except Exception as e:
            logger.error(f"   🔵 [COINBASE] ❌ ERROR placing market-making orders for {pair}: {e}")
            return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': str(e)}
    
    async def should_update_pair_orders(self, pair: str, target_spacing: float) -> Tuple[bool, str]:
        """Determine if existing orders should be updated. Returns (should_update, reason)."""
        existing_orders = self.active_orders.get(pair, [])
        if not existing_orders:
            return True, "no existing orders"
        
        open_orders = [o for o in existing_orders if o.status == 'open']
        if not open_orders:
            return True, "all orders closed"
        
        now = datetime.now()
        for order in open_orders:
            age_seconds = (now - order.created_at).total_seconds()
            if age_seconds > 900:  # 15 minutes to allow fills
                return True, f"order {order.order_id} age {age_seconds:.0f}s > 900s"
        
        try:
            ticker = await self.exchange_manager.fetch_ticker('coinbase', pair)
            current_bid = ticker.get('bid', 0) or 0
            current_ask = ticker.get('ask', 0) or 0
            
            if current_bid <= 0 or current_ask <= 0:
                return True, "missing bid/ask data"
            
            try:
                order_book = await self.exchange_manager.fetch_order_book('coinbase', pair, limit=20)
                bids = order_book.get('bids', []) or []
                asks = order_book.get('asks', []) or []
            except Exception as depth_error:
                bids, asks = [], []
                logger.debug(f"   🔵 [COINBASE] Depth fetch failed for {pair}: {depth_error}")

            top_bid_volume = bids[0][1] if bids else 0
            top_ask_volume = asks[0][1] if asks else 0

            drift_floor = max(self.micro_reprice_threshold, target_spacing * 0.5)
            buy_drift_threshold = drift_floor
            sell_drift_threshold = max(drift_floor * 1.8, target_spacing * 1.2)
            sell_grace_period = 120

            for order in open_orders:
                if order.price <= 0:
                    continue

                order_age = (now - order.created_at).total_seconds()

                if order.side == 'buy':
                    price_diff_pct = abs((current_bid - order.price) / current_bid) * 100
                    if order.price >= current_ask:
                        return True, f"buy order {order.order_id} price {order.price} >= current ask {current_ask}"
                    if top_ask_volume > top_bid_volume * 3 and price_diff_pct < 0.4:
                        return True, f"heavy ask pressure ({top_ask_volume:.4f} vs {top_bid_volume:.4f})"
                    drift_threshold = buy_drift_threshold
                else:
                    price_diff_pct = abs((current_ask - order.price) / current_ask) * 100
                    if order.price <= current_bid:
                        return True, f"sell order {order.order_id} price {order.price} <= current bid {current_bid}"
                    if top_bid_volume > top_ask_volume * 3 and price_diff_pct < 0.35:
                        return True, f"heavy bid pressure ({top_bid_volume:.4f} vs {top_ask_volume:.4f})"
                    drift_threshold = sell_drift_threshold

                    if order_age < sell_grace_period and price_diff_pct < max(drift_threshold, self.micro_reprice_threshold * 2):
                        continue

                if price_diff_pct > drift_threshold:
                    return True, f"order {order.order_id} price drift {price_diff_pct:.2f}%"
        except Exception as e:
            logger.debug(f"   🔵 [COINBASE] Error checking price movement for {pair}: {e}")
            return True, f"error checking price drift: {e}"

        # Orders are still competitive, keep them
        return False, "orders still competitive"
    
    async def cancel_pair_orders(self, pair: str, reason: str = "unspecified"):
        """Cancel all active orders for a pair with detailed logging"""
        try:
            orders_to_cancel = self.active_orders[pair].copy()
            open_orders = [o for o in orders_to_cancel if o.status == 'open']
            if not open_orders:
                logger.info(f"   🔵 [COINBASE] {pair}: No open orders to cancel (reason: {reason})")
                return
            logger.info(f"   🔵 [COINBASE] {pair}: Canceling {len(open_orders)} order(s) - Reason: {reason}")
            for mm_order in orders_to_cancel:
                if mm_order.order_id and mm_order.status == 'open':
                    try:
                        await self.exchange_manager.cancel_order(
                            'coinbase',
                            mm_order.order_id,
                            pair
                        )
                        mm_order.status = 'canceled'
                        logger.info(
                            f"   🔵 [COINBASE] ❎ ORDER CANCELED: {pair} | ID {mm_order.order_id} | "
                            f"Side: {mm_order.side} | Price: ${mm_order.price:.6f} | Amount: {mm_order.amount:.6f}"
                        )
                    except Exception as e:
                        logger.error(f"   🔵 [COINBASE] ❌ Failed to cancel order {mm_order.order_id} for {pair}: {e}")
            
            self.active_orders[pair] = [
                o for o in self.active_orders[pair] 
                if o.status == 'open' or o.status == 'filled'
            ]
        except Exception as e:
            logger.error(f"   🔵 [COINBASE] ❌ Error canceling orders for {pair}: {e}")
    
    async def check_and_update_orders(self, pair: str) -> int:
        """Check order status and update if needed. Returns count of filled orders."""
        filled_count = 0
        try:
            orders_to_check = self.active_orders.get(pair, []).copy()
            if not orders_to_check:
                return 0
            
            for mm_order in orders_to_check:
                if mm_order.order_id and mm_order.status == 'open':
                    try:
                        order_status = await self.exchange_manager.fetch_order(
                            'coinbase',
                            mm_order.order_id,
                            pair
                        )

                        info = order_status.get('info', {}) or {}
                        status = (order_status.get('status') or info.get('status') or 'unknown').lower()

                        def _as_float(value, default=0.0):
                            try:
                                if value is None:
                                    return default
                                return float(value)
                            except (TypeError, ValueError):
                                return default

                        amount = _as_float(order_status.get('amount'), mm_order.amount or 0.0)
                        if amount <= 0:
                            amount = _as_float(info.get('size'), mm_order.amount or 0.0)

                        filled_candidates = [
                            order_status.get('filled'),
                            info.get('filled_size'),
                            info.get('executed_value'),
                        ]
                        filled = 0.0
                        for candidate in filled_candidates:
                            filled = _as_float(candidate, None)
                            if filled is not None:
                                break
                        if filled is None:
                            remaining_hint = _as_float(order_status.get('remaining'), None)
                            if remaining_hint is None:
                                remaining_hint = _as_float(info.get('remaining_size'), 0.0)
                            filled = max(amount - remaining_hint, 0.0)

                        remaining_candidates = [
                            order_status.get('remaining'),
                            info.get('remaining_size'),
                            amount - filled
                        ]
                        remaining = None
                        for candidate in remaining_candidates:
                            remaining = _as_float(candidate, None)
                            if remaining is not None:
                                break
                        if remaining is None:
                            remaining = max(amount - filled, 0.0)

                        if remaining <= 1e-8 and amount > 0 and filled < amount:
                            filled = amount
                        if remaining <= 1e-8:
                            status = 'filled'

                        price = _as_float(order_status.get('price'), mm_order.price)
                        if price <= 0:
                            price = _as_float(info.get('price'), mm_order.price)
                        
                        # Track previous filled amount to detect new fills
                        previous_filled = getattr(mm_order, 'filled_amount', 0.0)
                        new_filled = filled - previous_filled
                        
                        if filled > previous_filled:
                            # New fill detected (partial or full)
                            mm_order.filled_amount = filled
                            
                            if mm_order.side == 'buy':
                                # Buy order got filled (partially or fully)
                                fee_info = order_status.get('fee', {}) or {}
                                total_fee = float(fee_info.get('cost', 0) or 0)
                                fee_per_unit = (total_fee / filled) if filled > 0 else 0.0
                                if new_filled > 0:
                                    new_fee = fee_per_unit * new_filled
                                    cost_value = price * new_filled
                                    self.position_tracker[pair].append({
                                        'amount': new_filled,
                                        'cost': cost_value,
                                        'fees': new_fee
                                    })
                                    self.stats[pair].total_fees_usd += new_fee
                                    self.stats[pair].net_profit_usd -= new_fee
                                    self.net_profit_usd -= new_fee
                                    mm_order.fees_paid += new_fee
                                if status in ['closed', 'filled', 'done', 'completed']:
                                    mm_order.status = 'filled'
                                    mm_order.filled_at = datetime.now()
                                    self.stats[pair].filled_orders += 1
                                    self.stats[pair].total_orders += 1
                                    filled_count += 1
                                    self.last_buy_prices[pair] = price
                                    logger.info(f"   🔵 [COINBASE] ✅✅✅ BUY FULLY FILLED: {pair} @ ${price:.4f} for {filled:.6f}")
                                else:
                                    # Partial fill
                                    logger.info(f"   🔵 [COINBASE] ✅ BUY PARTIALLY FILLED: {pair} @ ${price:.4f} - {new_filled:.6f} filled (total: {filled:.6f}/{mm_order.amount:.6f})")
                                
                                # 🔵 CRITICAL: Immediately sell the NEW amount that was just filled
                                if new_filled > 0:
                                    try:
                                        self.last_buy_prices[pair] = price
                                        sell_placed = await self._place_sell_order_for_filled_buy(pair, new_filled, price)
                                        if not sell_placed:
                                            logger.info(f"   🔵 [COINBASE] {pair}: Queued {new_filled:.6f} for later sell (inventory pending)")
                                    except Exception as e:
                                        logger.error(f"   🔵 [COINBASE] ❌ ERROR placing sell order after buy fill: {type(e).__name__}: {e}")
                                        import traceback
                                        logger.debug(f"   🔵 [COINBASE] Traceback: {traceback.format_exc()}")
                            
                            elif mm_order.side == 'sell':
                                fee_info = order_status.get('fee', {}) or {}
                                total_fee = float(fee_info.get('cost', 0) or 0)
                                fee_per_unit = (total_fee / filled) if filled > 0 else 0.0
                                remaining = new_filled
                                gross_accum = 0.0
                                fee_accum = 0.0
                                net_accum = 0.0
                                while remaining > 1e-12 and self.position_tracker[pair]:
                                    lot = self.position_tracker[pair][0]
                                    lot_amount = lot['amount']
                                    take = min(remaining, lot_amount)
                                    proportion = take / lot_amount if lot_amount > 0 else 0
                                    cost_value = lot['cost'] * proportion
                                    buy_fee = lot['fees'] * proportion
                                    sell_fee = fee_per_unit * take
                                    revenue = price * take
                                    gross = revenue - cost_value
                                    fees_total = buy_fee + sell_fee
                                    net = gross - fees_total
                                    gross_accum += gross
                                    fee_accum += fees_total
                                    net_accum += net
                                    lot['amount'] -= take
                                    lot['cost'] -= cost_value
                                    lot['fees'] -= buy_fee
                                    if lot['amount'] <= 1e-12:
                                        self.position_tracker[pair].pop(0)
                                    remaining -= take
                                if remaining > 1e-12:
                                    logger.warning(
                                        f"   🔵 [COINBASE] ⚠️ {pair}: Sell filled {new_filled:.6f} but only matched {new_filled-remaining:.6f} from inventory tracker"
                                    )
                                self.stats[pair].total_profit_usd += gross_accum
                                self.stats[pair].total_fees_usd += fee_accum
                                self.stats[pair].net_profit_usd += net_accum
                                self.net_profit_usd += net_accum
                                self.pair_performance[pair]['total_profit'] += net_accum
                                if net_accum >= 0:
                                    self.stats[pair].wins += 1
                                else:
                                    self.stats[pair].losses += 1
                                logger.info(
                                    f"   🔵 [COINBASE] ✅ SELL {'FULLY ' if status in ['closed', 'filled'] else ''}FILLED: {pair} @ ${price:.4f} for {new_filled:.6f} | Gross: ${gross_accum:.4f} | Fees: ${fee_accum:.4f} | Net: ${net_accum:.4f}"
                                )
                                if status in ['closed', 'filled', 'done', 'completed']:
                                    mm_order.status = 'filled'
                                    mm_order.filled_at = datetime.now()
                                    self.stats[pair].filled_orders += 1
                                    self.stats[pair].total_orders += 1
                                    filled_count += 1
                                    if not self.position_tracker[pair]:
                                        self.pair_last_inventory_timestamp.pop(pair, None)
                                    self.pair_performance[pair]['total_trades'] += 1
                            
                            # Update fill rate
                            current_fill_rate = self.pair_fill_rates.get(pair, 0.5)
                            self.pair_fill_rates[pair] = current_fill_rate * 0.9 + 0.1
                        
                        elif status in ['closed', 'filled', 'done', 'completed'] and mm_order.status == 'open':
                            # Order fully filled but we didn't detect it above (fallback)
                            mm_order.status = 'filled'
                            mm_order.filled_at = datetime.now()
                            self.stats[pair].filled_orders += 1
                            self.stats[pair].total_orders += 1
                            filled_count += 1
                            
                            if mm_order.side == 'buy':
                                fee_info = order_status.get('fee', {}) or {}
                                total_fee = float(fee_info.get('cost', 0) or 0)
                                fee_per_unit = (total_fee / filled) if filled > 0 else 0.0
                                if filled > 0:
                                    new_fee = fee_per_unit * filled
                                    cost_value = price * filled
                                    self.position_tracker[pair].append({
                                        'amount': filled,
                                        'cost': cost_value,
                                        'fees': new_fee
                                    })
                                    self.stats[pair].total_fees_usd += new_fee
                                    self.stats[pair].net_profit_usd -= new_fee
                                    self.net_profit_usd -= new_fee
                                    mm_order.fees_paid += new_fee
                                logger.info(f"   🔵 [COINBASE] ✅✅✅ BUY FILLED: {pair} @ ${price:.4f} for {filled:.6f}")
                                try:
                                    self.last_buy_prices[pair] = price
                                    sell_placed = await self._place_sell_order_for_filled_buy(pair, filled, price)
                                    if not sell_placed:
                                        logger.info(f"   🔵 [COINBASE] {pair}: Queued {filled:.6f} for later sell (inventory pending)")
                                except Exception as e:
                                    logger.error(f"   🔵 [COINBASE] ❌ ERROR placing sell order after buy fill: {type(e).__name__}: {e}")
                            else:
                                fee_info = order_status.get('fee', {}) or {}
                                total_fee = float(fee_info.get('cost', 0) or 0)
                                fee_per_unit = (total_fee / filled) if filled > 0 else 0.0
                                remaining = filled
                                gross_accum = 0.0
                                fee_accum = 0.0
                                net_accum = 0.0
                                while remaining > 1e-12 and self.position_tracker[pair]:
                                    lot = self.position_tracker[pair][0]
                                    lot_amount = lot['amount']
                                    take = min(remaining, lot_amount)
                                    proportion = take / lot_amount if lot_amount > 0 else 0
                                    cost_value = lot['cost'] * proportion
                                    buy_fee = lot['fees'] * proportion
                                    sell_fee = fee_per_unit * take
                                    revenue = price * take
                                    gross = revenue - cost_value
                                    fees_total = buy_fee + sell_fee
                                    net = gross - fees_total
                                    gross_accum += gross
                                    fee_accum += fees_total
                                    net_accum += net
                                    lot['amount'] -= take
                                    lot['cost'] -= cost_value
                                    lot['fees'] -= buy_fee
                                    if lot['amount'] <= 1e-12:
                                        self.position_tracker[pair].pop(0)
                                    remaining -= take
                                if remaining > 1e-12:
                                    logger.warning(
                                        f"   🔵 [COINBASE] ⚠️ {pair}: Fallback sell filled {filled:.6f} but only matched {filled-remaining:.6f} from inventory tracker"
                                    )
                                self.stats[pair].total_profit_usd += gross_accum
                                self.stats[pair].total_fees_usd += fee_accum
                                self.stats[pair].net_profit_usd += net_accum
                                self.net_profit_usd += net_accum
                                self.pair_performance[pair]['total_profit'] += net_accum
                                if net_accum >= 0:
                                    self.stats[pair].wins += 1
                                else:
                                    self.stats[pair].losses += 1
                                logger.info(
                                    f"   🔵 [COINBASE] ✅ SELL FILLED: {pair} @ ${price:.4f} for {filled:.6f} | Gross: ${gross_accum:.4f} | Fees: ${fee_accum:.4f} | Net: ${net_accum:.4f}"
                                )
                                if not self.position_tracker[pair]:
                                    self.pair_last_inventory_timestamp.pop(pair, None)
                                self.pair_performance[pair]['total_trades'] += 1
                        
                        elif status in ['canceled', 'cancelled']:
                            mm_order.status = 'canceled'
                            cancel_reason = (
                                order_status.get('info')
                                or order_status.get('reason')
                                or order_status.get('message')
                                or 'exchange_cancelled'
                            )
                            logger.warning(
                                f"   🔵 [COINBASE] ⚠️ ORDER CANCELED BY EXCHANGE: {pair} | ID {mm_order.order_id} | "
                                f"Side: {mm_order.side} | Filled: {filled:.6f} | Remaining: {remaining:.6f} | Reason: {cancel_reason}"
                            )
                        else:
                            mm_order.status = status
                            logger.info(
                                f"   🔵 [COINBASE] ℹ️ ORDER STATUS CHECK: {pair} | ID {mm_order.order_id} | "
                                f"Side: {mm_order.side} | Status: {status} | Filled: {filled:.6f} | Remaining: {remaining:.6f}"
                            )
                    except Exception as e:
                        logger.error(f"   🔵 [COINBASE] ❌ Error checking order {mm_order.order_id} for {pair}: {e}")
        except Exception as e:
            logger.error(f"   🔵 [COINBASE] ❌ Error updating orders for {pair}: {e}")
        
        return filled_count
    
    async def _place_sell_order_for_filled_buy(self, pair: str, filled_amount: float, buy_price: float, allow_queue: bool = True) -> bool:
        """Try to place a follow-up sell for a newly filled buy. Returns True when an order is submitted."""
        try:
            base_currency = pair.split('/')[0]

            await asyncio.sleep(0.2)

            max_checks = 5
            inventory = 0.0
            for attempt in range(max_checks):
                balance_value = await self.get_inventory_balance(base_currency)
                inventory = balance_value or 0.0
                if inventory + 1e-8 >= filled_amount:
                    break
                await asyncio.sleep(0.3 * (attempt + 1))
            else:
                balance_value = await self.get_inventory_balance(base_currency)
                inventory = balance_value or 0.0

            if inventory <= 0:
                if allow_queue:
                    self.pending_sell_queue[pair].append({
                        'amount': filled_amount,
                        'buy_price': buy_price,
                        'created_at': datetime.now(),
                        'retry_count': 0
                    })
                    logger.warning(f"   🔵 [COINBASE] ⚠️ {pair}: Inventory not ready after buy fill ({filled_amount:.6f}). Queued for retry.")
                return False

            self.pair_last_inventory_timestamp[pair] = datetime.now()

            sell_amount = min(filled_amount, inventory)
            leftover_amount = max(filled_amount - sell_amount, 0.0)

            ticker = await self.exchange_manager.fetch_ticker('coinbase', pair)
            current_ask = ticker.get('ask', 0) or 0

            min_sell_price_with_buffer = buy_price * (1 + self.min_spread_percent / 100)
            min_profit_price = buy_price * (1 + self.min_profit_buffer_percent / 100)
            min_profitable_price = self._get_min_profitable_sell_price(pair, fallback_buy_price=buy_price)

            if current_ask <= 0:
                sell_price = max(
                    buy_price * 1.01,
                    min_profit_price,
                    min_sell_price_with_buffer,
                    min_profitable_price or 0
                )
                logger.warning(f"   🔵 [COINBASE] ⚠️ {pair}: Missing ask, using fallback ${sell_price:.6f}")
            else:
                spread = await self.get_spread(pair)
                if spread and spread > 0:
                    markup = min(max(spread * 0.5, 0.25), 1.0) / 100
                else:
                    markup = 0.003

                sell_price = current_ask * (1 + markup)
                target_price = max(
                    min_sell_price_with_buffer,
                    min_profit_price,
                    min_profitable_price or 0
                )
                if sell_price < target_price:
                    logger.info(
                        f"   🔵 [COINBASE] {pair}: Raising sell target to maintain buffer ({sell_price:.6f} → {target_price:.6f})"
                    )
                    sell_price = target_price

            exchange = self.exchange_manager.get_exchange('coinbase')
            market_info = exchange.markets.get(pair, {})
            precision_data = market_info.get('precision', {})

            amount_precision = max(int(precision_data.get('amount', 8)), 1)

            sell_amount = round(sell_amount, amount_precision)

            limits = market_info.get('limits', {})
            exchange_min_cost = limits.get('cost', {}).get('min')
            min_cost = exchange_min_cost if exchange_min_cost and exchange_min_cost > 0 else 1.0
            min_amount = limits.get('amount', {}).get('min', 0.0) or 0.0

            order_value = sell_amount * sell_price
            if order_value < min_cost or sell_amount < min_amount:
                if allow_queue:
                    self.pending_sell_queue[pair].append({
                        'amount': filled_amount,
                        'buy_price': buy_price,
                        'created_at': datetime.now(),
                        'retry_count': 0
                    })
                    logger.warning(
                        f"   🔵 [COINBASE] ⚠️ {pair}: Sell below minimums (value ${order_value:.2f}, amount {sell_amount:.6f}). Queued for later."
                    )
                else:
                    logger.debug(
                        f"   🔵 [COINBASE] {pair}: Retry sell still below minimums (value ${order_value:.2f}, amount {sell_amount:.6f})."
                    )
                return False

            jitter = (random.random() * 0.0001 - 0.00005) * sell_price
            sell_price += jitter
            sell_price = max(sell_price, min_profit_price, min_sell_price_with_buffer, min_profitable_price or 0)

            logger.info(
                f"   🔵 [COINBASE] 📝 PLACING SELL ORDER for filled buy: {pair} @ ${sell_price:.6f} for {sell_amount:.6f} (${order_value:.2f})"
            )

            sell_order = await self.exchange_manager.create_order(
                exchange_id='coinbase',
                symbol=pair,
                order_type='limit',
                side='sell',
                amount=sell_amount,
                price=sell_price
            )

            if sell_order and sell_order.get('id'):
                sell_order_id = sell_order['id']
                mm_order = MarketMakingOrder(
                    pair=pair,
                    side='sell',
                    price=sell_price,
                    amount=sell_amount,
                    order_id=sell_order_id,
                    status='open',
                    created_at=datetime.now()
                )
                self.active_orders[pair].append(mm_order)
                logger.info(
                    f"   🔵 [COINBASE] ✅✅✅ SELL ORDER PLACED for filled buy: {pair} @ ${sell_price:.4f} for {sell_amount:.6f} | Order ID: {sell_order_id}"
                )
                self._reset_failures(pair)

                if leftover_amount > 1e-8 and allow_queue:
                    self.pending_sell_queue[pair].append({
                        'amount': leftover_amount,
                        'buy_price': buy_price,
                        'created_at': datetime.now(),
                        'retry_count': 0
                    })
                    logger.info(f"   🔵 [COINBASE] {pair}: Queued remaining {leftover_amount:.6f} for follow-up sell")

                return True

            logger.warning(f"   🔵 [COINBASE] ❌ Sell order placement returned no ID for {pair}: {sell_order}")
            if allow_queue:
                self.pending_sell_queue[pair].append({
                    'amount': filled_amount,
                    'buy_price': buy_price,
                    'created_at': datetime.now(),
                    'retry_count': 0
                })
            return False

        except Exception as e:
            logger.error(f"   🔵 [COINBASE] ❌ ERROR placing follow-up sell order on {pair}: {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"   🔵 [COINBASE] Traceback: {traceback.format_exc()}")
            if allow_queue:
                self.pending_sell_queue[pair].append({
                    'amount': filled_amount,
                    'buy_price': buy_price,
                    'created_at': datetime.now(),
                    'retry_count': 0
                })
            return False

    async def _flush_pending_sell_queue(self):
        """Retry queued sells that were waiting for balances or minimum sizing."""
        if not self.pending_sell_queue:
            return

        exchange = self.exchange_manager.get_exchange('coinbase')

        for pair in list(self.pending_sell_queue.keys()):
            entries = self.pending_sell_queue.get(pair, [])
            if not entries:
                self.pending_sell_queue.pop(pair, None)
                continue

            market_info = exchange.markets.get(pair, {}) or {}
            limits = market_info.get('limits', {}) or {}
            exchange_min_cost = limits.get('cost', {}).get('min', 0) or 0
            min_cost = max(exchange_min_cost, 1.0) if exchange_min_cost > 0 else 1.0

            total_amount = sum(entry.get('amount', 0.0) for entry in entries)
            weighted_buy_value = sum(entry.get('amount', 0.0) * entry.get('buy_price', 0.0) for entry in entries)
            weighted_buy_price = (weighted_buy_value / total_amount) if total_amount > 0 else 0.0
            current_price = await self.get_current_price(pair) or weighted_buy_price
            aggregated_value = total_amount * max(current_price, weighted_buy_price)

            if total_amount > 0 and aggregated_value >= min_cost:
                aggregated_success = await self._place_sell_order_for_filled_buy(
                    pair,
                    total_amount,
                    weighted_buy_price or current_price,
                    allow_queue=False
                )
                if aggregated_success:
                    logger.info(
                        f"   🔵 [COINBASE] {pair}: Cleared pending queue with aggregated sell "
                        f"{total_amount:.6f} (~${aggregated_value:.2f})"
                    )
                    self.pending_sell_queue.pop(pair, None)
                    continue

            remaining: List[Dict[str, Any]] = []
            for entry in entries:
                amount = entry.get('amount', 0.0)
                buy_price = entry.get('buy_price', 0.0)
                retry_count = entry.get('retry_count', 0)

                estimated_value = amount * max(current_price, buy_price)
                if estimated_value < min_cost * 0.9:
                    entry['retry_count'] = retry_count + 1
                    if entry['retry_count'] % 10 == 0:
                        logger.info(
                            f"   🔵 [COINBASE] Pending sell for {pair} still below minimum (${estimated_value:.2f} < ${min_cost:.2f}); awaiting additional fills"
                        )
                    remaining.append(entry)
                    continue

                success = await self._place_sell_order_for_filled_buy(pair, amount, buy_price, allow_queue=False)
                if success:
                    continue
                entry['retry_count'] = retry_count + 1
                if entry['retry_count'] % 5 == 0:
                    logger.warning(
                        f"   🔵 [COINBASE] ⚠️ Pending sell for {pair} still waiting after {entry['retry_count']} attempts (amount {amount:.6f})"
                    )
                remaining.append(entry)

            if remaining:
                self.pending_sell_queue[pair] = remaining
            else:
                self.pending_sell_queue.pop(pair, None)
    
    async def flatten_positions(self):
        """Flatten all positions (take profit)"""
        try:
            logger.info("   🔵 [COINBASE] 🔄 FLATTENING POSITIONS (Take Profit)...")
            
            exchange = self.exchange_manager.get_exchange('coinbase')
            flattened_count = 0
            
            for pair in self.available_pairs:
                base_currency = pair.split('/')[0]
                inventory = await self.get_inventory_balance(base_currency)
                
                if inventory and inventory > 0:
                    last_inventory_time = self.pair_last_inventory_timestamp.get(pair)
                    inventory_age_minutes = None
                    if last_inventory_time:
                        inventory_age_minutes = (datetime.now() - last_inventory_time).total_seconds() / 60

                    spread = await self.get_spread(pair)
                    fill_rate = self.pair_fill_rates.get(pair, 0.5)
                    market_ok, market_metrics, _ = await self._evaluate_market_health(pair)
                    required_spread = self._compute_required_spread(pair, market_metrics, fill_rate)

                    flatten_due_to_age = inventory_age_minutes is not None and inventory_age_minutes >= self.inventory_max_age_minutes
                    flatten_due_to_spread = spread is not None and spread < required_spread
                    flatten_due_to_risk = self.net_profit_usd <= self.max_global_loss_usd

                    if not (flatten_due_to_age or flatten_due_to_spread or flatten_due_to_risk or not market_ok):
                        continue

                    current_price = await self.get_current_price(pair)
                    if current_price and current_price > 0:
                        # Check if position is large enough to flatten (must meet minimum order size)
                        market_info = exchange.markets.get(pair, {})
                        limits = market_info.get('limits', {})
                        # 🔵 FLEXIBLE: Use exchange minimum or $1.00 (whichever is lower) to allow smaller orders
                        exchange_min_cost = limits.get('cost', {}).get('min', 0) or 0
                        min_cost = max(exchange_min_cost, 1.0) if exchange_min_cost > 0 else 1.0  # At least $1.00, use exchange min if higher
                        
                        position_value = inventory * current_price
                        if position_value < min_cost:
                            logger.debug(f"   🔵 [COINBASE] Skipping flatten {pair} - position value ${position_value:.2f} < minimum ${min_cost:.2f}")
                            continue
                        
                        sell_amount = inventory * 0.95  # 95% to leave buffer

                        min_profitable_price = self._get_min_profitable_sell_price(
                            pair,
                            fallback_buy_price=self.last_buy_prices.get(pair, current_price)
                        )

                        if min_profitable_price and current_price < min_profitable_price and not flatten_due_to_risk:
                            logger.info(
                                f"   🔵 [COINBASE] Skipping flatten {pair} - current price ${current_price:.4f} below profitable threshold ${min_profitable_price:.4f}"
                            )
                            continue

                        baseline_price = current_price * (1 + max(required_spread / 100.0, self.min_profit_buffer_percent / 100.0, 0.0015))
                        if min_profitable_price:
                            sell_price = max(min_profitable_price, baseline_price)
                        else:
                            sell_price = baseline_price
                        
                        # Ensure order meets minimum
                        if sell_amount * sell_price < min_cost:
                            logger.debug(f"   🔵 [COINBASE] Skipping flatten {pair} - order value ${sell_amount * sell_price:.2f} < minimum ${min_cost:.2f}")
                            continue
                        
                        try:
                            sell_order = await self.exchange_manager.create_order(
                                exchange_id='coinbase',
                                symbol=pair,
                                order_type='limit',
                                side='sell',
                                amount=sell_amount,
                                price=sell_price
                            )
                            self.pair_last_inventory_timestamp[pair] = datetime.now()
                            logger.info(f"   🔵 [COINBASE] ✅ FLATTENED {pair}: Placed sell order for {sell_amount:.6f} {base_currency} @ ${sell_price:.4f}")
                            flattened_count += 1
                        except Exception as e:
                            logger.warning(f"   🔵 [COINBASE] ⚠️ Failed to flatten {pair}: {e}")
            
            # Cancel all orders
            for pair in self.available_pairs:
                await self.cancel_pair_orders(pair, reason="flatten_positions")
            
            logger.info(f"   🔵 [COINBASE] ✅ Flattened {flattened_count} positions, canceled all orders")
            self.last_flatten_time = datetime.now()
        except Exception as e:
            logger.error(f"   🔵 [COINBASE] ❌ Error flattening positions: {e}")
    
    async def run_market_making_loop(self):
        """Main market-making loop with dynamic adjustments"""
        logger.info("=" * 80)
        logger.info("🚀 STARTING COINBASE MARKET-MAKING LOOP")
        logger.info("=" * 80)
        logger.info(f"   🔵 Available pairs: {len(self.available_pairs)}")
        logger.info(f"   🔵 Update interval: {self.requote_interval_seconds}s")
        logger.info(f"   🔵 Take profit interval: {self.take_profit_interval_minutes} minutes")
        logger.info(f"   🔵 Capital per pair: ${self.capital_per_pair:.2f}")
        logger.info(f"   🔵 Order size: {self.order_size_percent*100:.1f}% of capital = ${self.capital_per_pair * self.order_size_percent:.2f} per order")
        logger.info(f"   🔵 Dynamic adjustments: Order size and spacing adjust based on spread and fill rate")
        logger.info("=" * 80)
        
        self.running = True
        if not hasattr(self, 'last_flatten_time') or self.last_flatten_time is None:
            self.last_flatten_time = datetime.now()

        cycle_count = 0
        
        while self.running:
            try:
                cycle_count += 1
                logger.info("")
                logger.info(f"🔵 [COINBASE] MARKET-MAKING CYCLE #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info("=" * 80)
                
                # 🔵 CRITICAL: Check and sell ALL inventory first (even if not in trading pairs)
                await self.sell_all_inventory()
                # 🔵 Ensure any queued sells from balance lag are retried promptly
                await self._flush_pending_sell_queue()
                
                # Check if time to flatten (take profit)
                time_since_flatten = (datetime.now() - self.last_flatten_time).total_seconds() / 60
                if time_since_flatten >= self.take_profit_interval_minutes:
                    logger.info(f"   🔵 [COINBASE] Time to take profit ({time_since_flatten:.1f} min >= {self.take_profit_interval_minutes} min)")
                    await self.flatten_positions()
                else:
                    logger.info(f"   🔵 [COINBASE] Time until flatten: {self.take_profit_interval_minutes - time_since_flatten:.1f} minutes")
                
                # 🔵 DYNAMIC: Sort pairs by performance (focus on profitable pairs)
                pairs_to_process = sorted(
                    self.available_pairs,
                    key=lambda p: (
                        self.pair_fill_rates.get(p, 0.5),  # Higher fill rate = better
                        self.pair_performance[p]['total_profit']  # Higher profit = better
                    ),
                    reverse=True
                )
                
                total_orders_placed = 0
                total_orders_filled = 0
                cycle_errors: Dict[str, int] = defaultdict(int)
                # Process each pair
                for pair in pairs_to_process:
                    if not self.running:
                        break
                    
                    result = await self.place_market_making_orders(pair)
                    if isinstance(result, dict):
                        total_orders_placed += result.get('orders_placed', 0)
                        total_orders_filled += result.get('orders_filled', 0)
                        error_key = result.get('error')
                        if error_key:
                            cycle_errors[error_key] += 1
                    await asyncio.sleep(1)  # Small delay between pairs
                total_profit = sum(s.total_profit_usd for s in self.stats.values())
                total_fees = sum(s.total_fees_usd for s in self.stats.values())
                total_net = sum(s.net_profit_usd for s in self.stats.values())
                total_orders = sum(s.total_orders for s in self.stats.values())
                total_filled_orders = sum(s.filled_orders for s in self.stats.values())
                total_wins = sum(s.wins for s in self.stats.values())
                total_losses = sum(s.losses for s in self.stats.values())
                win_denom = total_wins + total_losses
                logger.info("")
                logger.info(f"   🔵 [COINBASE] CYCLE SUMMARY:")
                logger.info(f"      Orders placed this cycle: {total_orders_placed}")
                logger.info(f"      Orders filled this cycle: {total_orders_filled}")
                if cycle_errors:
                    error_breakdown = ", ".join(f"{key}:{count}" for key, count in sorted(cycle_errors.items()))
                    logger.info(f"      Skip reasons this cycle: {error_breakdown}")
                pending_items = sum(len(entries) for entries in self.pending_sell_queue.values())
                if pending_items:
                    pending_details = []
                    for pending_pair, entries in self.pending_sell_queue.items():
                        pair_amount = sum(entry.get('amount', 0.0) for entry in entries)
                        pair_value = sum(
                            entry.get('amount', 0.0) * entry.get('buy_price', 0.0)
                            for entry in entries
                        )
                        pending_details.append(f"{pending_pair}:{pair_amount:.4f} (~${pair_value:.2f})")
                    detail_preview = "; ".join(pending_details[:5])
                    if len(pending_details) > 5:
                        detail_preview += "; ..."
                    logger.info(f"      Pending sell queue: {pending_items} entries [{detail_preview}]")
                active_cooldowns = {
                    pair: reason for pair, (until, reason) in self.pair_cooldowns.items() if until > datetime.now()
                }
                if active_cooldowns:
                    cooldown_summary = ", ".join(
                        f"{pair}({reason})" for pair, reason in sorted(active_cooldowns.items())
                    )
                    logger.info(f"      Active cooldowns: {cooldown_summary}")
                logger.info(f"      Gross profit (all-time): ${total_profit:.2f}")
                logger.info(f"      Fees paid (all-time): ${total_fees:.2f}")
                logger.info(f"      Net profit (all-time): ${total_net:.2f}")
                logger.info(f"      Total orders (all-time): {total_orders}")
                logger.info(f"      Total filled (all-time): {total_filled_orders}")
                logger.info(f"      Wins / Losses: {total_wins} / {total_losses}")
                logger.info(f"      Win rate: {(total_wins / win_denom * 100) if win_denom > 0 else 0:.1f}%")
                logger.info(f"      Engine realized net: ${self.net_profit_usd:.2f}")
                logger.info("=" * 80)
                
                # Wait before next cycle
                await asyncio.sleep(self.requote_interval_seconds)
                
            except Exception as e:
                logger.error(f"   🔵 [COINBASE] Error in market-making loop: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop the market-making engine"""
        self.running = False
        logger.info("   🔵 [COINBASE] Market-making engine stopped")

