#!/usr/bin/env python3
"""
Coinbase Market Making Engine
Implements passive market-making strategy on Coinbase exchange
Top pairs optimized for maximum profitability with dynamic adjustments

EXCHANGE: 🔵 COINBASE ONLY - This entire module is for Coinbase market making
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Top pairs for market making on Coinbase (ranked by liquidity and profitability)
TOP_COINBASE_PAIRS = [
    'BTC/USD',   # Highest liquidity
    'ETH/USD',   # High liquidity
    'SOL/USD',   # High liquidity
    'AVAX/USD',  # Good liquidity
    'LINK/USD',  # Good liquidity
    'UNI/USD',   # Good liquidity
    'DOGE/USD',  # High volume
    'XRP/USD',   # High volume
    'ADA/USD',   # Good liquidity
    'DOT/USD',   # Good liquidity
    'MATIC/USD', # Good liquidity
    'ATOM/USD',  # Good liquidity
    'ALGO/USD',  # Good liquidity
    'LTC/USD',   # Good liquidity
    'AAVE/USD',  # Good liquidity
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

class CoinbaseMarketMakingEngine:
    """Market-making engine for Coinbase exchange"""
    
    def __init__(
        self,
        exchange_manager: CoinbaseGeminiExchangeManager,
        capital_per_pair: float = 50.0,  # $50 per pair
        grid_spacing_percent: float = 0.20,  # 0.20% spacing
        order_size_percent: float = 0.10,  # 10% of capital per order
        min_spread_percent: float = 0.12,  # Skip if spread < 0.12%
        max_inventory_percent: float = 0.25,  # Max 25% in one asset
        requote_interval_seconds: int = 15,  # Update orders every 15s
        stop_loss_percent: float = 0.02,  # -2% stop loss
        take_profit_interval_minutes: int = 60,  # Flatten every hour
    ):
        self.exchange_manager = exchange_manager
        self.capital_per_pair = capital_per_pair
        self.grid_spacing_percent = grid_spacing_percent
        self.order_size_percent = order_size_percent
        self.min_spread_percent = min_spread_percent
        self.max_inventory_percent = max_inventory_percent
        self.requote_interval_seconds = requote_interval_seconds
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_interval_minutes = take_profit_interval_minutes
        
        # Active orders tracking
        self.active_orders: Dict[str, List[MarketMakingOrder]] = defaultdict(list)
        
        # Statistics
        self.stats: Dict[str, MarketMakingStats] = {}
        self.available_pairs: List[str] = []  # Will be set during initialization
        
        # 🔵 IMPROVEMENT: Track fill rates for pairs (focus on pairs that actually fill)
        self.pair_fill_rates: Dict[str, float] = {}  # pair -> fill_rate (0-1)
        
        # 🔵 IMPROVEMENT: Dynamic adjustment tracking
        self.pair_performance: Dict[str, Dict] = defaultdict(lambda: {
            'total_profit': 0.0,
            'total_trades': 0,
            'avg_spread': 0.0,
            'fill_rate': 0.5
        })
        
        # Running state
        self.running = False
        self.last_flatten_time = datetime.now()
        
    async def discover_suitable_pairs(
        self,
        min_volume_usd: float = 50000.0,  # $50k minimum 24h volume
        max_pairs: int = 50,  # Top 50 pairs
    ) -> List[Tuple[str, float, float, float]]:
        """
        Dynamically discover all suitable pairs for market making
        Returns: List of (pair, volume_24h, spread, score) tuples, sorted by score
        """
        logger.info("   🔵 [COINBASE] 🔍 DISCOVERING SUITABLE PAIRS...")
        exchange = self.exchange_manager.get_exchange('coinbase')
        suitable_pairs = []
        
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
                    
                    if not volume_24h or volume_24h < min_volume_usd:
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
                    volume_score = min(volume_24h / 1000000.0, 1.0)  # Normalize to $1M
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
            min_volume_usd=50000.0,  # $50k minimum volume
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
            self.pair_performance[pair] = {'total_profit': 0.0, 'trades': 0}
        
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
                    return spread
            return None
        except Exception as e:
            logger.debug(f"   🔵 [COINBASE] Error fetching spread for {pair}: {e}")
            return None
    
    async def get_inventory_balance(self, base_currency: str) -> float:
        """Get current inventory balance for a base currency"""
        try:
            balance = await self.exchange_manager.fetch_balance('coinbase')
            free_balance = balance.get('free', {})
            return free_balance.get(base_currency, 0)
        except Exception as e:
            logger.debug(f"   Error fetching balance: {e}")
            return 0.0
    
    async def place_market_making_orders(self, pair: str) -> dict:
        """Place buy and sell limit orders for market making"""
        orders_placed = 0
        orders_filled = 0
        
        try:
            logger.info(f"   🔵 [COINBASE] 🔍 PROCESSING {pair}...")
            
            # Get current price first (needed for volume calculation)
            current_price = await self.get_current_price(pair)
            if current_price is None or current_price <= 0:
                logger.warning(f"   🔵 [COINBASE] ⚠️ Skipping {pair} - invalid price: {current_price}")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'invalid_price'}
            
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
            
            # 🔵 CRITICAL: Check for existing orders FIRST before spread check
            # If we have open orders, check them for fills even if spread is low
            existing_orders = self.active_orders.get(pair, [])
            open_orders = [o for o in existing_orders if o.status == 'open']
            
            # Get spread
            spread = await self.get_spread(pair)
            
            # If spread is too low BUT we have open orders, keep checking them for fills
            if (spread is None or spread <= 0 or spread < self.min_spread_percent) and open_orders:
                spread_msg = f"{spread:.3f}%" if spread is not None else "None"
                logger.info(f"   🔵 [COINBASE] {pair}: Spread {spread_msg} < minimum {self.min_spread_percent:.2f}%, but keeping {len(open_orders)} open order(s) to check for fills")
                # Check existing orders for fills, don't cancel them
                filled = await self.check_and_update_orders(pair)
                return {'success': True, 'orders_placed': 0, 'orders_filled': filled, 'error': None}
            
            # If spread is too low and no open orders, skip entirely
            if spread is None or spread <= 0 or spread < self.min_spread_percent:
                spread_msg = f"{spread:.3f}%" if spread is not None else "None"
                logger.info(f"   🔵 [COINBASE] ⏭️ Skipping {pair} - spread {spread_msg} < minimum {self.min_spread_percent:.2f}%")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'spread_too_tight'}
            
            # 🔵 DYNAMIC: Adjust grid spacing based on spread (50% of spread, min 0.15%, max 0.5%)
            dynamic_spacing = min(max(spread * 0.5, 0.15), 0.5)
            
            # 🔵 SMART: Only cancel/update orders if prices have moved significantly
            # This prevents canceling orders that are about to fill
            should_update_orders = await self.should_update_pair_orders(pair, dynamic_spacing)
            if should_update_orders:
                logger.debug(f"   🔵 [COINBASE] {pair}: Prices moved significantly, updating orders")
                await self.cancel_pair_orders(pair)
            else:
                logger.debug(f"   🔵 [COINBASE] {pair}: Existing orders still competitive, keeping them")
                # Check for fills on existing orders
                filled = await self.check_and_update_orders(pair)
                return {'success': True, 'orders_placed': 0, 'orders_filled': filled, 'error': None}
            
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
            min_cost = limits.get('cost', {}).get('min', 5.0) or 5.0
            
            # 🔵 DYNAMIC: Adjust order size based on spread and performance
            base_currency = pair.split('/')[0]
            spread_multiplier = min(max(spread / self.min_spread_percent, 0.5), 2.0)
            
            # Adjust based on fill rate (pairs with higher fill rates get larger orders)
            fill_rate = self.pair_fill_rates.get(pair, 0.5)
            fill_rate_multiplier = 0.5 + fill_rate  # 0.5x to 1.5x based on fill rate
            
            order_value_usd = self.capital_per_pair * self.order_size_percent * spread_multiplier * fill_rate_multiplier
            
            order_amount = order_value_usd / current_price
            
            if order_value_usd < min_cost:
                logger.info(f"   🔵 [COINBASE] ⏭️ Skipping {pair} - order value ${order_value_usd:.2f} < minimum ${min_cost:.2f}")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'order_value_too_small'}
            
            order_amount = round(order_amount, amount_precision)
            if order_amount <= 0:
                if min_amount > 0:
                    order_amount = min_amount
                    order_value_usd = order_amount * current_price
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
            
            # Get inventory
            inventory = await self.get_inventory_balance(base_currency)
            quote_currency = pair.split('/')[1]
            quote_balance = await self.get_inventory_balance(quote_currency)
            
            # Calculate max inventory
            inventory_value = (inventory * current_price) if inventory else 0
            total_balance_usd = inventory_value + quote_balance
            max_inventory = total_balance_usd * self.max_inventory_percent
            
            # Place buy order (if we have quote currency and haven't exceeded max inventory)
            # 🔵 CRITICAL: Check balance and dynamically size order
            if quote_balance is None:
                quote_balance = 0.0
            
            if inventory_value >= max_inventory:
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
                    if min_order_value < min_cost:
                        logger.info(f"   🔵 [COINBASE] ⏭️ Skipping buy order for {pair} - adjusted order value ${min_order_value:.2f} < minimum ${min_cost:.2f}")
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
                    # Not enough balance even for minimum order
                    logger.info(f"   🔵 [COINBASE] ⏭️ Skipping buy order for {pair} - insufficient {quote_currency} balance: ${quote_balance:.2f} < minimum required ${min_cost:.2f}")
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
                            logger.info(f"   🔵 [COINBASE] ✅ BUY ORDER PLACED: {pair} @ ${buy_price:.4f} for {order_amount:.6f} | Order ID: {buy_order_id}")
                    except Exception as e:
                        logger.error(f"   🔵 [COINBASE] ❌ FAILED TO PLACE BUY ORDER: {e}")
            
            # Place sell order (if we have inventory)
            if inventory is not None and inventory > order_amount * 0.5:
                try:
                    sell_amount = min(order_amount, inventory)
                    sell_order = await self.exchange_manager.create_order(
                        exchange_id='coinbase',
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
                        orders_placed += 1
                        logger.info(f"   🔵 [COINBASE] ✅ SELL ORDER PLACED: {pair} @ ${sell_price:.4f} for {sell_amount:.6f} | Order ID: {sell_order_id}")
                except Exception as e:
                    logger.error(f"   🔵 [COINBASE] ❌ FAILED TO PLACE SELL ORDER: {e}")
            
            # Check for filled orders
            orders_filled = await self.check_and_update_orders(pair)
            
            return {'success': orders_placed > 0, 'orders_placed': orders_placed, 'orders_filled': orders_filled, 'error': None}
            
        except Exception as e:
            logger.error(f"   🔵 [COINBASE] ❌ ERROR placing market-making orders for {pair}: {e}")
            return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': str(e)}
    
    async def should_update_pair_orders(self, pair: str, target_spacing: float) -> bool:
        """
        Determine if existing orders should be updated
        Returns True if:
        - No existing orders
        - Orders are older than 2 minutes
        - Prices have moved significantly (>0.5% away from current market)
        """
        existing_orders = self.active_orders.get(pair, [])
        if not existing_orders:
            return True  # No orders, need to place new ones
        
        # Check if any orders are still open
        open_orders = [o for o in existing_orders if o.status == 'open']
        if not open_orders:
            return True  # No open orders, need to place new ones
        
        # Check order age - if older than 5 minutes, update them (increased from 2 to 5 minutes)
        now = datetime.now()
        for order in open_orders:
            age_seconds = (now - order.created_at).total_seconds()
            if age_seconds > 300:  # 5 minutes (increased to give more time to fill)
                logger.debug(f"   🔵 [COINBASE] {pair}: Order {order.order_id} is {age_seconds:.0f}s old, updating")
                return True
        
        # Check if prices have moved significantly
        try:
            ticker = await self.exchange_manager.fetch_ticker('coinbase', pair)
            current_bid = ticker.get('bid', 0) or 0
            current_ask = ticker.get('ask', 0) or 0
            
            if current_bid <= 0 or current_ask <= 0:
                return True  # Can't check, update anyway
            
            for order in open_orders:
                if order.price > 0:
                    # Check if order price is >0.5% away from current market
                    if order.side == 'buy':
                        price_diff_pct = abs((current_bid - order.price) / current_bid) * 100
                    else:  # sell
                        price_diff_pct = abs((current_ask - order.price) / current_ask) * 100
                    
                    if price_diff_pct > 1.0:  # More than 1.0% away (increased from 0.5% to prevent premature cancellation)
                        logger.debug(f"   🔵 [COINBASE] {pair}: Order {order.order_id} price {price_diff_pct:.2f}% away from market, updating")
                        return True
        except Exception as e:
            logger.debug(f"   🔵 [COINBASE] Error checking price movement for {pair}: {e}")
            # On error, don't update (keep existing orders)
            return False
        
        # Orders are still competitive, keep them
        return False
    
    async def cancel_pair_orders(self, pair: str):
        """Cancel all active orders for a pair"""
        try:
            orders_to_cancel = self.active_orders[pair].copy()
            for mm_order in orders_to_cancel:
                if mm_order.order_id and mm_order.status == 'open':
                    try:
                        await self.exchange_manager.cancel_order(
                            'coinbase',
                            mm_order.order_id,
                            pair
                        )
                        mm_order.status = 'canceled'
                        logger.debug(f"   🔵 [COINBASE] Canceled order {mm_order.order_id} for {pair}")
                    except Exception as e:
                        logger.debug(f"   🔵 [COINBASE] Error canceling order {mm_order.order_id}: {e}")
            
            self.active_orders[pair] = [
                o for o in self.active_orders[pair] 
                if o.status == 'open' or o.status == 'filled'
            ]
        except Exception as e:
            logger.debug(f"   🔵 [COINBASE] Error canceling orders for {pair}: {e}")
    
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
                        status = order_status.get('status', 'unknown')
                        
                        # Check for partial or full fills
                        filled = float(order_status.get('filled', 0))
                        remaining = float(order_status.get('remaining', 0))
                        price = float(order_status.get('price', mm_order.price))
                        
                        # Track previous filled amount to detect new fills
                        previous_filled = getattr(mm_order, 'filled_amount', 0.0)
                        new_filled = filled - previous_filled
                        
                        if filled > previous_filled:
                            # New fill detected (partial or full)
                            mm_order.filled_amount = filled
                            
                            if mm_order.side == 'buy':
                                # Buy order got filled (partially or fully)
                                if status in ['closed', 'filled']:
                                    mm_order.status = 'filled'
                                    mm_order.filled_at = datetime.now()
                                    self.stats[pair].filled_orders += 1
                                    self.stats[pair].total_orders += 1
                                    filled_count += 1
                                    logger.info(f"   🔵 [COINBASE] ✅✅✅ BUY FULLY FILLED: {pair} @ ${price:.4f} for {filled:.6f}")
                                else:
                                    # Partial fill
                                    logger.info(f"   🔵 [COINBASE] ✅ BUY PARTIALLY FILLED: {pair} @ ${price:.4f} - {new_filled:.6f} filled (total: {filled:.6f}/{mm_order.amount:.6f})")
                                
                                # 🔵 CRITICAL: Immediately sell the NEW amount that was just filled
                                if new_filled > 0:
                                    try:
                                        await self._place_sell_order_for_filled_buy(pair, new_filled, price)
                                    except Exception as e:
                                        logger.error(f"   🔵 [COINBASE] ❌ ERROR placing sell order after buy fill: {type(e).__name__}: {e}")
                                        import traceback
                                        logger.debug(f"   🔵 [COINBASE] Traceback: {traceback.format_exc()}")
                            
                            elif mm_order.side == 'sell':
                                # Sell order got filled (partially or fully)
                                if status in ['closed', 'filled']:
                                    mm_order.status = 'filled'
                                    mm_order.filled_at = datetime.now()
                                    self.stats[pair].filled_orders += 1
                                    self.stats[pair].total_orders += 1
                                    filled_count += 1
                                    spread_profit = (price - mm_order.price) * filled
                                    logger.info(f"   🔵 [COINBASE] ✅✅✅ SELL FULLY FILLED: {pair} @ ${price:.4f} for {filled:.6f} | Profit: ${spread_profit:.2f}")
                                    self.stats[pair].total_profit_usd += spread_profit
                                    self.pair_performance[pair]['total_profit'] += spread_profit
                                    self.pair_performance[pair]['total_trades'] += 1
                                else:
                                    # Partial fill
                                    spread_profit = (price - mm_order.price) * new_filled
                                    logger.info(f"   🔵 [COINBASE] ✅ SELL PARTIALLY FILLED: {pair} @ ${price:.4f} - {new_filled:.6f} filled (total: {filled:.6f}/{mm_order.amount:.6f}) | Profit: ${spread_profit:.2f}")
                                    self.stats[pair].total_profit_usd += spread_profit
                                    self.pair_performance[pair]['total_profit'] += spread_profit
                            
                            # Update fill rate
                            current_fill_rate = self.pair_fill_rates.get(pair, 0.5)
                            self.pair_fill_rates[pair] = current_fill_rate * 0.9 + 0.1
                        
                        elif status in ['closed', 'filled'] and mm_order.status == 'open':
                            # Order fully filled but we didn't detect it above (fallback)
                            mm_order.status = 'filled'
                            mm_order.filled_at = datetime.now()
                            self.stats[pair].filled_orders += 1
                            self.stats[pair].total_orders += 1
                            filled_count += 1
                            
                            if mm_order.side == 'buy':
                                logger.info(f"   🔵 [COINBASE] ✅✅✅ BUY FILLED: {pair} @ ${price:.4f} for {filled:.6f}")
                                try:
                                    await self._place_sell_order_for_filled_buy(pair, filled, price)
                                except Exception as e:
                                    logger.error(f"   🔵 [COINBASE] ❌ ERROR placing sell order after buy fill: {type(e).__name__}: {e}")
                            else:
                                spread_profit = (price - mm_order.price) * filled
                                logger.info(f"   🔵 [COINBASE] ✅ SELL FILLED: {pair} @ ${price:.4f} for {filled:.6f} | Profit: ${spread_profit:.2f}")
                                self.stats[pair].total_profit_usd += spread_profit
                                self.pair_performance[pair]['total_profit'] += spread_profit
                                self.pair_performance[pair]['total_trades'] += 1
                        
                        elif status == 'canceled':
                            mm_order.status = 'canceled'
                    except Exception:
                        pass
        except Exception:
            pass
        
        return filled_count
    
    async def _place_sell_order_for_filled_buy(self, pair: str, filled_amount: float, buy_price: float):
        """
        Place a sell order immediately after a buy order fills
        This ensures we sell the complete amount we bought
        """
        try:
            base_currency = pair.split('/')[0]
            
            # Wait a moment for balance to update
            await asyncio.sleep(0.5)
            
            # Get current inventory to verify we have the crypto
            inventory = await self.get_inventory_balance(base_currency)
            if inventory is None:
                inventory = 0.0
            
            # Use the actual filled amount (or available inventory if less)
            sell_amount = min(filled_amount, inventory)
            
            if sell_amount <= 0:
                logger.warning(f"   🔵 [COINBASE] ⚠️ {pair}: No inventory available to sell after buy fill (filled: {filled_amount}, inventory: {inventory})")
                return
            
            # Get current market price for sell order
            ticker = await self.exchange_manager.fetch_ticker('coinbase', pair)
            current_ask = ticker.get('ask', 0) or 0
            current_bid = ticker.get('bid', 0) or 0
            
            if current_ask <= 0:
                # Fallback to buy_price with markup
                sell_price = buy_price * 1.01  # 1% markup
                logger.warning(f"   🔵 [COINBASE] ⚠️ {pair}: No ask price, using buy_price * 1.01 = ${sell_price:.6f}")
            else:
                # Place sell order slightly above ask to get filled quickly
                spread = await self.get_spread(pair)
                if spread and spread > 0:
                    # Use 50% of spread as markup
                    markup = min(max(spread * 0.5, 0.15), 0.5) / 100
                else:
                    markup = 0.002  # Default 0.2% markup
                
                sell_price = current_ask * (1 + markup)
            
            # Get market info for precision
            exchange = self.exchange_manager.get_exchange('coinbase')
            market_info = exchange.markets.get(pair, {})
            precision_data = market_info.get('precision', {})
            
            amount_precision = max(int(precision_data.get('amount', 8)), 1)
            price_precision = max(int(precision_data.get('price', 8)), 2)
            
            # Round amounts to exchange precision
            sell_amount = round(sell_amount, amount_precision)
            
            # Check minimum order size
            min_cost = market_info.get('limits', {}).get('cost', {}).get('min', 1.0)
            min_amount = market_info.get('limits', {}).get('amount', {}).get('min', 0.0)
            
            if sell_amount * sell_price < min_cost:
                logger.warning(f"   🔵 [COINBASE] ⚠️ {pair}: Sell order value ${sell_amount * sell_price:.2f} < minimum ${min_cost:.2f}, skipping")
                return
            
            if sell_amount < min_amount:
                logger.warning(f"   🔵 [COINBASE] ⚠️ {pair}: Sell amount {sell_amount:.6f} < minimum {min_amount:.6f}, skipping")
                return
            
            # Place the sell order
            logger.info(f"   🔵 [COINBASE] 📝 PLACING SELL ORDER for filled buy: {pair} @ ${sell_price:.6f} for {sell_amount:.6f} (${sell_amount * sell_price:.2f})")
            
            sell_order = await self.exchange_manager.create_order(
                exchange_id='coinbase',
                symbol=pair,
                order_type='limit',
                side='sell',
                amount=sell_amount,
                price=sell_price
            )
            
            sell_order_id = sell_order.get('id')
            if sell_order_id:
                # Track the order
                from datetime import datetime
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
                
                logger.info(f"   🔵 [COINBASE] ✅✅✅ SELL ORDER PLACED for filled buy: {pair} @ ${sell_price:.4f} for {sell_amount:.6f} | Order ID: {sell_order_id}")
            else:
                logger.error(f"   🔵 [COINBASE] ❌ Failed to place sell order for filled buy: No order ID returned")
                
        except Exception as e:
            logger.error(f"   🔵 [COINBASE] ❌ ERROR placing sell order for filled buy on {pair}: {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"   🔵 [COINBASE] Traceback: {traceback.format_exc()}")
    
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
                    current_price = await self.get_current_price(pair)
                    if current_price and current_price > 0:
                        # Check if position is large enough to flatten (must meet minimum order size)
                        market_info = exchange.markets.get(pair, {})
                        limits = market_info.get('limits', {})
                        min_cost = limits.get('cost', {}).get('min', 5.0) or 5.0
                        
                        position_value = inventory * current_price
                        if position_value < min_cost:
                            logger.debug(f"   🔵 [COINBASE] Skipping flatten {pair} - position value ${position_value:.2f} < minimum ${min_cost:.2f}")
                            continue
                        
                        sell_amount = inventory * 0.95  # 95% to leave buffer
                        sell_price = current_price * 0.995  # 0.5% below market to ensure fill
                        
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
                            logger.info(f"   🔵 [COINBASE] ✅ FLATTENED {pair}: Placed sell order for {sell_amount:.6f} {base_currency} @ ${sell_price:.4f}")
                            flattened_count += 1
                        except Exception as e:
                            logger.warning(f"   🔵 [COINBASE] ⚠️ Failed to flatten {pair}: {e}")
            
            # Cancel all orders
            for pair in self.available_pairs:
                await self.cancel_pair_orders(pair)
            
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
        cycle_count = 0
        
        while self.running:
            try:
                cycle_count += 1
                logger.info("")
                logger.info(f"🔵 [COINBASE] MARKET-MAKING CYCLE #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info("=" * 80)
                
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
                
                # Process each pair
                for pair in pairs_to_process:
                    if not self.running:
                        break
                    
                    await self.place_market_making_orders(pair)
                    await asyncio.sleep(1)  # Small delay between pairs
                
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

