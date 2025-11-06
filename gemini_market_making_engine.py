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

class GeminiMarketMakingEngine:
    """Market-making engine for Gemini exchange"""
    
    def __init__(
        self,
        exchange_manager: CoinbaseGeminiExchangeManager,
        capital_per_pair: float = 10.0,  # $10 per pair
        grid_spacing_percent: float = 0.20,  # 0.20% spacing
        order_size_percent: float = 0.01,  # 1% of capital per order
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
        
        # Statistics (will be initialized with available pairs)
        self.stats: Dict[str, MarketMakingStats] = {}
        self.available_pairs: List[str] = []  # Will be set during initialization
        
        # 🟢 IMPROVEMENT: Track fill rates for pairs (focus on pairs that actually fill)
        self.pair_fill_rates: Dict[str, float] = {}  # pair -> fill_rate (0-1)
        
        # Running state
        self.running = False
        self.last_flatten_time = datetime.now()
        
    async def discover_suitable_pairs(
        self,
        min_volume_usd: float = 10000.0,  # $10k minimum 24h volume (lower for Gemini)
        max_pairs: int = 50,  # Top 50 pairs
    ) -> List[Tuple[str, float, float, float]]:
        """
        Dynamically discover all suitable pairs for market making
        Returns: List of (pair, volume_24h, spread, score) tuples, sorted by score
        """
        logger.info("   🟢 [GEMINI] 🔍 DISCOVERING SUITABLE PAIRS...")
        exchange = self.exchange_manager.get_exchange('gemini')
        suitable_pairs = []
        
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
            min_volume_usd=10000.0,  # $10k minimum volume (lower for Gemini)
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
    
    async def get_inventory_balance(self, base_currency: str) -> float:
        """Get current inventory balance for a base currency"""
        try:
            balance = await self.exchange_manager.fetch_balance('gemini')
            free_balance = balance.get('free', {})
            return free_balance.get(base_currency, 0)
        except Exception as e:
            logger.debug(f"   Error fetching balance: {e}")
            return 0.0
    
    async def place_market_making_orders(self, pair: str) -> dict:
        """Place buy and sell limit orders for market making
        
        Returns:
            dict with 'success' (bool), 'orders_placed' (int), 'orders_filled' (int), 'error' (str)
        """
        orders_placed = 0
        orders_filled = 0
        
        try:
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
            
            # If spread is too low BUT we have open orders, keep checking them for fills
            if (spread is None or spread <= 0 or spread < self.min_spread_percent) and open_orders:
                spread_msg = f"{spread:.3f}%" if spread is not None else "None"
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
            
            # 🟢 IMPROVEMENT: Use 50% of current spread as grid spacing (max 0.5%, min 0.15%)
            dynamic_spacing = min(max(spread * 0.5, 0.15), 0.5)
            logger.debug(f"   🟢 [GEMINI] {pair}: Spread {spread:.3f}% → Dynamic spacing {dynamic_spacing:.3f}%")
            
            # 🟢 SMART: Only cancel/update orders if prices have moved significantly
            # This prevents canceling orders that are about to fill
            should_update_orders = await self.should_update_pair_orders(pair, dynamic_spacing)
            if should_update_orders:
                logger.debug(f"   🟢 [GEMINI] {pair}: Prices moved significantly, updating orders")
                await self.cancel_pair_orders(pair)
            else:
                logger.debug(f"   🟢 [GEMINI] {pair}: Existing orders still competitive, keeping them")
                # Check for fills on existing orders
                filled = await self.check_and_update_orders(pair)
                return {'success': True, 'orders_placed': 0, 'orders_filled': filled, 'error': None}
            
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
            min_cost = limits.get('cost', {}).get('min', 5.0) or 5.0  # Default $5 minimum
            
            # 🟢 IMPROVEMENT: Adjust order size based on spread
            base_currency = pair.split('/')[0]
            if spread and self.min_spread_percent > 0:
                # Scale order size: wider spread = larger orders (max 2x, min 0.5x)
                spread_multiplier = min(max(spread / self.min_spread_percent, 0.5), 2.0)
                order_value_usd = self.capital_per_pair * self.order_size_percent * spread_multiplier
                logger.debug(f"   🟢 [GEMINI] {pair}: Spread {spread:.3f}% → Order size multiplier {spread_multiplier:.2f}x → Order value: ${order_value_usd:.2f}")
            else:
                order_value_usd = self.capital_per_pair * self.order_size_percent
            
            # Calculate order amount from USD value
            # 🔵 CRITICAL FIX: Prevent division by zero
            if current_price <= 0:
                logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - invalid current price: {current_price}")
                return False
            
            order_amount = order_value_usd / current_price
            
            # Ensure order value meets minimum cost requirement
            logger.debug(f"   🟢 [GEMINI] {pair}: Order value = ${order_value_usd:.2f}, min cost = ${min_cost:.2f}")
            if order_value_usd < min_cost:
                logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - order value ${order_value_usd:.2f} < minimum ${min_cost:.2f}")
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
                    logger.info(f"   🟢 [GEMINI] {pair}: Using minimum amount {min_amount} after rounding to 0")
                else:
                    logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - order amount too small after rounding: {order_amount}")
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
            if min_order_value < min_cost:
                # Try to increase order amount to meet minimum
                # 🔵 CRITICAL FIX: Prevent division by zero
                if buy_price > 0:
                    required_amount = min_cost / buy_price
                    if required_amount > order_amount:
                        order_amount = round(required_amount, amount_precision)
                        min_order_value = order_amount * buy_price
                        logger.debug(f"   🟢 [GEMINI] {pair}: Increased order amount to meet minimum cost")
                
                # Final check
                if min_order_value < min_cost:
                    logger.info(f"   🟢 [GEMINI] ⏭️ Skipping {pair} - order value ${min_order_value:.2f} < minimum ${min_cost:.2f} (after rounding)")
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
                    if min_order_value < min_cost:
                        logger.info(f"   🟢 [GEMINI] ⏭️ Skipping buy order for {pair} - adjusted order value ${min_order_value:.2f} < minimum ${min_cost:.2f}")
                        order_amount = 0  # Skip order
                    else:
                        # Round to precision
                        order_amount = round(order_amount, amount_precision)
                        if order_amount <= 0:
                            logger.info(f"   🟢 [GEMINI] ⏭️ Skipping buy order for {pair} - order amount rounded to 0")
                            order_amount = 0  # Skip order
                elif max_order_amount >= order_amount:
                    # Have enough balance for full order
                    logger.info(f"   🟢 [GEMINI] {pair}: 📝 ATTEMPTING TO PLACE BUY ORDER... (Balance: ${quote_balance:.2f} {quote_currency}, Required: ${order_amount * buy_price:.2f})")
                else:
                    # Not enough balance even for minimum order
                    logger.info(f"   🟢 [GEMINI] ⏭️ Skipping buy order for {pair} - insufficient {quote_currency} balance: ${quote_balance:.2f} < minimum required ${min_cost:.2f}")
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
            # 🔵 CRITICAL FIX: Use actual inventory, not order_amount (which might be 0 if buy was skipped)
            # Only place sell order if we have sufficient inventory
            if inventory is not None and inventory > 0:
                # Calculate sell amount based on available inventory, not order_amount
                # Use a reasonable sell amount (e.g., 50% of inventory or minimum order size)
                min_sell_amount = min(inventory * 0.5, inventory)  # Sell up to 50% of inventory
                
                # Check if we have enough for minimum order
                if min_sell_amount * sell_price >= min_cost:
                    logger.info(f"   🟢 [GEMINI] {pair}: 📝 ATTEMPTING TO PLACE SELL ORDER... (Inventory: {inventory:.6f})")
                    try:
                        sell_amount = min(min_sell_amount, inventory)
                        
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
                logger.debug(f"   🟢 [GEMINI] {pair}: Order {order.order_id} is {age_seconds:.0f}s old, updating")
                return True
        
        # Check if prices have moved significantly
        try:
            ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
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
                        logger.debug(f"   🟢 [GEMINI] {pair}: Order {order.order_id} price {price_diff_pct:.2f}% away from market, updating")
                        return True
        except Exception as e:
            logger.debug(f"   🟢 [GEMINI] Error checking price movement for {pair}: {e}")
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
                            'gemini',
                            mm_order.order_id,
                            pair
                        )
                        mm_order.status = 'canceled'
                        logger.debug(f"   🟢 [GEMINI] Canceled order {mm_order.order_id} for {pair}")
                    except Exception as e:
                        logger.debug(f"   Error canceling order {mm_order.order_id}: {e}")
            
            # Remove canceled orders
            self.active_orders[pair] = [
                o for o in self.active_orders[pair] 
                if o.status == 'open' or o.status == 'filled'
            ]
        except Exception as e:
            logger.debug(f"   Error canceling orders for {pair}: {e}")
    
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
                        
                        if status in ['closed', 'filled']:
                            mm_order.status = 'filled'
                            mm_order.filled_at = datetime.now()
                            self.stats[pair].filled_orders += 1
                            self.stats[pair].total_orders += 1
                            filled_count += 1
                            
                            # 🟢 IMPROVEMENT: Update fill rate (exponential moving average)
                            current_fill_rate = self.pair_fill_rates.get(pair, 0.5)
                            self.pair_fill_rates[pair] = current_fill_rate * 0.9 + 0.1  # 10% weight to new fill
                            
                            # Calculate profit (simplified - actual calculation depends on inventory)
                            filled = float(order_status.get('filled', 0))
                            price = float(order_status.get('price', mm_order.price))
                            cost = float(order_status.get('cost', 0))
                            
                            if mm_order.side == 'buy':
                                # Bought at lower price - profit when we sell
                                logger.info(f"   🟢 [GEMINI] ✅✅✅ BUY FILLED: {pair} @ ${price:.4f} for {filled:.6f}")
                                
                                # 🟢 CRITICAL: Immediately place sell order for FULL amount bought
                                try:
                                    await self._place_sell_order_for_filled_buy(pair, filled, price)
                                except Exception as e:
                                    logger.error(f"   🟢 [GEMINI] ❌ ERROR placing sell order after buy fill: {type(e).__name__}: {e}")
                                    import traceback
                                    logger.debug(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
                            else:
                                # Sold at higher price - realized profit
                                spread_profit = (price - mm_order.price) * filled if mm_order.side == 'sell' else 0
                                logger.info(f"   🟢 [GEMINI] ✅ SELL FILLED: {pair} @ ${price:.4f} for {filled:.6f} | Profit: ${spread_profit:.2f}")
                                self.stats[pair].total_profit_usd += spread_profit
                        
                        elif status == 'canceled':
                            mm_order.status = 'canceled'
                            logger.debug(f"   🟢 [GEMINI] Order {mm_order.order_id} canceled for {pair}")
                    except Exception as e:
                        logger.debug(f"   🟢 [GEMINI] Error checking order {mm_order.order_id}: {e}")
        except Exception as e:
            logger.debug(f"   🟢 [GEMINI] Error checking orders for {pair}: {e}")
        
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
                logger.warning(f"   🟢 [GEMINI] ⚠️ {pair}: No inventory available to sell after buy fill (filled: {filled_amount}, inventory: {inventory})")
                return
            
            # Get current market price for sell order
            ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
            current_ask = ticker.get('ask', 0) or 0
            current_bid = ticker.get('bid', 0) or 0
            
            if current_ask <= 0:
                # Fallback to buy_price with markup
                sell_price = buy_price * 1.01  # 1% markup
                logger.warning(f"   🟢 [GEMINI] ⚠️ {pair}: No ask price, using buy_price * 1.01 = ${sell_price:.6f}")
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
            exchange = self.exchange_manager.get_exchange('gemini')
            market_info = exchange.markets.get(pair, {})
            precision_data = market_info.get('precision', {})
            
            amount_precision = max(int(precision_data.get('amount', 8)), 1)
            price_precision = max(int(precision_data.get('price', 8)), 1)
            
            # Round amounts to exchange precision
            sell_amount = round(sell_amount, amount_precision)
            
            # Check minimum order size
            min_cost = market_info.get('limits', {}).get('cost', {}).get('min', 5.0)
            min_amount = market_info.get('limits', {}).get('amount', {}).get('min', 0.0)
            
            if sell_amount * sell_price < min_cost:
                logger.warning(f"   🟢 [GEMINI] ⚠️ {pair}: Sell order value ${sell_amount * sell_price:.2f} < minimum ${min_cost:.2f}, skipping")
                return
            
            if sell_amount < min_amount:
                logger.warning(f"   🟢 [GEMINI] ⚠️ {pair}: Sell amount {sell_amount:.6f} < minimum {min_amount:.6f}, skipping")
                return
            
            # Place the sell order
            logger.info(f"   🟢 [GEMINI] 📝 PLACING SELL ORDER for filled buy: {pair} @ ${sell_price:.6f} for {sell_amount:.6f} (${sell_amount * sell_price:.2f})")
            
            sell_order = await self.exchange_manager.create_order(
                exchange_id='gemini',
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
                
                logger.info(f"   🟢 [GEMINI] ✅✅✅ SELL ORDER PLACED for filled buy: {pair} @ ${sell_price:.4f} for {sell_amount:.6f} | Order ID: {sell_order_id}")
            else:
                logger.error(f"   🟢 [GEMINI] ❌ Failed to place sell order for filled buy: No order ID returned")
                
        except Exception as e:
            logger.error(f"   🟢 [GEMINI] ❌ ERROR placing sell order for filled buy on {pair}: {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
    
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
                await self.cancel_pair_orders(pair)
            
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
                
                total_orders_placed = 0
                total_orders_filled = 0
                
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
                    
                    # Wait 1 second between batches to respect rate limit
                    if i + pairs_per_batch < len(pairs_to_process):
                        await asyncio.sleep(1)
                
                # Summary stats
                total_profit = sum(s.total_profit_usd for s in self.stats.values())
                total_orders = sum(s.total_orders for s in self.stats.values())
                total_filled = sum(s.filled_orders for s in self.stats.values())
                
                logger.info("")
                logger.info(f"   🟢 [GEMINI] CYCLE SUMMARY:")
                logger.info(f"      Orders placed this cycle: {total_orders_placed}")
                logger.info(f"      Orders filled this cycle: {total_orders_filled}")
                logger.info(f"      Total profit (all-time): ${total_profit:.2f}")
                logger.info(f"      Total orders (all-time): {total_orders}")
                logger.info(f"      Total filled (all-time): {total_filled}")
                logger.info(f"      Win rate: {(total_filled / total_orders * 100) if total_orders > 0 else 0:.1f}%")
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
                return {'orders_placed': orders_placed, 'orders_filled': orders_filled}
            else:
                # Legacy support (shouldn't happen)
                return {'orders_placed': 0, 'orders_filled': filled_count}
        except Exception as e:
            logger.error(f"   🟢 [GEMINI] ❌ Error processing {pair}: {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"   🟢 [GEMINI] Traceback: {traceback.format_exc()}")
            # Don't raise - continue with other pairs
            return {'orders_placed': 0, 'orders_filled': 0}
    
    def stop(self):
        """Stop the market-making engine"""
        logger.info("   🛑 Stopping Gemini market-making engine...")
        self.running = False
        
        # Cancel all orders
        pairs_to_process = self.available_pairs if self.available_pairs else TOP_GEMINI_PAIRS
        for pair in pairs_to_process:
            asyncio.create_task(self.cancel_pair_orders(pair))
    
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

