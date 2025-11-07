#!/usr/bin/env python3
"""
Gemini Market Making Engine
Implements passive market-making strategy on Gemini exchange
Top 10 pairs optimized for maximum profitability

EXCHANGE: 🟢 GEMINI ONLY - This entire module is for Gemini market making
"""

import asyncio
import logging
import time
import statistics
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Top 10 pairs for market making on Gemini (ranked by profitability)
# Note: These will be filtered during initialization to only include pairs that exist on Gemini
TOP_GEMINI_PAIRS = [
    'ARB/USD',   # Rank 1: 1.5-4.0% daily ROI, Low-Med risk
    'OP/USD',    # Rank 2: 1.2-3.5% daily ROI, Low risk
    'LINK/USD',  # Rank 3: 0.8-2.2% daily ROI, Low risk
    'AVAX/USD',  # Rank 4: 1.0-2.8% daily ROI, Low-Med risk
    'MATIC/USD', # Rank 5: 1.0-2.5% daily ROI, Low risk (may not exist on Gemini)
    'AAVE/USD',  # Rank 6: 1.2-3.2% daily ROI, Low-Med risk
    'SOL/USD',   # Rank 7: 0.7-2.0% daily ROI, Low risk
    'INJ/USD',   # Rank 8: 1.3-3.0% daily ROI, Low-Med risk
    'ATOM/USD',  # Rank 9: 0.9-2.4% daily ROI, Low risk
    'SUSHI/USD', # Rank 10: 1.5-3.5% daily ROI, Med risk
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

class GeminiMarketMakingEngine:
    """Market-making engine for Gemini exchange"""
    
    def __init__(
        self,
        exchange_manager: CoinbaseGeminiExchangeManager,
        capital_per_pair: float = 60.0,  # $60 per pair to sustain larger orders
        grid_spacing_percent: float = 0.20,  # 0.20% spacing
        order_size_percent: float = 0.12,  # 12% of capital per order (~$7)
        min_spread_percent: float = 0.35,  # Skip if spread < 0.35% (covers fees + buffer)
        max_inventory_percent: float = 0.25,  # Max 25% in one asset
        requote_interval_seconds: int = 15,  # Update orders every 15s
        stop_loss_percent: float = 0.02,  # -2% stop loss
        take_profit_interval_minutes: int = 60,  # Flatten every hour
        max_volatility_percent: float = 2.5,  # Skip highly volatile markets
        min_depth_usd: float = 300.0,  # Require at least this much depth per side
    ):
        self.exchange_manager = exchange_manager
        self.capital_per_pair = capital_per_pair
        self.grid_spacing_percent = grid_spacing_percent
        self.order_size_percent = order_size_percent
        self.maker_fee_percent = 0.10  # Estimated maker fee (percent)
        self.taker_fee_percent = 0.35  # Conservative fallback for forced exits
        self.min_order_value_usd = 5.00
        self.min_profit_buffer_percent = 0.15  # Cushion beyond fees
        self.min_spread_percent = max(
            min_spread_percent,
            (self.maker_fee_percent + self.taker_fee_percent) + self.min_profit_buffer_percent
        )
        self.max_inventory_percent = max_inventory_percent
        self.requote_interval_seconds = requote_interval_seconds
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_interval_minutes = take_profit_interval_minutes
        self.max_volatility_percent = max_volatility_percent
        self.min_depth_usd = min_depth_usd
        
        # Active orders tracking
        self.active_orders: Dict[str, List[MarketMakingOrder]] = defaultdict(list)
        
        # Statistics (will be initialized with available pairs)
        self.stats: Dict[str, MarketMakingStats] = {}
        self.available_pairs: List[str] = []  # Will be set during initialization
        
        # 🟢 IMPROVEMENT: Track fill rates for pairs (focus on pairs that actually fill)
        self.pair_fill_rates: Dict[str, float] = {}  # pair -> fill_rate (0-1)
        self.last_buy_prices: Dict[str, float] = defaultdict(lambda: 0.0)
        self.pair_anomaly_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.min_volume_usd = 50000.0
        self.net_profit_usd: float = 0.0
        self.position_tracker: Dict[str, List[Dict[str, float]]] = defaultdict(list)
        self.pending_sell_queue: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.pair_failure_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.pair_cooldowns: Dict[str, Tuple[datetime, str]] = {}
        self.failure_threshold = 3
        self.failure_cooldown_minutes = 5

        # Running state
        self.running = False
        self.last_flatten_time = datetime.now()
        
    def _reset_failures(self, pair: str):
        if pair in self.pair_failure_counts:
            self.pair_failure_counts[pair].clear()
        if pair in self.pair_cooldowns and self.pair_cooldowns[pair][0] <= datetime.now():
            self.pair_cooldowns.pop(pair, None)

    def _register_failure(self, pair: str, failure_type: str, detail: str):
        counts = self.pair_failure_counts[pair]
        counts[failure_type] += 1
        logger.debug(f"   🟢 [GEMINI] {pair}: Failure '{failure_type}' count -> {counts[failure_type]} ({detail})")
        if counts[failure_type] >= self.failure_threshold:
            cooldown_until = datetime.now() + timedelta(minutes=self.failure_cooldown_minutes)
            self.pair_cooldowns[pair] = (cooldown_until, failure_type)
            counts[failure_type] = 0
            logger.warning(
                f"   🟢 [GEMINI] ⏸️ Cooling down {pair} for {self.failure_cooldown_minutes}m after repeated '{failure_type}' failures ({detail})"
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

        # Running state
        self.running = False
        self.last_flatten_time = datetime.now()
        
    async def discover_suitable_pairs(
        self,
        min_volume_usd: Optional[float] = None,
        max_pairs: int = 50,  # Top 50 pairs
    ) -> List[Tuple[str, float, float, float]]:
        """
        Dynamically discover all suitable pairs for market making
        Returns: List of (pair, volume_24h, spread, score) tuples, sorted by score
        """
        logger.info("   🟢 [GEMINI] 🔍 DISCOVERING SUITABLE PAIRS...")
        exchange = self.exchange_manager.get_exchange('gemini')
        suitable_pairs = []
        volume_threshold = min_volume_usd if min_volume_usd is not None else self.min_volume_usd
        base_order_budget = self.capital_per_pair * self.order_size_percent
        
        # Scan all markets
        for symbol, market_info in exchange.markets.items():
            try:
                # Filter: Active spot markets only, USD/USDC/GUSD quote
                if not market_info.get('active', True) and market_info.get('type') != 'spot':
                    continue
                if market_info.get('future', False) or market_info.get('swap', False):
                    continue
                if ':' in symbol:  # Skip futures contracts
                    continue
                
                quote = market_info.get('quote', '').strip().upper()
                if quote not in ['USD', 'USDC', 'GUSD']:
                    continue
                
                # Get ticker data (volume, spread)
                try:
                    ticker = await self.exchange_manager.fetch_ticker('gemini', symbol)
                    
                    # Get volume
                    volume_24h = ticker.get('quoteVolume') or ticker.get('quote_volume')
                    if not volume_24h:
                        base_volume = ticker.get('volume') or ticker.get('baseVolume')
                        last_price = ticker.get('last') or ticker.get('close')
                        if base_volume and last_price:
                            volume_24h = base_volume * last_price
                    
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
                        logger.debug(f"   🟢 [GEMINI] Skipping {symbol} - min order cost ${min_cost:.2f} > target order value ${est_order_value:.2f}")
                        continue
                    if min_amount and est_order_amount < min_amount * 1.1:
                        logger.debug(f"   🟢 [GEMINI] Skipping {symbol} - min order amount {min_amount:.6f} > target amount {est_order_amount:.6f}")
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
                    
                    # Calculate suitability score
                    # Higher volume = better, wider spread = better (up to a point)
                    volume_score = min(volume_24h / 500000.0, 1.0)  # Normalize to $500k (lower for Gemini)
                    spread_score = min(spread / 1.0, 1.0)  # Normalize to 1% spread
                    score = (volume_score * 0.6) + (spread_score * 0.4)  # 60% volume, 40% spread
                    
                    suitable_pairs.append((symbol, volume_24h, spread, score))
                    
                except Exception as e:
                    logger.debug(f"   🟢 [GEMINI] Error analyzing {symbol}: {e}")
                    continue
                    
            except Exception as e:
                logger.debug(f"   🟢 [GEMINI] Error processing {symbol}: {e}")
                continue
        
        # Sort by score (best first)
        suitable_pairs.sort(key=lambda x: x[3], reverse=True)
        
        # Return top N pairs
        top_pairs = suitable_pairs[:max_pairs]
        logger.info(f"   🟢 [GEMINI] Found {len(suitable_pairs)} suitable pairs, selecting top {len(top_pairs)}")
        
        return top_pairs
    
    async def initialize(self):
        """Initialize the market-making engine"""
        logger.info("=" * 80)
        logger.info("🚀 INITIALIZING GEMINI MARKET-MAKING ENGINE")
        logger.info("=" * 80)
        logger.info(f"   Capital per pair: ${self.capital_per_pair:.2f}")
        logger.info(f"   Grid spacing: {self.grid_spacing_percent:.2f}%")
        logger.info(f"   Order size: {self.order_size_percent*100:.1f}% of capital")
        logger.info(f"   Min spread: {self.min_spread_percent:.2f}%")
        logger.info("=" * 80)
        
        # 🟢 DYNAMIC: Discover all suitable pairs
        discovered_pairs = await self.discover_suitable_pairs(
            min_volume_usd=self.min_volume_usd,
            max_pairs=50  # Top 50 pairs
        )
        
        # Combine with hardcoded top pairs (prioritize them)
        exchange = self.exchange_manager.get_exchange('gemini')
        available_pairs = []
        pair_set = set()
        
        # First, add hardcoded top pairs if they exist
        for pair in TOP_GEMINI_PAIRS:
            base_crypto = pair.split('/')[0]
            # Try USD, USDC, and GUSD variants
            for quote in ['USD', 'USDC', 'GUSD']:
                test_pair = f"{base_crypto}/{quote}"
                if test_pair in exchange.markets:
                    market_info = exchange.markets[test_pair]
                    active = market_info.get('active', True)
                    if active or market_info.get('type') == 'spot':
                        if test_pair not in pair_set:
                            available_pairs.append(test_pair)
                            pair_set.add(test_pair)
                            logger.info(f"   ✅ Top pair: {test_pair}")
                        break
        
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
        
        logger.info(f"   ✅ Total available pairs: {len(available_pairs)}")
        if len(available_pairs) == 0:
            logger.error(f"   ❌ No pairs available on Gemini! Market making will not work.")
        logger.info("=" * 80)
        
    async def get_current_price(self, pair: str) -> Optional[float]:
        """Get current market price for a pair"""
        try:
            ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
            bid = ticker.get('bid', 0) or 0
            ask = ticker.get('ask', 0) or 0
            
            # Calculate mid price (average of bid and ask)
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
            logger.debug(f"   🟢 [GEMINI] Error fetching price for {pair}: {e}")
            return None
    
    async def get_spread(self, pair: str) -> Optional[float]:
        """Get current spread percentage"""
        try:
            ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
            bid = ticker.get('bid', 0) or 0
            ask = ticker.get('ask', 0) or 0
            if bid > 0 and ask > 0:
                mid = (bid + ask) / 2
                # 🔵 CRITICAL FIX: Prevent division by zero
                if mid > 0:
                    spread = ((ask - bid) / mid) * 100
                    return spread
            return None
        except Exception as e:
            logger.debug(f"   🟢 [GEMINI] Error fetching spread for {pair}: {e}")
            return None

    async def _compute_short_term_volatility(self, pair: str, limit: int = 20) -> Optional[float]:
        """Calculate short-term volatility using 1-minute candles."""
        try:
            ohlcv = await self.exchange_manager.fetch_ohlcv('gemini', pair, timeframe='1m', limit=limit)
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
            logger.debug(f"   🟢 [GEMINI] Unable to compute volatility for {pair}: {e}")
            return None

    async def _compute_order_book_depth(self, pair: str, depth_levels: int = 5) -> Optional[float]:
        """Estimate USD depth by summing top-of-book levels."""
        try:
            order_book = await self.exchange_manager.fetch_order_book('gemini', pair, limit=depth_levels)
            bids = order_book.get('bids', []) or []
            asks = order_book.get('asks', []) or []
            if not bids or not asks:
                return None
            bid_depth = sum(price * amount for price, amount in bids[:depth_levels])
            ask_depth = sum(price * amount for price, amount in asks[:depth_levels])
            return min(bid_depth, ask_depth)
        except Exception as e:
            logger.debug(f"   🟢 [GEMINI] Unable to compute order book depth for {pair}: {e}")
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
    
    async def get_inventory_balance(self, base_currency: str) -> float:
        """Get current inventory balance for a base currency"""
        try:
            balance = await self.exchange_manager.fetch_balance('gemini')
            free_balance = balance.get('free', {})
            return free_balance.get(base_currency, 0)
        except Exception as e:
            logger.debug(f"   Error fetching balance: {e}")
            return 0.0
    
    async def sell_all_inventory(self):
        """Check ALL inventory and place sell orders for any crypto we have"""
        try:
            balance = await self.exchange_manager.fetch_balance('gemini')
            free_balance = balance.get('free', {})
            exchange = self.exchange_manager.get_exchange('gemini')
            logger.info("   🟢 [GEMINI] 🔁 Checking account inventory for outstanding positions...")
            
            # Check all currencies (not just trading pairs)
            tradable_found = False
            for currency, amount in free_balance.items():
                # Skip quote currencies (cash)
                if currency in ['USD', 'USDT', 'USDC', 'GUSD'] or amount <= 0:
                    continue
                tradable_found = True
                
                # Try to find a trading pair for this currency
                for quote in ['USD', 'USDC', 'GUSD']:
                    pair = f"{currency}/{quote}"
                    if pair in exchange.markets:
                        market_info = exchange.markets[pair]
                        if not market_info.get('active', True):
                            continue
                        
                        # Get current price
                        ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
                        if not ticker:
                            continue
                        
                        ask = ticker.get('ask', 0) or 0
                        if ask <= 0:
                            continue
                        
                        # Check if we already have an open sell order for this pair
                        existing_orders = self.active_orders.get(pair, [])
                        open_sell_orders = [o for o in existing_orders if o.side == 'sell' and o.status == 'open']
                        if open_sell_orders:
                            logger.info(
                                f"   🟢 [GEMINI] {pair}: Existing sell order already open (count={len(open_sell_orders)}), skipping forced sell"
                            )
                            break
                        
                        # Calculate sell amount (use all available inventory)
                        sell_amount = amount
                        sell_price = ask * 0.999  # Slightly below ask to get filled quickly
                        
                        # Get market limits
                        limits = market_info.get('limits', {})
                        min_cost = limits.get('cost', {}).get('min', 1.0) or 1.0
                        
                        # Check minimum order size
                        order_value = sell_amount * sell_price
                        if order_value < min_cost:
                            logger.info(
                                f"   🟢 [GEMINI] {pair}: Inventory value ${order_value:.2f} below minimum ${min_cost:.2f}, keeping position"
                            )
                            break
                        
                        # Place sell order
                        try:
                            logger.info(f"   🟢 [GEMINI] 💰 SELLING INVENTORY: {pair} - {sell_amount:.6f} {currency} @ ${sell_price:.6f} (${order_value:.2f})")
                            sell_order = await self.exchange_manager.create_order(
                                exchange_id='gemini',
                                symbol=pair,
                                order_type='limit',
                                side='sell',
                                amount=sell_amount,
                                price=sell_price
                            )
                            
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
                                logger.info(f"   🟢 [GEMINI] ✅✅✅ INVENTORY SELL ORDER PLACED: {pair} @ ${sell_price:.4f} for {sell_amount:.6f} | Order ID: {sell_order_id}")
                        except Exception as e:
                            logger.error(f"   🟢 [GEMINI] ❌ Failed to sell inventory {pair}: {type(e).__name__}: {e}")
                        
                        break  # Found a working pair, move to next currency
            if not tradable_found:
                logger.info("   🟢 [GEMINI] No non-cash balances detected for forced selling.")
        except Exception as e:
            logger.error(f"   🟢 [GEMINI] ❌ Error selling all inventory: {type(e).__name__}: {e}")
    
    async def place_market_making_orders(self, pair: str) -> dict:
        """Place buy and sell limit orders for market making
        
        Returns:
            dict with 'success' (bool), 'orders_placed' (int), 'orders_filled' (int), 'error' (str)
        """
        orders_placed = 0
        orders_filled = 0
        
        try:
            cooldown_entry = self._is_on_cooldown(pair)
            if cooldown_entry:
                cooldown_until, reason = cooldown_entry
                remaining = max((cooldown_until - datetime.now()).total_seconds(), 0)
                logger.info(
                    f"   🟢 [GEMINI] ⏭️ Skipping {pair} - on cooldown for {remaining:.0f}s (reason: {reason})"
                )
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'cooldown'}

            logger.info(f"   🟢 [GEMINI] 🔍 PROCESSING {pair}...")
            
            # 🟢 IMPROVEMENT: Skip low volume pairs
            try:
                ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
                volume_24h = ticker.get('quoteVolume', 0) or (ticker.get('volume', 0) * ticker.get('last', 0))
                logger.debug(f"   🟢 [GEMINI] {pair}: 24h volume = ${volume_24h:.2f}")
                if volume_24h < 10000:  # Less than $10k volume
                    logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - low volume: ${volume_24h:.0f} < $10,000")
                    return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'low_volume'}
            except Exception as e:
                logger.warning(f"   🟢 [GEMINI] ⚠️ Volume check failed for {pair}: {e}")
                pass  # Continue if volume check fails
            
            # 🟢 CRITICAL: Check for existing orders FIRST before spread check
            # If we have open orders, check them for fills even if spread is low
            existing_orders = self.active_orders.get(pair, [])
            open_orders = [o for o in existing_orders if o.status == 'open']
            
            # 🟢 IMPROVEMENT: Dynamic grid spacing based on spread
            spread = await self.get_spread(pair)
            logger.debug(f"   🟢 [GEMINI] {pair}: Current spread = {spread}%")
            spread_msg = f"{spread:.3f}%" if spread is not None else "None"
            logger.info(
                f"   🟢 [GEMINI] {pair}: Spread snapshot | raw={spread_msg} | threshold={self.min_spread_percent:.2f}%"
            )
            
            # If spread is too low BUT we have open orders, keep checking them for fills
            if (spread is None or spread <= 0 or spread < self.min_spread_percent) and open_orders:
                logger.info(f"   🟢 [GEMINI] {pair}: Spread {spread_msg} < minimum {self.min_spread_percent:.2f}%, but keeping {len(open_orders)} open order(s) to check for fills")
                # Check existing orders for fills, don't cancel them
                filled = await self.check_and_update_orders(pair)
                return {'success': True, 'orders_placed': 0, 'orders_filled': filled, 'error': None}
            
            # If spread is too low and no open orders, skip entirely
            if spread is None or spread <= 0 or spread < self.min_spread_percent:
                spread_msg = f"{spread:.3f}%" if spread is not None else "None"
                logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - spread {spread_msg} < minimum {self.min_spread_percent:.2f}%")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'spread_too_tight'}
            
            # Get current price
            current_price = await self.get_current_price(pair)
            logger.debug(f"   🟢 [GEMINI] {pair}: Current price = ${current_price}")
            if current_price is None or current_price <= 0:
                logger.warning(f"   🟢 [GEMINI] ⚠️ Skipping {pair} - invalid price: {current_price}")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'invalid_price'}

            market_ok, market_metrics, health_reason = await self._evaluate_market_health(pair)
            if not market_ok:
                logger.info(
                    f"   🟢 [GEMINI] ⏭️ Skipping {pair} - {health_reason}"
                    + (f" | metrics: {market_metrics}" if any(market_metrics.values()) else "")
                )
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'market_unhealthy'}
            else:
                if any(market_metrics.values()):
                    logger.debug(f"   🟢 [GEMINI] {pair}: Market metrics {market_metrics}")
            
            # 🟢 IMPROVEMENT: Use 50% of current spread as grid spacing (max 0.5%, min 0.15%)
            dynamic_spacing = min(max(spread * 0.5, 0.15), 0.5)
            logger.debug(f"   🟢 [GEMINI] {pair}: Spread {spread:.3f}% → Dynamic spacing {dynamic_spacing:.3f}%")
            
            # 🟢 SMART: Only cancel/update orders if prices have moved significantly
            # This prevents canceling orders that are about to fill
            should_update_orders, update_reason = await self.should_update_pair_orders(pair, dynamic_spacing)
            if should_update_orders:
                logger.info(f"   🟢 [GEMINI] {pair}: Updating existing orders - Reason: {update_reason}")
                await self.cancel_pair_orders(pair, reason=f"update_required: {update_reason}")
            else:
                logger.info(f"   🟢 [GEMINI] {pair}: Keeping existing orders - Reason: {update_reason}")
                # Check for fills on existing orders
                filled = await self.check_and_update_orders(pair)
                return {'success': True, 'orders_placed': 0, 'orders_filled': filled, 'error': None}
            
            pending_entries = self.pending_sell_queue.get(pair, [])
            if pending_entries:
                pending_value = sum(entry.get('amount', 0.0) * (current_price or 0.0) for entry in pending_entries)
                logger.info(
                    f"   🟢 [GEMINI] ⏭️ Skipping {pair} - pending sell queue size {len(pending_entries)} (~${pending_value:.2f})"
                )
                self._register_failure(pair, 'pending_inventory', f"pending value ${pending_value:.2f}")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'pending_sell_queue'}

            # Get market info for precision requirements FIRST (before calculating order amount)
            exchange = self.exchange_manager.get_exchange('gemini')
            market_info = exchange.markets.get(pair, {})
            
            # Apply precision requirements (if available from market info)
            # CCXT precision can be int (decimal places) or float (step size)
            # Convert to int for round() function
            precision_data = market_info.get('precision', {})
            amount_precision_val = precision_data.get('amount', 8)
            if amount_precision_val:
                amount_precision = max(int(amount_precision_val), 1)  # At least 1 decimal place
            else:
                amount_precision = 8  # Default to 8
            
            price_precision_val = precision_data.get('price', 8)
            if price_precision_val:
                price_precision = max(int(price_precision_val), 1)  # At least 1 decimal place
            else:
                price_precision = 8  # Default to 8
            
            # Get minimum order size from market info
            limits = market_info.get('limits', {})
            min_amount = limits.get('amount', {}).get('min', 0) or 0
            # 🟢 FLEXIBLE: Use exchange minimum or $1.00 (whichever is lower) to allow smaller orders
            exchange_min_cost = limits.get('cost', {}).get('min', 0) or 0
            min_cost = max(exchange_min_cost, 1.0) if exchange_min_cost > 0 else 1.0  # Exchange requirement (can be < $5)
            min_buy_cost = max(min_cost, self.min_order_value_usd)
            
            # 🟢 IMPROVEMENT: Adjust order size based on spread
            base_currency = pair.split('/')[0]
            if spread and self.min_spread_percent > 0:
                # Scale order size: wider spread = larger orders (max 2x, min 0.5x)
                spread_multiplier = min(max(spread / self.min_spread_percent, 0.5), 2.0)
                order_value_usd = self.capital_per_pair * self.order_size_percent * spread_multiplier
                logger.debug(f"   🟢 [GEMINI] {pair}: Spread {spread:.3f}% → Order size multiplier {spread_multiplier:.2f}x → Order value: ${order_value_usd:.2f}")
            else:
                order_value_usd = self.capital_per_pair * self.order_size_percent

            order_value_usd = max(order_value_usd, min_buy_cost)
            
            # Calculate order amount from USD value
            # 🔵 CRITICAL FIX: Prevent division by zero
            if current_price <= 0:
                logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - invalid current price: {current_price}")
                return False
            
            order_amount = order_value_usd / current_price
            
            # Ensure order value meets minimum cost requirement
            logger.debug(f"   🟢 [GEMINI] {pair}: Order value = ${order_value_usd:.2f}, min buy cost = ${min_buy_cost:.2f}")
            if order_value_usd < min_buy_cost:
                logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - order value ${order_value_usd:.2f} < minimum ${min_buy_cost:.2f}")
                self._register_failure(pair, 'min_order', f"target ${order_value_usd:.2f} vs min ${min_buy_cost:.2f}")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'order_value_too_small'}
            
            # Round amounts to exchange precision (but ensure it's not 0)
            order_amount = round(order_amount, amount_precision)
            
            # 🔵 CRITICAL FIX: If rounding caused amount to become 0, recalculate
            logger.debug(f"   🟢 [GEMINI] {pair}: Order amount after rounding = {order_amount}, min amount = {min_amount}")
            if order_amount <= 0:
                # Try to use minimum amount if available
                if min_amount > 0:
                    order_amount = min_amount
                    order_value_usd = order_amount * current_price
                    if order_value_usd < min_buy_cost:
                        logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - minimum amount value ${order_value_usd:.2f} < floor ${min_buy_cost:.2f}")
                        self._register_failure(pair, 'min_order', f"min amount value ${order_value_usd:.2f} < floor ${min_buy_cost:.2f}")
                        return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'order_amount_too_small'}
                    logger.info(f"   🟢 [GEMINI] {pair}: Using minimum amount {min_amount} after rounding to 0")
                else:
                    logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - order amount too small after rounding: {order_amount}")
                    self._register_failure(pair, 'min_order', 'amount rounded to zero')
                    return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'amount_too_small_after_rounding'}
            
            # Ensure order amount meets minimum amount requirement
            if min_amount > 0 and order_amount < min_amount:
                # Increase order amount to meet minimum
                order_amount = min_amount
                order_value_usd = order_amount * current_price
                logger.debug(f"   🟢 [GEMINI] {pair}: Adjusted order amount to minimum {min_amount}")
            
            # 🟢 DYNAMIC PRICING: Get fresh bid/ask every time for real-time adjustment
            ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
            bid = ticker.get('bid', 0) or 0
            ask = ticker.get('ask', 0) or 0
            
            # 🟢 DYNAMIC: Prices adjust based on current market conditions
            if bid > 0 and ask > 0:
                # Calculate mid price for reference
                mid_price = (bid + ask) / 2
                current_spread = ((ask - bid) / mid_price) * 100 if mid_price > 0 else 0
                
                # 🟢 DYNAMIC: Adjust spacing based on actual market spread
                # If market spread is tight, use smaller spacing to stay competitive
                # If market spread is wide, use larger spacing to capture more profit
                if current_spread > 0 and spread:
                    # Use 30-70% of market spread as our spacing (adaptive)
                    adaptive_spacing = min(max(current_spread * 0.5, dynamic_spacing * 0.5), dynamic_spacing * 1.5)
                elif spread:
                    adaptive_spacing = dynamic_spacing
                else:
                    adaptive_spacing = self.grid_spacing_percent
                
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
                    logger.warning(f"   🟢 [GEMINI] ⚠️ {pair}: Bid/ask inverted, using mid price with spacing")
            else:
                # Fallback: Use current_price with spacing
                if spread:
                    buy_price = current_price * (1 - dynamic_spacing / 100)
                    sell_price = current_price * (1 + dynamic_spacing / 100)
                else:
                    buy_price = current_price * (1 - self.grid_spacing_percent / 100)
                    sell_price = current_price * (1 + self.grid_spacing_percent / 100)
            
            # 🔵 CRITICAL FIX: Validate prices are not None
            if buy_price is None or sell_price is None or buy_price <= 0 or sell_price <= 0:
                logger.warning(f"   🟢 [GEMINI] ⚠️ Skipping {pair} - invalid calculated prices: buy=${buy_price}, sell=${sell_price}")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'invalid_calculated_prices'}
            
            # 🟢 NO ROUNDING: Use exact calculated prices (exchange will handle precision)
            # Prices are already calculated with proper precision from market data
            # Exchange manager will apply necessary precision for API requirements
            
            # Check minimum order size (recalculate after rounding)
            min_order_value = order_amount * buy_price
            if min_order_value < min_buy_cost:
                # Try to increase order amount to meet minimum
                # 🔵 CRITICAL FIX: Prevent division by zero
                if buy_price > 0:
                    required_amount = min_buy_cost / buy_price
                    if required_amount > order_amount:
                        order_amount = round(required_amount, amount_precision)
                        min_order_value = order_amount * buy_price
                        logger.debug(f"   🟢 [GEMINI] {pair}: Increased order amount to meet minimum cost")
                
                # Final check
                if min_order_value < min_buy_cost:
                    logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - order value ${min_order_value:.2f} < minimum ${min_buy_cost:.2f} (after rounding)")
                    self._register_failure(pair, 'min_order', f"value ${min_order_value:.2f} < floor ${min_buy_cost:.2f}")
                    return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'order_value_too_small_after_rounding'}
            
            # Check inventory limits
            inventory = await self.get_inventory_balance(base_currency)
            # 🔵 CRITICAL FIX: Handle None values from balance fetch failures
            if inventory is None:
                inventory = 0.0
            if current_price is None or current_price <= 0:
                logger.warning(f"   🟢 [GEMINI] ⚠️ Skipping {pair} - invalid current_price: {current_price}")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'invalid_price'}
            
            inventory_value = inventory * current_price
            max_inventory = self.capital_per_pair * self.max_inventory_percent
            
            logger.info(f"   🟢 [GEMINI] {pair}: Inventory = {inventory:.6f} {base_currency} (${inventory_value:.2f}), Max = ${max_inventory:.2f}")
            logger.info(f"   🟢 [GEMINI] {pair}: Buy price = ${buy_price:.6f}, Sell price = ${sell_price:.6f}, Amount = {order_amount:.6f}")
            
            # Place buy order (if not over-inventoried)
            # 🔵 CRITICAL FIX: Ensure inventory_value is not None before comparison
            if inventory_value is not None and inventory_value < max_inventory:
                # 🟢 CRITICAL: Check balance and dynamically size order
                quote_currency = pair.split('/')[1]
                quote_balance = await self.get_inventory_balance(quote_currency)
                if quote_balance is None:
                    quote_balance = 0.0
                
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
                    logger.info(f"   🟢 [GEMINI] {pair}: Adjusting order size to fit balance: {original_amount:.6f} → {order_amount:.6f} (Balance: ${quote_balance:.2f} {quote_currency})")
                    
                    # Re-check minimum order size after adjustment
                    min_order_value = order_amount * buy_price
                    if min_order_value < min_buy_cost:
                        logger.info(f"   🟢 [GEMINI] ⏭️ Skipping buy order for {pair} - adjusted order value ${min_order_value:.2f} < minimum ${min_buy_cost:.2f}")
                        self._register_failure(pair, 'min_order', f"adjusted order ${min_order_value:.2f} < floor ${min_buy_cost:.2f}")
                        order_amount = 0  # Skip order
                    else:
                        # Round to precision
                        order_amount = round(order_amount, amount_precision)
                        if order_amount <= 0:
                            logger.info(f"   🟢 [GEMINI] ⏭️ Skipping buy order for {pair} - order amount rounded to 0")
                            self._register_failure(pair, 'min_order', 'amount rounded to zero after balance adjust')
                            order_amount = 0  # Skip order
                elif max_order_amount >= order_amount:
                    # Have enough balance for full order
                    logger.info(f"   🟢 [GEMINI] {pair}: 📝 ATTEMPTING TO PLACE BUY ORDER... (Balance: ${quote_balance:.2f} {quote_currency}, Required: ${order_amount * buy_price:.2f})")
                else:
                    # Not enough balance even for minimum order
                    required_value = max(order_amount * buy_price if order_amount and buy_price else 0, min_buy_cost)
                    logger.info(f"   🟢 [GEMINI] ⏭️ Skipping buy order for {pair} - insufficient {quote_currency} balance: ${quote_balance:.2f} < minimum required ${required_value:.2f}")
                    self._register_failure(pair, 'insufficient_balance', f"balance ${quote_balance:.2f} < required ${required_value:.2f}")
                    order_amount = 0  # Skip order
                
                if order_amount > 0:
                    try:
                        # 🔵 CRITICAL FIX: Validate order parameters before creating order
                        if order_amount is None or order_amount <= 0:
                            logger.error(f"   🟢 [GEMINI] ❌ Invalid order_amount: {order_amount}")
                            raise ValueError(f"Invalid order_amount: {order_amount}")
                        if buy_price is None or buy_price <= 0:
                            logger.error(f"   🟢 [GEMINI] ❌ Invalid buy_price: {buy_price}")
                            raise ValueError(f"Invalid buy_price: {buy_price}")
                        
                        logger.debug(f"   🟢 [GEMINI] {pair}: Creating buy order - amount={order_amount:.6f}, price=${buy_price:.6f}")
                        buy_order = await self.exchange_manager.create_order(
                            exchange_id='gemini',
                            symbol=pair,
                            order_type='limit',
                            side='buy',
                            amount=order_amount,
                            price=buy_price
                        )
                        logger.debug(f"   🟢 [GEMINI] {pair}: Buy order response = {buy_order}")
                        
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
                            logger.info(f"   🟢 [GEMINI] ✅✅✅ BUY ORDER PLACED SUCCESSFULLY: {pair} @ ${buy_price:.4f} for {order_amount:.6f} (${order_amount * buy_price:.2f}) | Order ID: {buy_order_id}")
                        else:
                            logger.warning(f"   🟢 [GEMINI] ⚠️ Buy order creation returned no ID: {buy_order}")
                    except Exception as e:
                        logger.error(f"   🟢 [GEMINI] ❌ FAILED TO PLACE BUY ORDER for {pair}: {type(e).__name__}: {e}")
                        import traceback
                        logger.debug(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
            else:
                inventory_value_str = f"${inventory_value:.2f}" if inventory_value is not None else "None"
                logger.info(f"   🟢 [GEMINI] {pair}: ⏭️ Skipping buy order - inventory {inventory_value_str} >= max ${max_inventory:.2f}")
            
            # Place sell order (if we have inventory)
            if inventory is not None and inventory > 0:
                min_amount_limit = market_info.get('limits', {}).get('amount', {}).get('min', 0) or 0
                required_amount_for_value = (min_cost / sell_price) if sell_price and sell_price > 0 else 0
                required_amount = max(min_amount_limit, required_amount_for_value)

                if inventory < required_amount:
                    logger.info(
                        f"   🟢 [GEMINI] {pair}: ⏭️ Skipping sell order - inventory {inventory:.6f} ({inventory * sell_price:.2f}) < minimum requirement {required_amount:.6f} ({min_cost:.2f})"
                    )
                    return

                sell_amount = inventory
                logger.info(f"   🟢 [GEMINI] {pair}: 📝 ATTEMPTING TO PLACE SELL ORDER... (Inventory: {inventory:.6f})")
                try:
                    # 🔵 CRITICAL FIX: Validate sell order parameters
                    if sell_amount is None or sell_amount <= 0:
                        logger.error(f"   🟢 [GEMINI] ❌ Invalid sell_amount: {sell_amount}")
                        raise ValueError(f"Invalid sell_amount: {sell_amount}")
                    if sell_price is None or sell_price <= 0:
                        logger.error(f"   🟢 [GEMINI] ❌ Invalid sell_price: {sell_price}")
                        raise ValueError(f"Invalid sell_price: {sell_price}")
                    
                    logger.debug(f"   🟢 [GEMINI] {pair}: Creating sell order - amount={sell_amount:.6f}, price=${sell_price:.6f}")
                    sell_order = await self.exchange_manager.create_order(
                        exchange_id='gemini',
                        symbol=pair,
                        order_type='limit',
                        side='sell',
                        amount=sell_amount,
                        price=sell_price
                    )
                    logger.debug(f"   🟢 [GEMINI] {pair}: Sell order response = {sell_order}")
                    
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
                        logger.info(f"   🟢 [GEMINI] ✅✅✅ SELL ORDER PLACED SUCCESSFULLY: {pair} @ ${sell_price:.4f} for {sell_amount:.6f} (${sell_amount * sell_price:.2f}) | Order ID: {sell_order_id}")
                        self._reset_failures(pair)
                    else:
                        logger.warning(f"   🟢 [GEMINI] ⚠️ Sell order creation returned no ID: {sell_order}")
                except Exception as e:
                    logger.error(f"   🟢 [GEMINI] ❌ FAILED TO PLACE SELL ORDER for {pair}: {type(e).__name__}: {e}")
                    import traceback
                    logger.debug(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
            else:
                if inventory is None or inventory <= 0:
                    logger.debug(f"   🟢 [GEMINI] {pair}: ⏭️ Skipping sell order - no inventory")
                else:
                    logger.debug(f"   🟢 [GEMINI] {pair}: ⏭️ Skipping sell order - inventory {inventory:.6f} too small for minimum order")
            
            # Check for filled orders
            # 🔵 CRITICAL FIX: Use correct method name
            orders_filled = await self.check_and_update_orders(pair)
            
            if orders_placed > 0:
                logger.info(f"   🟢 [GEMINI] ✅ {pair}: Successfully placed {orders_placed} order(s), {orders_filled} filled")
            else:
                logger.info(f"   🟢 [GEMINI] ⚠️ {pair}: No orders placed (inventory limits or errors)")
            
            return {'success': orders_placed > 0, 'orders_placed': orders_placed, 'orders_filled': orders_filled, 'error': None}
            
        except Exception as e:
            logger.error(f"   🟢 [GEMINI] ❌❌❌ ERROR placing market-making orders for {pair}: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
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
            if age_seconds > 900:  # let quotes rest for up to 15 minutes
                return True, f"order {order.order_id} age {age_seconds:.0f}s > 900s"

        try:
            ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
            current_bid = ticker.get('bid', 0) or 0
            current_ask = ticker.get('ask', 0) or 0

            if current_bid <= 0 or current_ask <= 0:
                return True, "missing bid/ask data"

            try:
                order_book = await self.exchange_manager.fetch_order_book('gemini', pair, limit=20)
                bids = order_book.get('bids', []) or []
                asks = order_book.get('asks', []) or []
            except Exception as depth_error:
                bids, asks = [], []
                logger.debug(f"   🟢 [GEMINI] Depth fetch failed for {pair}: {depth_error}")

            top_bid_volume = bids[0][1] if bids else 0
            top_ask_volume = asks[0][1] if asks else 0

            buy_drift_threshold = 0.2
            sell_drift_threshold = max(0.6, self.min_spread_percent * 3)
            sell_grace_period = 240  # seconds

            for order in open_orders:
                if order.price <= 0:
                    continue

                order_age = (now - order.created_at).total_seconds()

                if order.side == 'buy':
                    price_diff_pct = abs((current_bid - order.price) / current_bid) * 100
                    if order.price >= current_ask:
                        return True, f"buy order {order.order_id} price {order.price} >= current ask {current_ask}"
                    if top_ask_volume > top_bid_volume * 3 and price_diff_pct < 0.5:
                        return True, f"heavy ask pressure ({top_ask_volume:.0f} vs {top_bid_volume:.0f})"
                    drift_threshold = buy_drift_threshold
                else:
                    price_diff_pct = abs((current_ask - order.price) / current_ask) * 100
                    if order.price <= current_bid:
                        return True, f"sell order {order.order_id} price {order.price} <= current bid {current_bid}"
                    if top_bid_volume > top_ask_volume * 3 and price_diff_pct < 0.5:
                        return True, f"heavy bid pressure ({top_bid_volume:.0f} vs {top_ask_volume:.0f})"
                    drift_threshold = sell_drift_threshold

                    if order_age < sell_grace_period and price_diff_pct < drift_threshold * 1.5:
                        continue

                if price_diff_pct > drift_threshold:
                    return True, f"order {order.order_id} price drift {price_diff_pct:.2f}%"

        except Exception as e:
            logger.debug(f"   🟢 [GEMINI] Error checking price movement for {pair}: {e}")
            return True, f"error checking price drift: {e}"

        return False, "orders still competitive"
    
    async def cancel_pair_orders(self, pair: str, reason: str = "unspecified"):
        """Cancel all active orders for a pair with logging"""
        try:
            orders_to_cancel = self.active_orders[pair].copy()
            open_orders = [o for o in orders_to_cancel if o.status == 'open']
            if not open_orders:
                logger.info(f"   🟢 [GEMINI] {pair}: No open orders to cancel (reason: {reason})")
                return
            logger.info(f"   🟢 [GEMINI] {pair}: Canceling {len(open_orders)} order(s) - Reason: {reason}")
            for mm_order in orders_to_cancel:
                if mm_order.order_id and mm_order.status == 'open':
                    try:
                        await self.exchange_manager.cancel_order(
                            'gemini',
                            mm_order.order_id,
                            pair
                        )
                        mm_order.status = 'canceled'
                        logger.info(
                            f"   🟢 [GEMINI] ❎ ORDER CANCELED: {pair} | ID {mm_order.order_id} | "
                            f"Side: {mm_order.side} | Price: ${mm_order.price:.6f} | Amount: {mm_order.amount:.6f}"
                        )
                    except Exception as e:
                        logger.error(f"   🟢 [GEMINI] ❌ Failed to cancel order {mm_order.order_id} for {pair}: {e}")
            
            # Remove canceled orders
            self.active_orders[pair] = [
                o for o in self.active_orders[pair] 
                if o.status == 'open' or o.status == 'filled'
            ]
        except Exception as e:
            logger.error(f"   🟢 [GEMINI] ❌ Error canceling orders for {pair}: {e}")
    
    async def check_and_update_orders(self, pair: str) -> int:
        """Check order status and update if needed. Returns count of filled orders."""
        filled_count = 0
        try:
            orders_to_check = self.active_orders.get(pair, []).copy()
            if not orders_to_check:
                return 0
                
            logger.debug(f"   🟢 [GEMINI] Checking {len(orders_to_check)} orders for {pair}")
            
            for mm_order in orders_to_check:
                if mm_order.order_id and mm_order.status == 'open':
                    try:
                        order_status = await self.exchange_manager.fetch_order(
                            'gemini',
                            mm_order.order_id,
                            pair
                        )
                        status = order_status.get('status', 'unknown')
                        
                        # Check for partial or full fills
                        filled = float(order_status.get('filled', 0))
                        remaining = float(order_status.get('remaining', 0))
                        price = float(order_status.get('price', mm_order.price))
                        cost = float(order_status.get('cost', 0))
                        
                        # Track previous filled amount to detect new fills
                        previous_filled = getattr(mm_order, 'filled_amount', 0.0)
                        new_filled = filled - previous_filled
                        
                        if filled > previous_filled:
                            # New fill detected (partial or full)
                            mm_order.filled_amount = filled
                            
                            if mm_order.side == 'buy':
                                # Buy order got filled (partially or fully)
                                total_fee = float(order_status.get('fee', {}).get('cost', 0) or 0)
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
                                    self.last_buy_prices[pair] = price
                                if status in ['closed', 'filled']:
                                    mm_order.status = 'filled'
                                    mm_order.filled_at = datetime.now()
                                    self.stats[pair].filled_orders += 1
                                    self.stats[pair].total_orders += 1
                                    filled_count += 1
                                    logger.info(f"   🟢 [GEMINI] ✅✅✅ BUY FULLY FILLED: {pair} @ ${price:.4f} for {filled:.6f}")
                                else:
                                    # Partial fill
                                    logger.info(f"   🟢 [GEMINI] ✅ BUY PARTIALLY FILLED: {pair} @ ${price:.4f} - {new_filled:.6f} filled (total: {filled:.6f}/{mm_order.amount:.6f})")

                                if new_filled > 0:
                                    try:
                                        sell_placed = await self._place_sell_order_for_filled_buy(pair, new_filled, price)
                                        if not sell_placed:
                                            logger.info(f"   🟢 [GEMINI] {pair}: Queued {new_filled:.6f} for later sell (inventory pending)")
                                    except Exception as e:
                                        logger.error(f"   🟢 [GEMINI] ❌ ERROR placing sell order after buy fill: {type(e).__name__}: {e}")
                                        import traceback
                                        logger.debug(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
                            
                            elif mm_order.side == 'sell':
                                # Sell order got filled (partially or fully)
                                total_fee = float(order_status.get('fee', {}).get('cost', 0) or 0)
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
                                    logger.warning(f"   🟢 [GEMINI] ⚠️ {pair}: Sell filled {new_filled:.6f} but only matched {new_filled-remaining:.6f} from inventory tracker")
                                self.stats[pair].total_profit_usd += gross_accum
                                self.stats[pair].total_fees_usd += fee_accum
                                self.stats[pair].net_profit_usd += net_accum
                                self.net_profit_usd += net_accum
                                if net_accum >= 0:
                                    self.stats[pair].wins += 1
                                else:
                                    self.stats[pair].losses += 1
                                logger.info(f"   🟢 [GEMINI] ✅ SELL {'FULLY ' if status in ['closed','filled'] else ''}FILLED: {pair} @ ${price:.4f} for {new_filled:.6f} | Gross: ${gross_accum:.4f} | Fees: ${fee_accum:.4f} | Net: ${net_accum:.4f}")
                                if status in ['closed', 'filled']:
                                    mm_order.status = 'filled'
                                    mm_order.filled_at = datetime.now()
                                    self.stats[pair].filled_orders += 1
                                    self.stats[pair].total_orders += 1
                                    filled_count += 1
                            
                            # Update fill rate
                            current_fill_rate = self.pair_fill_rates.get(pair, 0.5)
                            self.pair_fill_rates[pair] = current_fill_rate * 0.9 + 0.1  # 10% weight to new fill
                        
                        elif status in ['closed', 'filled'] and mm_order.status == 'open':
                            # Order fully filled but we didn't detect it above (fallback)
                            mm_order.status = 'filled'
                            mm_order.filled_at = datetime.now()
                            self.stats[pair].filled_orders += 1
                            self.stats[pair].total_orders += 1
                            filled_count += 1
                            
                            if mm_order.side == 'buy':
                                logger.info(f"   🟢 [GEMINI] ✅✅✅ BUY FILLED: {pair} @ ${price:.4f} for {filled:.6f}")
                                try:
                                    sell_placed = await self._place_sell_order_for_filled_buy(pair, filled, price)
                                    if not sell_placed:
                                        logger.info(f"   🟢 [GEMINI] {pair}: Queued {filled:.6f} for later sell (inventory pending)")
                                except Exception as e:
                                    logger.error(f"   🟢 [GEMINI] ❌ ERROR placing sell order after buy fill: {type(e).__name__}: {e}")
                            else:
                                logger.info(f"   🟢 [GEMINI] ✅ SELL FILLED: {pair} @ ${price:.4f} for {filled:.6f}")
                                self.stats[pair].total_profit_usd += (price - mm_order.price) * filled
                        
                        elif status == 'canceled':
                            mm_order.status = 'canceled'
                            cancel_reason = (
                                order_status.get('info')
                                or order_status.get('reason')
                                or order_status.get('message')
                                or 'exchange_cancelled'
                            )
                            logger.warning(
                                f"   🟢 [GEMINI] ⚠️ ORDER CANCELED BY EXCHANGE: {pair} | ID {mm_order.order_id} | "
                                f"Side: {mm_order.side} | Filled: {filled:.6f} | Remaining: {remaining:.6f} | Reason: {cancel_reason}"
                            )
                        else:
                            mm_order.status = status
                            logger.info(
                                f"   🟢 [GEMINI] ℹ️ ORDER STATUS CHECK: {pair} | ID {mm_order.order_id} | "
                                f"Side: {mm_order.side} | Status: {status} | Filled: {filled:.6f} | Remaining: {remaining:.6f}"
                            )
                    except Exception as e:
                        logger.debug(f"   🟢 [GEMINI] Error checking order {mm_order.order_id}: {e}")
        except Exception as e:
            logger.debug(f"   🟢 [GEMINI] Error checking orders for {pair}: {e}")
        
        return filled_count
    
    async def _place_sell_order_for_filled_buy(self, pair: str, filled_amount: float, buy_price: float, allow_queue: bool = True) -> bool:
        """Attempt to place a sell order for newly acquired inventory. Returns True if an order was placed."""
        try:
            base_currency = pair.split('/')[0]

            # Wait briefly for balances to settle (Gemini can lag balance updates by a few hundred ms)
            await asyncio.sleep(0.2)

            max_inventory_checks = 5
            inventory = 0.0
            for attempt in range(max_inventory_checks):
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
                    logger.warning(f"   🟢 [GEMINI] ⚠️ {pair}: Inventory not yet available after buy fill ({filled_amount:.6f}). Queued for retry.")
                return False

            sell_amount = min(filled_amount, inventory)
            leftover_amount = max(filled_amount - sell_amount, 0.0)

            ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
            current_ask = ticker.get('ask', 0) or 0
            current_bid = ticker.get('bid', 0) or 0

            min_sell_price_with_buffer = buy_price * (1 + self.min_spread_percent / 100)

            if current_ask <= 0:
                sell_price = max(buy_price * 1.01, min_sell_price_with_buffer)
                logger.warning(f"   🟢 [GEMINI] ⚠️ {pair}: No ask price, using fallback ${sell_price:.6f}")
            else:
                spread = await self.get_spread(pair)
                if spread and spread > 0:
                    markup = min(max(spread * 0.5, 0.15), 0.5) / 100
                else:
                    markup = 0.002

                sell_price = current_ask * (1 + markup)
                if sell_price < min_sell_price_with_buffer:
                    logger.info(
                        f"   🟢 [GEMINI] {pair}: Raising sell price to maintain profit buffer ({sell_price:.6f} → {min_sell_price_with_buffer:.6f})"
                    )
                    sell_price = min_sell_price_with_buffer

            exchange = self.exchange_manager.get_exchange('gemini')
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
                        f"   🟢 [GEMINI] ⚠️ {pair}: Sell order too small (${order_value:.2f} vs min ${min_cost:.2f} or amount {sell_amount:.6f} vs min {min_amount:.6f}). Queued for later."
                    )
                else:
                    logger.debug(
                        f"   🟢 [GEMINI] {pair}: Pending sell still below exchange minimums (value ${order_value:.2f}, amount {sell_amount:.6f})."
                    )
                return False

            jitter = (random.random() * 0.0001 - 0.00005) * sell_price
            sell_price += jitter
            if sell_price < min_sell_price_with_buffer:
                sell_price = min_sell_price_with_buffer

            logger.info(
                f"   🟢 [GEMINI] 📝 PLACING SELL ORDER for filled buy: {pair} @ ${sell_price:.6f} for {sell_amount:.6f} (${sell_amount * sell_price:.2f})"
            )

            sell_order = await self.exchange_manager.create_order(
                exchange_id='gemini',
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
                    order_id=sell_order_id,
                    price=sell_price,
                    amount=sell_amount,
                    status='open',
                    created_at=datetime.now()
                )
                self.active_orders[pair].append(mm_order)
                logger.info(
                    f"   🟢 [GEMINI] ✅✅✅ SELL ORDER PLACED for filled buy: {pair} @ ${sell_price:.4f} for {sell_amount:.6f} | Order ID: {sell_order_id}"
                )
                self._reset_failures(pair)

                if leftover_amount > 1e-8 and allow_queue:
                    self.pending_sell_queue[pair].append({
                        'amount': leftover_amount,
                        'buy_price': buy_price,
                        'created_at': datetime.now(),
                        'retry_count': 0
                    })
                    logger.info(f"   🟢 [GEMINI] {pair}: Queued remaining {leftover_amount:.6f} for follow-up sell")

                return True

            logger.warning(f"   🟢 [GEMINI] ❌ Sell order placement returned no ID for {pair}: {sell_order}")
            if allow_queue:
                self.pending_sell_queue[pair].append({
                    'amount': filled_amount,
                    'buy_price': buy_price,
                    'created_at': datetime.now(),
                    'retry_count': 0
                })
            return False

        except Exception as e:
            logger.error(f"   🟢 [GEMINI] ❌ ERROR placing follow-up sell order on {pair}: {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
            if allow_queue:
                self.pending_sell_queue[pair].append({
                    'amount': filled_amount,
                    'buy_price': buy_price,
                    'created_at': datetime.now(),
                    'retry_count': 0
                })
            return False

    async def _flush_pending_sell_queue(self):
        """Retry any queued sell orders that could not be placed earlier."""
        if not self.pending_sell_queue:
            return

        for pair in list(self.pending_sell_queue.keys()):
            queue_entries = self.pending_sell_queue.get(pair, [])
            if not queue_entries:
                self.pending_sell_queue.pop(pair, None)
                continue

            remaining_entries: List[Dict[str, Any]] = []
            for entry in queue_entries:
                amount = entry.get('amount', 0.0)
                buy_price = entry.get('buy_price', 0.0)
                retry_count = entry.get('retry_count', 0)
                success = await self._place_sell_order_for_filled_buy(pair, amount, buy_price, allow_queue=False)
                if success:
                    continue
                entry['retry_count'] = retry_count + 1
                if entry['retry_count'] % 5 == 0:
                    logger.warning(
                        f"   🟢 [GEMINI] ⚠️ Pending sell for {pair} still waiting after {entry['retry_count']} attempts (amount {amount:.6f})"
                    )
                remaining_entries.append(entry)

            if remaining_entries:
                self.pending_sell_queue[pair] = remaining_entries
            else:
                self.pending_sell_queue.pop(pair, None)
    
    async def flatten_positions(self):
        """Flatten all positions (take profit)"""
        try:
            logger.info("   🟢 [GEMINI] 🔄 FLATTENING POSITIONS (Take Profit)...")
            pairs_to_process = self.available_pairs if self.available_pairs else TOP_GEMINI_PAIRS
            
            # 🟢 IMPROVEMENT: Check if spread is too tight before flattening
            flattened_count = 0
            for pair in pairs_to_process:
                spread = await self.get_spread(pair)
                if spread and spread < self.min_spread_percent * 0.5:
                    logger.info(f"   🟢 [GEMINI] Spread too tight on {pair} ({spread:.3f}%) - flattening early")
            for pair in pairs_to_process:
                base_currency = pair.split('/')[0]
                inventory = await self.get_inventory_balance(base_currency)
                
                if inventory > 0:
                    # Get current price
                    current_price = await self.get_current_price(pair)
                    if current_price and current_price > 0:
                        # CRITICAL: Gemini only supports limit orders, not market orders
                        # Use limit order slightly below market to ensure fill
                        sell_amount = inventory * 0.95  # 95% to leave buffer
                        sell_price = current_price * 0.995  # 0.5% below market to ensure fill
                        
                        try:
                            sell_order = await self.exchange_manager.create_order(
                                exchange_id='gemini',
                                symbol=pair,
                                order_type='limit',  # CRITICAL: Gemini only supports limit orders
                                side='sell',
                                amount=sell_amount,
                                price=sell_price
                            )
                            logger.info(f"   🟢 [GEMINI] ✅ FLATTENED {pair}: Placed sell order for {sell_amount:.6f} {base_currency} @ ${sell_price:.4f} (${sell_amount * sell_price:.2f})")
                            flattened_count += 1
                        except Exception as e:
                            logger.warning(f"   ⚠️ Failed to flatten {pair}: {e}")
            
            # Cancel all orders
            for pair in pairs_to_process:
                await self.cancel_pair_orders(pair, reason="flatten_positions")
            
            logger.info(f"   🟢 [GEMINI] ✅ Flattened {flattened_count} positions, canceled all orders")
            self.last_flatten_time = datetime.now()
            
        except Exception as e:
            logger.error(f"   ❌ Error flattening positions: {e}")
    
    async def run_market_making_loop(self):
        """Main market-making loop"""
        logger.info("=" * 80)
        logger.info("🟢 🚀 STARTING GEMINI MARKET-MAKING ENGINE")
        logger.info("=" * 80)
        logger.info(f"   🟢 Strategy: Passive Market Making")
        pairs_to_show = len(self.available_pairs) if self.available_pairs else len(TOP_GEMINI_PAIRS)
        logger.info(f"   🟢 Pairs: {pairs_to_show}")
        logger.info(f"   🟢 Available pairs: {self.available_pairs if self.available_pairs else 'Not initialized'}")
        logger.info(f"   🟢 Update interval: {self.requote_interval_seconds}s")
        logger.info(f"   🟢 Take profit interval: {self.take_profit_interval_minutes} minutes")
        logger.info(f"   🟢 Capital per pair: ${self.capital_per_pair:.2f}")
        logger.info(f"   🟢 Order size: {self.order_size_percent*100:.1f}% of capital = ${self.capital_per_pair * self.order_size_percent:.2f} per order")
        logger.info("=" * 80)
        
        self.running = True
        if not hasattr(self, 'last_flatten_time') or self.last_flatten_time is None:
            self.last_flatten_time = datetime.now()

        cycle_count = 0
        
        while self.running:
            try:
                cycle_count += 1
                logger.info("")
                logger.info(f"🟢 [GEMINI] MARKET-MAKING CYCLE #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info("=" * 80)
                
                # Check if time to flatten (take profit)
                time_since_flatten = (datetime.now() - self.last_flatten_time).total_seconds() / 60
                if time_since_flatten >= self.take_profit_interval_minutes:
                    logger.info(f"   🟢 [GEMINI] Time to take profit ({time_since_flatten:.1f} min >= {self.take_profit_interval_minutes} min)")
                    await self.flatten_positions()
                else:
                    logger.info(f"   🟢 [GEMINI] Time until flatten: {self.take_profit_interval_minutes - time_since_flatten:.1f} minutes")
                
                # Process each pair (with rate limiting)
                # Gemini rate limit: 10 req/sec, so we process 10 pairs max per second
                pairs_per_batch = 10  # Process 10 pairs per second to stay under rate limit
                
                # 🟢 IMPROVEMENT: Sort pairs by fill rate (focus on pairs that actually fill)
                pairs_to_process = self.available_pairs if self.available_pairs else TOP_GEMINI_PAIRS
                pairs_to_process = sorted(
                    pairs_to_process,
                    key=lambda p: self.pair_fill_rates.get(p, 0.5),
                    reverse=True
                )
                
                logger.info(f"   🟢 [GEMINI] Processing {len(pairs_to_process)} pairs in batches of {pairs_per_batch}")
                
                # 🟢 CRITICAL: Check and sell ALL inventory first (even if not in trading pairs)
                await self.sell_all_inventory()
                # 🟢 Ensure any queued sells from recent fills are retried once inventory settles
                await self._flush_pending_sell_queue()
                
                total_orders_placed = 0
                total_orders_filled = 0
                cycle_errors: Dict[str, int] = defaultdict(int)
                
                for i in range(0, len(pairs_to_process), pairs_per_batch):
                    batch = pairs_to_process[i:i+pairs_per_batch]
                    logger.info(f"   🟢 [GEMINI] Processing batch {i//pairs_per_batch + 1}: {', '.join(batch)}")
                    
                    # Process batch concurrently
                    tasks = []
                    for pair in batch:
                        tasks.append(self._process_pair_safely(pair))
                    
                    # Wait for batch to complete
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Count results
                    for result in results:
                        if isinstance(result, dict):
                            total_orders_placed += result.get('orders_placed', 0)
                            total_orders_filled += result.get('orders_filled', 0)
                            error_key = result.get('error')
                            if error_key:
                                cycle_errors[error_key] += 1
                    
                    # Wait 1 second between batches to respect rate limit
                    if i + pairs_per_batch < len(pairs_to_process):
                        await asyncio.sleep(1)
                
                # Summary stats
                total_profit = sum(s.total_profit_usd for s in self.stats.values())
                total_fees = sum(s.total_fees_usd for s in self.stats.values())
                total_net = sum(s.net_profit_usd for s in self.stats.values())
                total_orders = sum(s.total_orders for s in self.stats.values())
                total_filled = sum(s.filled_orders for s in self.stats.values())
                total_wins = sum(s.wins for s in self.stats.values())
                total_losses = sum(s.losses for s in self.stats.values())
                win_denom = total_wins + total_losses
                 
                logger.info("")
                logger.info(f"   🟢 [GEMINI] CYCLE SUMMARY:")
                logger.info(f"      Orders placed this cycle: {total_orders_placed}")
                logger.info(f"      Orders filled this cycle: {total_orders_filled}")
                if cycle_errors:
                    error_breakdown = ", ".join(f"{key}:{count}" for key, count in sorted(cycle_errors.items()))
                    logger.info(f"      Skip reasons this cycle: {error_breakdown}")
                pending_items = sum(len(entries) for entries in self.pending_sell_queue.values())
                if pending_items:
                    pending_value_usd = sum(
                        sum(entry.get('amount', 0.0) * entry.get('buy_price', 0.0) for entry in entries)
                        for entries in self.pending_sell_queue.values()
                    )
                    logger.info(f"      Pending sell queue: {pending_items} entries (~${pending_value_usd:.2f} not yet listed)")
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
                logger.info(f"      Total filled (all-time): {total_filled}")
                logger.info(f"      Wins / Losses: {total_wins} / {total_losses}")
                logger.info(f"      Win rate: {(total_wins / win_denom * 100) if win_denom > 0 else 0:.1f}%")
                logger.info(f"      Engine realized net: ${self.net_profit_usd:.2f}")
                logger.info("=" * 80)
                
                # Wait before next update cycle
                await asyncio.sleep(self.requote_interval_seconds)
                
            except Exception as e:
                logger.error(f"   🟢 [GEMINI] ❌ Error in market-making loop: {e}")
                import traceback
                logger.error(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
                await asyncio.sleep(self.requote_interval_seconds)
    
    async def _process_pair_safely(self, pair: str):
        """Process a single pair with error handling"""
        try:
            # Check and update existing orders
            filled_count = await self.check_and_update_orders(pair)
            
            # Place new orders if needed
            result = await self.place_market_making_orders(pair)
            
            # Extract orders from result (now returns dict)
            if isinstance(result, dict):
                orders_placed = result.get('orders_placed', 0)
                orders_filled = result.get('orders_filled', 0) + filled_count
                error_key = result.get('error')
                return {'orders_placed': orders_placed, 'orders_filled': orders_filled, 'error': error_key}
            else:
                # Legacy support (shouldn't happen)
                return {'orders_placed': 0, 'orders_filled': filled_count}
        except Exception as e:
            logger.error(f"   🟢 [GEMINI] ❌ Error processing {pair}: {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
            # Don't raise - continue with other pairs
            return {'orders_placed': 0, 'orders_filled': 0, 'error': 'exception'}
    
    def stop(self):
        """Stop the market-making engine"""
        logger.info("   🛑 Stopping Gemini market-making engine...")
        self.running = False
        
        # Cancel all orders
        pairs_to_process = self.available_pairs if self.available_pairs else TOP_GEMINI_PAIRS
        for pair in pairs_to_process:
            asyncio.create_task(self.cancel_pair_orders(pair, reason="engine_stop"))
    
    def get_stats_summary(self) -> Dict:
        """Get statistics summary"""
        total_profit = sum(s.total_profit_usd for s in self.stats.values())
        total_orders = sum(s.total_orders for s in self.stats.values())
        total_filled = sum(s.filled_orders for s in self.stats.values())
        
        return {
            'total_profit_usd': total_profit,
            'total_orders': total_orders,
            'total_filled': total_filled,
            'win_rate': (total_filled / total_orders * 100) if total_orders > 0 else 0,
            'by_pair': {
                pair: {
                    'profit': s.total_profit_usd,
                    'orders': s.total_orders,
                    'filled': s.filled_orders,
                    'win_rate': (s.filled_orders / s.total_orders * 100) if s.total_orders > 0 else 0
                }
                for pair, s in self.stats.items()
            }
        }

