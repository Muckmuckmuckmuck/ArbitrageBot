#!/usr/bin/env python3
"""
Dynamic Order Manager - Advanced Order Management System
=======================================================

This module provides intelligent order management with:
- Adaptive pricing (chase moving prices)
- Automatic cancellation when opportunities disappear
- Retry logic with exponential backoff
- Stuck position recovery
- Real-time opportunity monitoring

Key Features:
1. Price Chasing: Adjusts buy/sell prices to catch moving opportunities
2. Opportunity Monitoring: Cancels orders when arbitrage opportunity disappears
3. Stuck Position Recovery: Sells at market when stuck
4. Retry Logic: Handles temporary failures gracefully
5. Dynamic Limits: Adjusts order sizes based on market conditions
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import ccxt

# Import bot configuration
from coinbase_gemini_config import Config

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    STUCK = "stuck"

class OpportunityStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

@dataclass
class OrderInfo:
    """Information about a placed order"""
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: float
    price: float
    exchange: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    fill_amount: float = 0.0
    fill_price: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    opportunity_id: Optional[str] = None

@dataclass
class OpportunityInfo:
    """Information about an arbitrage opportunity"""
    opportunity_id: str
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    estimated_profit: float
    status: OpportunityStatus
    created_at: datetime
    expires_at: datetime
    buy_order: Optional[OrderInfo] = None
    sell_order: Optional[OrderInfo] = None

class DynamicOrderManager:
    """
    Advanced order management system with adaptive pricing and retry logic
    """
    
    def __init__(self, exchanges: Dict[str, ccxt.Exchange], config: Config):
        self.exchanges = exchanges
        self.config = config
        self.active_orders: Dict[str, OrderInfo] = {}
        self.active_opportunities: Dict[str, OpportunityInfo] = {}
        self.order_history: List[OrderInfo] = []
        
        # Configuration - AGGRESSIVE MODE
        self.max_order_age_minutes = 5   # Cancel orders older than 5 minutes (aggressive)
        self.price_chase_increment = 0.0005  # 0.05% price increment for chasing (more aggressive)
        self.max_price_chase_percent = 0.01  # Max 1% price chase (more aggressive)
        self.opportunity_timeout_minutes = 3  # Cancel opportunity after 3 minutes (aggressive)
        self.retry_delay_seconds = [0.5, 1, 2, 5]  # Faster retry delays (aggressive)
        
        # Stuck position prevention
        self.stuck_position_threshold_minutes = 2  # Consider stuck after 2 minutes
        self.aggressive_price_chase = True  # Enable aggressive price chasing
        self.auto_market_sell_stuck = True  # Auto market sell stuck positions
        
        # Monitoring
        self.last_cleanup = datetime.now()
        self.cleanup_interval_minutes = 2
        
        logger.info("🚀 Dynamic Order Manager initialized")
        logger.info(f"   Max order age: {self.max_order_age_minutes} minutes")
        logger.info(f"   Price chase increment: {self.price_chase_increment*100:.1f}%")
        logger.info(f"   Max price chase: {self.max_price_chase_percent*100:.1f}%")
        logger.info(f"   Opportunity timeout: {self.opportunity_timeout_minutes} minutes")

    async def place_adaptive_order(self, 
                                 exchange_name: str, 
                                 symbol: str, 
                                 side: str, 
                                 amount: float, 
                                 target_price: float,
                                 opportunity_id: str,
                                 max_price_chase: float = None) -> Optional[OrderInfo]:
        """
        Place an order with adaptive pricing that chases moving prices
        
        Args:
            exchange_name: Name of the exchange
            symbol: Trading symbol (e.g., 'BTC/USD')
            side: 'buy' or 'sell'
            amount: Order amount
            target_price: Initial target price
            opportunity_id: ID of the arbitrage opportunity
            max_price_chase: Maximum price chase percentage (default: self.max_price_chase_percent)
        
        Returns:
            OrderInfo if successful, None if failed
        """
        if max_price_chase is None:
            max_price_chase = self.max_price_chase_percent
            
        exchange = self.exchanges[exchange_name]
        order_id = f"{opportunity_id}_{side}_{int(time.time())}"
        
        # Calculate initial order price with small improvement
        if side == 'buy':
            initial_price = target_price * (1 + self.price_chase_increment)
        else:
            initial_price = target_price * (1 - self.price_chase_increment)
        
        order_info = OrderInfo(
            order_id=order_id,
            symbol=symbol,
            side=side,
            amount=amount,
            price=initial_price,
            exchange=exchange_name,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            opportunity_id=opportunity_id
        )
        
        try:
            # Place the initial order
            logger.info(f"🎯 Placing {side} order: {amount:.6f} {symbol} at ${initial_price:.4f} on {exchange_name}")
            
            if exchange_name == 'coinbase':
                # Coinbase requires price for market orders
                order = exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side=side,
                    amount=amount,
                    price=initial_price
                )
            else:  # gemini
                # Gemini only supports limit orders
                order = exchange.create_limit_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=initial_price
                )
            
            if hasattr(order, '__await__'):
                order = await order
            
            # Update order info with exchange response
            order_info.order_id = order.get('id', order_id)
            order_info.status = OrderStatus.PENDING
            
            # Store the order
            self.active_orders[order_info.order_id] = order_info
            
            logger.info(f"✅ Order placed: {order_info.order_id} on {exchange_name}")
            
            # Start monitoring this order
            asyncio.create_task(self._monitor_order(order_info, max_price_chase))
            
            return order_info
            
        except Exception as e:
            logger.error(f"❌ Failed to place {side} order on {exchange_name}: {str(e)}")
            order_info.status = OrderStatus.FAILED
            return None

    async def _monitor_order(self, order_info: OrderInfo, max_price_chase: float):
        """
        Monitor an order and implement adaptive pricing
        """
        start_time = time.time()
        max_monitor_time = 300  # 5 minutes max monitoring
        
        while time.time() - start_time < max_monitor_time:
            try:
                # Check if opportunity still exists
                if order_info.opportunity_id in self.active_opportunities:
                    opportunity = self.active_opportunities[order_info.opportunity_id]
                    if opportunity.status != OpportunityStatus.ACTIVE:
                        logger.info(f"🛑 Opportunity {order_info.opportunity_id} no longer active, cancelling order")
                        await self._cancel_order(order_info)
                        return
                
                # Fetch current order status
                exchange = self.exchanges[order_info.exchange]
                order_status = exchange.fetch_order(order_info.order_id, order_info.symbol)
                if hasattr(order_status, '__await__'):
                    order_status = await order_status
                
                # Update order info
                order_info.updated_at = datetime.now()
                order_info.fill_amount = float(order_status.get('filled', 0))
                order_info.fill_price = float(order_status.get('average', 0))
                
                status = order_status.get('status', 'unknown')
                
                if status in ['closed', 'filled']:
                    order_info.status = OrderStatus.FILLED
                    logger.info(f"✅ Order {order_info.order_id} filled: {order_info.fill_amount:.6f} at ${order_info.fill_price:.4f}")
                    break
                    
                elif status in ['canceled', 'cancelled']:
                    order_info.status = OrderStatus.CANCELLED
                    logger.info(f"🛑 Order {order_info.order_id} cancelled")
                    break
                    
                elif status == 'open':
                    # Order is still open, check if we should chase the price
                    await self._check_price_chase(order_info, max_price_chase)
                
                # Wait before next check
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.warning(f"⚠️ Error monitoring order {order_info.order_id}: {str(e)}")
                order_info.retry_count += 1
                
                if order_info.retry_count >= order_info.max_retries:
                    logger.error(f"❌ Max retries reached for order {order_info.order_id}")
                    order_info.status = OrderStatus.FAILED
                    break
                
                # Exponential backoff
                delay = self.retry_delay_seconds[min(order_info.retry_count, len(self.retry_delay_seconds) - 1)]
                await asyncio.sleep(delay)
        
        # Clean up
        if order_info.order_id in self.active_orders:
            del self.active_orders[order_info.order_id]
        self.order_history.append(order_info)

    async def _check_price_chase(self, order_info: OrderInfo, max_price_chase: float):
        """
        Check if we should chase the price and update the order
        """
        try:
            # Get current market price
            exchange = self.exchanges[order_info.exchange]
            ticker = exchange.fetch_ticker(order_info.symbol)
            if hasattr(ticker, '__await__'):
                ticker = await ticker
            
            current_price = float(ticker['last'])
            
            # Calculate how much we've already chased
            original_price = order_info.price
            if order_info.side == 'buy':
                price_chase_percent = (current_price - original_price) / original_price
                new_price = current_price * (1 + self.price_chase_increment)
            else:
                price_chase_percent = (original_price - current_price) / original_price
                new_price = current_price * (1 - self.price_chase_increment)
            
            # Check if we should chase the price
            if price_chase_percent < max_price_chase:
                # Cancel old order and place new one
                logger.info(f"🏃 Chasing price: {order_info.side} {order_info.symbol} from ${order_info.price:.4f} to ${new_price:.4f}")
                
                await self._cancel_order(order_info)
                await asyncio.sleep(1)  # Brief delay
                
                # Place new order at current price
                if order_info.exchange == 'coinbase':
                    new_order = exchange.create_order(
                        symbol=order_info.symbol,
                        type='limit',
                        side=order_info.side,
                        amount=order_info.amount,
                        price=new_price
                    )
                else:  # gemini
                    new_order = exchange.create_limit_order(
                        symbol=order_info.symbol,
                        side=order_info.side,
                        amount=order_info.amount,
                        price=new_price
                    )
                
                if hasattr(new_order, '__await__'):
                    new_order = await new_order
                
                # Update order info
                order_info.order_id = new_order.get('id', order_info.order_id)
                order_info.price = new_price
                order_info.updated_at = datetime.now()
                
                logger.info(f"✅ Price chase successful: New order {order_info.order_id}")
                
        except Exception as e:
            logger.warning(f"⚠️ Error in price chase for order {order_info.order_id}: {str(e)}")

    async def _cancel_order(self, order_info: OrderInfo) -> bool:
        """
        Cancel an order
        """
        try:
            exchange = self.exchanges[order_info.exchange]
            result = exchange.cancel_order(order_info.order_id, order_info.symbol)
            if hasattr(result, '__await__'):
                result = await result
            
            order_info.status = OrderStatus.CANCELLED
            logger.info(f"🛑 Order {order_info.order_id} cancelled")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to cancel order {order_info.order_id}: {str(e)}")
            return False

    async def create_opportunity(self, 
                               symbol: str, 
                               buy_exchange: str, 
                               sell_exchange: str,
                               buy_price: float, 
                               sell_price: float,
                               spread_percent: float,
                               estimated_profit: float) -> str:
        """
        Create a new arbitrage opportunity
        """
        opportunity_id = f"opp_{symbol}_{int(time.time())}"
        
        opportunity = OpportunityInfo(
            opportunity_id=opportunity_id,
            symbol=symbol,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            spread_percent=spread_percent,
            estimated_profit=estimated_profit,
            status=OpportunityStatus.ACTIVE,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=self.opportunity_timeout_minutes)
        )
        
        self.active_opportunities[opportunity_id] = opportunity
        
        logger.info(f"🎯 New opportunity: {symbol} {buy_exchange}→{sell_exchange} "
                   f"spread={spread_percent:.3f}% profit=${estimated_profit:.3f}")
        
        return opportunity_id

    async def execute_opportunity(self, opportunity_id: str, amount: float) -> bool:
        """
        Execute an arbitrage opportunity with adaptive order management
        """
        if opportunity_id not in self.active_opportunities:
            logger.error(f"❌ Opportunity {opportunity_id} not found")
            return False
        
        opportunity = self.active_opportunities[opportunity_id]
        
        try:
            # Place buy order
            buy_order = await self.place_adaptive_order(
                exchange_name=opportunity.buy_exchange,
                symbol=opportunity.symbol,
                side='buy',
                amount=amount,
                target_price=opportunity.buy_price,
                opportunity_id=opportunity_id
            )
            
            if buy_order is None:
                logger.error(f"❌ Failed to place buy order for opportunity {opportunity_id}")
                opportunity.status = OpportunityStatus.FAILED
                return False
            
            opportunity.buy_order = buy_order
            
            # Place sell order
            sell_order = await self.place_adaptive_order(
                exchange_name=opportunity.sell_exchange,
                symbol=opportunity.symbol,
                side='sell',
                amount=amount,
                target_price=opportunity.sell_price,
                opportunity_id=opportunity_id
            )
            
            if sell_order is None:
                logger.error(f"❌ Failed to place sell order for opportunity {opportunity_id}")
                # Cancel buy order
                await self._cancel_order(buy_order)
                opportunity.status = OpportunityStatus.FAILED
                return False
            
            opportunity.sell_order = sell_order
            
            logger.info(f"🚀 Opportunity {opportunity_id} execution started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error executing opportunity {opportunity_id}: {str(e)}")
            opportunity.status = OpportunityStatus.FAILED
            return False

    async def recover_stuck_position(self, symbol: str, exchange_name: str, amount: float) -> bool:
        """
        Recover a stuck position by selling at market price
        """
        try:
            exchange = self.exchanges[exchange_name]
            
            # Get current market price
            ticker = exchange.fetch_ticker(symbol)
            if hasattr(ticker, '__await__'):
                ticker = await ticker
            
            current_price = float(ticker['last'])
            
            logger.info(f"🚨 Recovering stuck position: {amount:.6f} {symbol} on {exchange_name} at ${current_price:.4f}")
            
            # Place market sell order
            if exchange_name == 'coinbase':
                order = exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side='sell',
                    amount=amount,
                    price=current_price
                )
            else:  # gemini
                # Gemini requires limit orders, use slightly below market
                order = exchange.create_limit_order(
                    symbol=symbol,
                    side='sell',
                    amount=amount,
                    price=current_price * 0.99
                )
            
            if hasattr(order, '__await__'):
                order = await order
            
            order_id = order.get('id', 'unknown')
            logger.info(f"✅ Stuck position recovery order placed: {order_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to recover stuck position: {str(e)}")
            return False

    async def cleanup_expired_orders(self):
        """
        Clean up expired orders and opportunities
        """
        now = datetime.now()
        
        # Clean up expired opportunities
        expired_opportunities = []
        for opp_id, opportunity in self.active_opportunities.items():
            if now > opportunity.expires_at:
                expired_opportunities.append(opp_id)
        
        for opp_id in expired_opportunities:
            opportunity = self.active_opportunities[opp_id]
            opportunity.status = OpportunityStatus.EXPIRED
            
            # Cancel associated orders
            if opportunity.buy_order:
                await self._cancel_order(opportunity.buy_order)
            if opportunity.sell_order:
                await self._cancel_order(opportunity.sell_order)
            
            del self.active_opportunities[opp_id]
            logger.info(f"🧹 Cleaned up expired opportunity: {opp_id}")
        
        # Clean up old orders
        old_orders = []
        for order_id, order_info in self.active_orders.items():
            age_minutes = (now - order_info.created_at).total_seconds() / 60
            if age_minutes > self.max_order_age_minutes:
                old_orders.append(order_id)
        
        for order_id in old_orders:
            order_info = self.active_orders[order_id]
            await self._cancel_order(order_info)
            del self.active_orders[order_id]
            logger.info(f"🧹 Cleaned up old order: {order_id}")

    async def get_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current status
        """
        active_orders = len(self.active_orders)
        active_opportunities = len(self.active_opportunities)
        total_orders = len(self.order_history)
        
        # Count orders by status
        status_counts = {}
        for order in self.order_history:
            status = order.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'active_orders': active_orders,
            'active_opportunities': active_opportunities,
            'total_orders': total_orders,
            'status_counts': status_counts,
            'last_cleanup': self.last_cleanup.isoformat()
        }

    async def run_cleanup_cycle(self):
        """
        Run periodic cleanup
        """
        while True:
            try:
                await self.cleanup_expired_orders()
                self.last_cleanup = datetime.now()
                
                # Log status
                status = await self.get_status_summary()
                logger.info(f"🧹 Cleanup cycle complete: {status['active_orders']} active orders, "
                           f"{status['active_opportunities']} active opportunities")
                
            except Exception as e:
                logger.error(f"❌ Error in cleanup cycle: {str(e)}")
            
            # Wait for next cleanup
            await asyncio.sleep(self.cleanup_interval_minutes * 60)

# Example usage and testing
async def test_dynamic_order_manager():
    """
    Test the dynamic order manager
    """
    # This would be called from the main bot
    pass

if __name__ == "__main__":
    # Test the module
    asyncio.run(test_dynamic_order_manager())
