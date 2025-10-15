"""
Smart Order Placer - Uses Limit Orders to Pay Maker Fees (0.50% vs 0.95%)
Saves 47% on trading fees!
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SmartOrderPlacer:
    """
    Places limit orders that become maker orders to minimize fees.
    
    Maker Fees:
        Coinbase: 0.40%
        Gemini: 0.10%
        Total: 0.50%
    
    Taker Fees (what we're avoiding):
        Coinbase: 0.60%
        Gemini: 0.35%
        Total: 0.95%
    
    Savings: 47%!
    """
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.logger = logger
        
        # Limit order configuration
        self.MAX_WAIT_TIME = 10  # Max seconds to wait for fill (reduced from 30)
        self.PRICE_IMPROVEMENT = 0.0001  # 0.01% better than market (more aggressive, fills faster)
        self.CHECK_INTERVAL = 0.5  # Check order status every 0.5 seconds
    
    async def place_smart_buy(
        self,
        exchange_id: str,
        symbol: str,
        amount: float,
        current_ask: float
    ) -> Dict:
        """
        Place a limit buy order at a price slightly better than market ask.
        This ensures we're a maker (adding liquidity) and pay lower fees.
        
        Strategy:
        1. Place limit buy at current_ask - 0.05% (better for us, maker fee)
        2. Wait up to 30 seconds for fill
        3. If not filled, cancel and place slightly higher (still below ask)
        4. Repeat until filled or max attempts
        """
        self.logger.info(f"[SMART BUY] Placing limit buy for {symbol} on {exchange_id}")
        
        # Calculate limit price (slightly below market ask = maker order)
        limit_price = current_ask * (1 - self.PRICE_IMPROVEMENT)
        self.logger.info(f"   Market Ask: ${current_ask:.6f}")
        self.logger.info(f"   Limit Price: ${limit_price:.6f} (0.01% better - AGGRESSIVE)")
        
        try:
            # Place limit buy order
            order = await self.exchange_manager.create_order(
                exchange_id=exchange_id,
                symbol=symbol,
                order_type='limit',  # LIMIT ORDER = MAKER FEE
                side='buy',
                amount=amount,
                price=limit_price
            )
            
            order_id = order['id']
            self.logger.info(f"   Order placed: {order_id}")
            
            # Wait for order to fill
            filled_order = await self._wait_for_fill(
                exchange_id, order_id, symbol, 'buy'
            )
            
            if filled_order:
                self.logger.info(f"✅ Limit buy filled: {amount:.8f} @ ${filled_order['average']:.6f}")
                self.logger.info(f"   Fee Type: MAKER (0.40-0.10% instead of 0.60-0.35%)")
                return filled_order
            
            # If not filled, cancel and use market order as fallback
            self.logger.warning(f"⚠️  Limit order not filled, using market order")
            await self._cancel_order(exchange_id, order_id, symbol)
            
            return await self._fallback_market_order(
                exchange_id, symbol, 'buy', amount, current_ask
            )
            
        except Exception as e:
            self.logger.error(f"❌ Smart buy failed: {e}")
            # Fallback to market order
            return await self._fallback_market_order(
                exchange_id, symbol, 'buy', amount, current_ask
            )
    
    async def place_smart_sell(
        self,
        exchange_id: str,
        symbol: str,
        amount: float,
        current_bid: float
    ) -> Dict:
        """
        Place a limit sell order at a price slightly better than market bid.
        This ensures we're a maker (adding liquidity) and pay lower fees.
        
        Strategy:
        1. Place limit sell at current_bid + 0.05% (better for us, maker fee)
        2. Wait up to 30 seconds for fill
        3. If not filled, cancel and place slightly lower (still above bid)
        4. Repeat until filled or max attempts
        """
        self.logger.info(f"[SMART SELL] Placing limit sell for {symbol} on {exchange_id}")
        
        # Calculate limit price (slightly above market bid = maker order)
        limit_price = current_bid * (1 + self.PRICE_IMPROVEMENT)
        self.logger.info(f"   Market Bid: ${current_bid:.6f}")
        self.logger.info(f"   Limit Price: ${limit_price:.6f} (0.01% better - AGGRESSIVE)")
        
        try:
            # Place limit sell order
            order = await self.exchange_manager.create_order(
                exchange_id=exchange_id,
                symbol=symbol,
                order_type='limit',  # LIMIT ORDER = MAKER FEE
                side='sell',
                amount=amount,
                price=limit_price
            )
            
            order_id = order['id']
            self.logger.info(f"   Order placed: {order_id}")
            
            # Wait for order to fill
            filled_order = await self._wait_for_fill(
                exchange_id, order_id, symbol, 'sell'
            )
            
            if filled_order:
                self.logger.info(f"✅ Limit sell filled: {amount:.8f} @ ${filled_order['average']:.6f}")
                self.logger.info(f"   Fee Type: MAKER (0.40-0.10% instead of 0.60-0.35%)")
                return filled_order
            
            # If not filled, cancel and use market order as fallback
            self.logger.warning(f"⚠️  Limit order not filled, using market order")
            await self._cancel_order(exchange_id, order_id, symbol)
            
            return await self._fallback_market_order(
                exchange_id, symbol, 'sell', amount, current_bid
            )
            
        except Exception as e:
            self.logger.error(f"❌ Smart sell failed: {e}")
            # Fallback to market order
            return await self._fallback_market_order(
                exchange_id, symbol, 'sell', amount, current_bid
            )
    
    async def _wait_for_fill(
        self,
        exchange_id: str,
        order_id: str,
        symbol: str,
        side: str
    ) -> Optional[Dict]:
        """Wait for order to fill, checking periodically"""
        elapsed = 0
        
        while elapsed < self.MAX_WAIT_TIME:
            await asyncio.sleep(self.CHECK_INTERVAL)
            elapsed += self.CHECK_INTERVAL
            
            try:
                order = await self.exchange_manager.fetch_order(
                    exchange_id, order_id, symbol
                )
                
                status = order.get('status', 'open')
                
                if status == 'closed' or status == 'filled':
                    return order
                
                if status == 'canceled':
                    return None
                
                # Log progress
                filled = order.get('filled', 0)
                if filled > 0:
                    self.logger.info(f"   Partially filled: {filled:.8f}")
                
            except Exception as e:
                self.logger.warning(f"Error checking order: {e}")
        
        # Timeout
        self.logger.warning(f"Order not filled after {self.MAX_WAIT_TIME}s")
        return None
    
    async def _cancel_order(
        self,
        exchange_id: str,
        order_id: str,
        symbol: str
    ):
        """Cancel an order"""
        try:
            await self.exchange_manager.cancel_order(
                exchange_id, order_id, symbol
            )
            self.logger.info(f"Order {order_id} canceled")
        except Exception as e:
            self.logger.warning(f"Failed to cancel order: {e}")
    
    async def _fallback_market_order(
        self,
        exchange_id: str,
        symbol: str,
        side: str,
        amount: float,
        current_price: Optional[float] = None
    ) -> Dict:
        """Fallback to market order if limit order fails"""
        self.logger.warning(f"Using market order (taker fees) as fallback")
        
        # For Coinbase market buy orders, CCXT requires createMarketBuyOrderRequiresPrice=False
        # OR passing the cost in the 'amount' parameter
        # We'll get the current price and pass the cost for buy orders on Coinbase
        if exchange_id == 'coinbase' and side == 'buy' and current_price:
            # Coinbase market buy orders expect the cost (quote currency amount)
            cost = amount * current_price
            self.logger.info(f"   Coinbase market buy: ${cost:.2f} worth of {symbol}")
            
            # Use the exchange's createMarketBuyOrderRequiresPrice workaround
            order = await self.exchange_manager.create_order(
                exchange_id=exchange_id,
                symbol=symbol,
                order_type='market',
                side=side,
                amount=amount,
                price=current_price  # Pass price for Coinbase to calculate cost
            )
        else:
            # Standard market order for other exchanges or sell orders
            order = await self.exchange_manager.create_order(
                exchange_id=exchange_id,
                symbol=symbol,
                order_type='market',
                side=side,
                amount=amount
            )
        
        await asyncio.sleep(1)
        
        filled_order = await self.exchange_manager.fetch_order(
            exchange_id, order['id'], symbol
        )
        
        return filled_order

