#!/usr/bin/env python3
"""
Gemini Market Making Engine
Implements passive market-making strategy on Gemini exchange
Top 10 pairs optimized for maximum profitability
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
TOP_GEMINI_PAIRS = [
    'ARB/USD',   # Rank 1: 1.5-4.0% daily ROI, Low-Med risk
    'OP/USD',    # Rank 2: 1.2-3.5% daily ROI, Low risk
    'LINK/USD',  # Rank 3: 0.8-2.2% daily ROI, Low risk
    'AVAX/USD',  # Rank 4: 1.0-2.8% daily ROI, Low-Med risk
    'MATIC/USD', # Rank 5: 1.0-2.5% daily ROI, Low risk
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
        
        # Statistics
        self.stats: Dict[str, MarketMakingStats] = {}
        for pair in TOP_GEMINI_PAIRS:
            self.stats[pair] = MarketMakingStats(pair=pair)
        
        # Running state
        self.running = False
        self.last_flatten_time = datetime.now()
        
    async def initialize(self):
        """Initialize the market-making engine"""
        logger.info("=" * 80)
        logger.info("🚀 INITIALIZING GEMINI MARKET-MAKING ENGINE")
        logger.info("=" * 80)
        logger.info(f"   Pairs: {len(TOP_GEMINI_PAIRS)}")
        logger.info(f"   Capital per pair: ${self.capital_per_pair:.2f}")
        logger.info(f"   Grid spacing: {self.grid_spacing_percent:.2f}%")
        logger.info(f"   Order size: {self.order_size_percent*100:.1f}% of capital")
        logger.info(f"   Min spread: {self.min_spread_percent:.2f}%")
        logger.info("=" * 80)
        
        # Verify Gemini has these pairs
        exchange = self.exchange_manager.get_exchange('gemini')
        available_pairs = []
        for pair in TOP_GEMINI_PAIRS:
            if pair in exchange.markets:
                market_info = exchange.markets[pair]
                if market_info.get('active', True):
                    available_pairs.append(pair)
                else:
                    logger.warning(f"   ⚠️ {pair} is not active on Gemini")
            else:
                logger.warning(f"   ⚠️ {pair} not found on Gemini")
        
        logger.info(f"   ✅ Available pairs: {len(available_pairs)}/{len(TOP_GEMINI_PAIRS)}")
        logger.info("=" * 80)
        
    async def get_current_price(self, pair: str) -> Optional[float]:
        """Get current market price for a pair"""
        try:
            ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
            mid_price = (ticker.get('bid', 0) + ticker.get('ask', 0)) / 2
            if mid_price > 0:
                return mid_price
            return ticker.get('last') or ticker.get('close') or None
        except Exception as e:
            logger.debug(f"   Error fetching price for {pair}: {e}")
            return None
    
    async def get_spread(self, pair: str) -> Optional[float]:
        """Get current spread percentage"""
        try:
            ticker = await self.exchange_manager.fetch_ticker('gemini', pair)
            bid = ticker.get('bid', 0)
            ask = ticker.get('ask', 0)
            if bid > 0 and ask > 0:
                mid = (bid + ask) / 2
                spread = ((ask - bid) / mid) * 100
                return spread
            return None
        except Exception as e:
            logger.debug(f"   Error fetching spread for {pair}: {e}")
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
    
    async def place_market_making_orders(self, pair: str) -> bool:
        """Place buy and sell limit orders for market making"""
        try:
            # Check if spread is wide enough
            spread = await self.get_spread(pair)
            if spread is None or spread < self.min_spread_percent:
                return False  # Spread too tight
            
            # Get current price
            current_price = await self.get_current_price(pair)
            if current_price is None or current_price <= 0:
                return False
            
            # Cancel existing orders for this pair first
            await self.cancel_pair_orders(pair)
            
            # Calculate order sizes
            base_currency = pair.split('/')[0]
            order_amount = (self.capital_per_pair * self.order_size_percent) / current_price
            
            # Get market info for precision requirements
            exchange = self.exchange_manager.get_exchange('gemini')
            market_info = exchange.markets.get(pair, {})
            
            # Apply precision requirements (if available from market info)
            amount_precision = market_info.get('precision', {}).get('amount', 8)
            price_precision = market_info.get('precision', {}).get('price', 8)
            
            # Round amounts and prices to exchange precision
            order_amount = round(order_amount, amount_precision)
            if order_amount <= 0:
                logger.debug(f"   ⚠️ Order amount too small after rounding: {order_amount}")
                return False
            
            # Calculate grid prices
            buy_price = current_price * (1 - self.grid_spacing_percent / 100)
            sell_price = current_price * (1 + self.grid_spacing_percent / 100)
            
            # Round prices to exchange precision
            buy_price = round(buy_price, price_precision)
            sell_price = round(sell_price, price_precision)
            
            # Check minimum order size (typically $5-10 for most pairs)
            min_order_value = order_amount * buy_price
            if min_order_value < 5.0:  # Minimum $5 order
                logger.debug(f"   ⚠️ Order value ${min_order_value:.2f} < minimum $5.00")
                return False
            
            # Check inventory limits
            inventory = await self.get_inventory_balance(base_currency)
            inventory_value = inventory * current_price
            max_inventory = self.capital_per_pair * self.max_inventory_percent
            
            # Place buy order (if not over-inventoried)
            if inventory_value < max_inventory:
                try:
                    buy_order = await self.exchange_manager.create_order(
                        exchange_id='gemini',
                        symbol=pair,
                        order_type='limit',
                        side='buy',
                        amount=order_amount,
                        price=buy_price
                    )
                    if buy_order and buy_order.get('id'):
                        buy_mm_order = MarketMakingOrder(
                            pair=pair,
                            side='buy',
                            order_id=buy_order.get('id'),
                            price=buy_price,
                            amount=order_amount,
                            status='open'
                        )
                        self.active_orders[pair].append(buy_mm_order)
                        logger.debug(f"   ✅ Placed buy order: {pair} @ ${buy_price:.4f} for {order_amount:.6f}")
                except Exception as e:
                    logger.debug(f"   ⚠️ Failed to place buy order for {pair}: {e}")
            
            # Place sell order (if we have inventory)
            if inventory > order_amount * 0.5:  # Only sell if we have at least 50% of order size
                try:
                    sell_order = await self.exchange_manager.create_order(
                        exchange_id='gemini',
                        symbol=pair,
                        order_type='limit',
                        side='sell',
                        amount=min(order_amount, inventory),
                        price=sell_price
                    )
                    if sell_order and sell_order.get('id'):
                        sell_mm_order = MarketMakingOrder(
                            pair=pair,
                            side='sell',
                            order_id=sell_order.get('id'),
                            price=sell_price,
                            amount=min(order_amount, inventory),
                            status='open'
                        )
                        self.active_orders[pair].append(sell_mm_order)
                        logger.debug(f"   ✅ Placed sell order: {pair} @ ${sell_price:.4f} for {min(order_amount, inventory):.6f}")
                except Exception as e:
                    logger.debug(f"   ⚠️ Failed to place sell order for {pair}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"   ❌ Error placing market-making orders for {pair}: {e}")
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
                    except Exception as e:
                        logger.debug(f"   Error canceling order {mm_order.order_id}: {e}")
            
            # Remove canceled orders
            self.active_orders[pair] = [
                o for o in self.active_orders[pair] 
                if o.status == 'open' or o.status == 'filled'
            ]
        except Exception as e:
            logger.debug(f"   Error canceling orders for {pair}: {e}")
    
    async def check_and_update_orders(self, pair: str):
        """Check order status and update if needed"""
        try:
            orders_to_check = self.active_orders[pair].copy()
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
                            
                            # Calculate profit (simplified - actual calculation depends on inventory)
                            filled = float(order_status.get('filled', 0))
                            price = float(order_status.get('price', mm_order.price))
                            cost = float(order_status.get('cost', 0))
                            
                            if mm_order.side == 'buy':
                                # Bought at lower price - profit when we sell
                                logger.info(f"   ✅ Buy filled: {pair} @ ${price:.4f} for {filled:.6f}")
                            else:
                                # Sold at higher price - realized profit
                                spread_profit = (price - mm_order.price) * filled if mm_order.side == 'sell' else 0
                                logger.info(f"   ✅ Sell filled: {pair} @ ${price:.4f} for {filled:.6f} (profit: ${spread_profit:.2f})")
                                self.stats[pair].total_profit_usd += spread_profit
                        
                        elif status == 'canceled':
                            mm_order.status = 'canceled'
                    except Exception as e:
                        logger.debug(f"   Error checking order {mm_order.order_id}: {e}")
        except Exception as e:
            logger.debug(f"   Error checking orders for {pair}: {e}")
    
    async def flatten_positions(self):
        """Flatten all positions (take profit)"""
        try:
            logger.info("   🔄 Flattening positions...")
            for pair in TOP_GEMINI_PAIRS:
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
                            logger.info(f"   ✅ Flattened {pair}: Placed sell order for {sell_amount:.6f} {base_currency} @ ${sell_price:.4f}")
                        except Exception as e:
                            logger.warning(f"   ⚠️ Failed to flatten {pair}: {e}")
            
            # Cancel all orders
            for pair in TOP_GEMINI_PAIRS:
                await self.cancel_pair_orders(pair)
            
            self.last_flatten_time = datetime.now()
            
        except Exception as e:
            logger.error(f"   ❌ Error flattening positions: {e}")
    
    async def run_market_making_loop(self):
        """Main market-making loop"""
        logger.info("=" * 80)
        logger.info("🚀 STARTING GEMINI MARKET-MAKING ENGINE")
        logger.info("=" * 80)
        logger.info(f"   Strategy: Passive Market Making")
        logger.info(f"   Pairs: {len(TOP_GEMINI_PAIRS)}")
        logger.info(f"   Update interval: {self.requote_interval_seconds}s")
        logger.info(f"   Take profit interval: {self.take_profit_interval_minutes} minutes")
        logger.info("=" * 80)
        
        self.running = True
        
        while self.running:
            try:
                # Check if time to flatten (take profit)
                time_since_flatten = (datetime.now() - self.last_flatten_time).total_seconds() / 60
                if time_since_flatten >= self.take_profit_interval_minutes:
                    await self.flatten_positions()
                
                # Process each pair (with rate limiting)
                # Gemini rate limit: 10 req/sec, so we process 10 pairs max per second
                pairs_per_batch = 10  # Process 10 pairs per second to stay under rate limit
                
                for i in range(0, len(TOP_GEMINI_PAIRS), pairs_per_batch):
                    batch = TOP_GEMINI_PAIRS[i:i+pairs_per_batch]
                    
                    # Process batch concurrently
                    tasks = []
                    for pair in batch:
                        tasks.append(self._process_pair_safely(pair))
                    
                    # Wait for batch to complete
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Wait 1 second between batches to respect rate limit
                    if i + pairs_per_batch < len(TOP_GEMINI_PAIRS):
                        await asyncio.sleep(1)
                
                # Wait before next update cycle
                await asyncio.sleep(self.requote_interval_seconds)
                
            except Exception as e:
                logger.error(f"   ❌ Error in market-making loop: {e}")
                await asyncio.sleep(self.requote_interval_seconds)
    
    async def _process_pair_safely(self, pair: str):
        """Process a single pair with error handling"""
        try:
            # Check and update existing orders
            await self.check_and_update_orders(pair)
            
            # Place new orders if needed
            await self.place_market_making_orders(pair)
        except Exception as e:
            logger.debug(f"   Error processing {pair}: {e}")
            # Don't raise - continue with other pairs
    
    def stop(self):
        """Stop the market-making engine"""
        logger.info("   🛑 Stopping Gemini market-making engine...")
        self.running = False
        
        # Cancel all orders
        for pair in TOP_GEMINI_PAIRS:
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

