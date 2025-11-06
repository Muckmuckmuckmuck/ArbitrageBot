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
        
    async def initialize(self):
        """Initialize the market-making engine"""
        logger.info("=" * 80)
        logger.info("🚀 INITIALIZING COINBASE MARKET-MAKING ENGINE")
        logger.info("=" * 80)
        logger.info(f"   Total pairs to check: {len(TOP_COINBASE_PAIRS)}")
        logger.info(f"   Capital per pair: ${self.capital_per_pair:.2f}")
        logger.info(f"   Grid spacing: {self.grid_spacing_percent:.2f}%")
        logger.info(f"   Order size: {self.order_size_percent*100:.1f}% of capital")
        logger.info(f"   Min spread: {self.min_spread_percent:.2f}%")
        logger.info("=" * 80)
        
        # Verify Coinbase has these pairs
        exchange = self.exchange_manager.get_exchange('coinbase')
        available_pairs = []
        for pair in TOP_COINBASE_PAIRS:
            if pair in exchange.markets:
                market_info = exchange.markets[pair]
                active = market_info.get('active', True)
                if active and not market_info.get('future', False) and ':' not in pair:
                    available_pairs.append(pair)
                    logger.info(f"   ✅ Found {pair} on Coinbase")
            else:
                logger.warning(f"   ⚠️ {pair} not found on Coinbase")
        
        self.available_pairs = available_pairs
        
        # Initialize stats for available pairs only
        self.stats = {}
        for pair in available_pairs:
            self.stats[pair] = MarketMakingStats(pair=pair)
            self.pair_fill_rates[pair] = 0.5  # Default neutral fill rate
        
        logger.info(f"   ✅ Available pairs: {len(available_pairs)}/{len(TOP_COINBASE_PAIRS)}")
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
            
            # Get spread
            spread = await self.get_spread(pair)
            if spread is None or spread <= 0 or spread < self.min_spread_percent:
                spread_msg = f"{spread:.3f}%" if spread is not None else "None"
                logger.info(f"   🔵 [COINBASE] ⏭️ Skipping {pair} - spread {spread_msg} < minimum {self.min_spread_percent:.2f}%")
                return {'success': False, 'orders_placed': 0, 'orders_filled': 0, 'error': 'spread_too_tight'}
            
            # 🔵 DYNAMIC: Adjust grid spacing based on spread (50% of spread, min 0.15%, max 0.5%)
            dynamic_spacing = min(max(spread * 0.5, 0.15), 0.5)
            
            # Cancel existing orders
            await self.cancel_pair_orders(pair)
            
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
                price_precision = max(int(price_precision_val), 1)  # At least 1 decimal place
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
            
            # Calculate buy and sell prices
            buy_price = current_price * (1 - dynamic_spacing / 100)
            sell_price = current_price * (1 + dynamic_spacing / 100)
            
            buy_price = round(buy_price, price_precision)
            sell_price = round(sell_price, price_precision)
            
            # Get inventory
            inventory = await self.get_inventory_balance(base_currency)
            quote_currency = pair.split('/')[1]
            quote_balance = await self.get_inventory_balance(quote_currency)
            
            # Calculate max inventory
            inventory_value = (inventory * current_price) if inventory else 0
            total_balance_usd = inventory_value + quote_balance
            max_inventory = total_balance_usd * self.max_inventory_percent
            
            # Place buy order (if we have quote currency and haven't exceeded max inventory)
            if quote_balance is not None and quote_balance >= order_value_usd and inventory_value < max_inventory:
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
                    except Exception:
                        pass
            
            self.active_orders[pair] = [
                o for o in self.active_orders[pair] 
                if o.status == 'open' or o.status == 'filled'
            ]
        except Exception:
            pass
    
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
                        
                        if status in ['closed', 'filled']:
                            mm_order.status = 'filled'
                            mm_order.filled_at = datetime.now()
                            self.stats[pair].filled_orders += 1
                            self.stats[pair].total_orders += 1
                            filled_count += 1
                            
                            # Update fill rate
                            current_fill_rate = self.pair_fill_rates.get(pair, 0.5)
                            self.pair_fill_rates[pair] = current_fill_rate * 0.9 + 0.1
                            
                            # Update performance tracking
                            filled = float(order_status.get('filled', 0))
                            price = float(order_status.get('price', mm_order.price))
                            
                            if mm_order.side == 'buy':
                                logger.info(f"   🔵 [COINBASE] ✅ BUY FILLED: {pair} @ ${price:.4f} for {filled:.6f}")
                            else:
                                spread_profit = (price - mm_order.price) * filled if mm_order.side == 'sell' else 0
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

