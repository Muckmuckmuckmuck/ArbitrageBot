#!/usr/bin/env python3
"""
Stuck Position Recovery System - Enterprise Grade
================================================

This module provides comprehensive stuck position recovery with:
- Real-time position tracking
- Automatic market sell for stuck positions
- Position risk assessment
- Recovery strategy optimization
- Performance monitoring

Key Features:
1. Position Tracking: Real-time monitoring of all positions
2. Market Sell Recovery: Automatic market sell when stuck
3. Risk Assessment: Evaluate position risk levels
4. Recovery Strategies: Multiple recovery approaches
5. Performance Monitoring: Track recovery success rates
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
from enhanced_retry_logic import enhanced_retry_logic

logger = logging.getLogger(__name__)

class PositionStatus(Enum):
    """Position status enumeration"""
    ACTIVE = "active"           # Position is active and trading
    STUCK = "stuck"            # Position is stuck and needs recovery
    RECOVERING = "recovering"   # Position is being recovered
    RECOVERED = "recovered"     # Position has been recovered
    FAILED = "failed"          # Recovery failed

class RecoveryStrategy(Enum):
    """Recovery strategy enumeration"""
    MARKET_SELL = "market_sell"           # Sell at market price
    LIMIT_SELL = "limit_sell"             # Sell with limit order
    TRANSFER_AND_SELL = "transfer_and_sell"  # Transfer to other exchange and sell
    WAIT_AND_RECOVER = "wait_and_recover"    # Wait for better price

@dataclass
class Position:
    """Information about a trading position"""
    position_id: str
    symbol: str
    exchange: str
    side: str  # 'buy' or 'sell'
    amount: float
    entry_price: float
    current_price: float
    status: PositionStatus
    created_at: datetime
    updated_at: datetime
    stuck_duration_minutes: float = 0.0
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    risk_level: str = "low"  # low, medium, high
    estimated_loss: float = 0.0
    recovery_strategy: Optional[RecoveryStrategy] = None

@dataclass
class RecoveryResult:
    """Result of a recovery operation"""
    success: bool
    recovered_amount: float
    recovered_price: float
    recovery_time_minutes: float
    strategy_used: RecoveryStrategy
    error_message: Optional[str] = None

class StuckPositionRecovery:
    """
    Comprehensive stuck position recovery system
    """
    
    def __init__(self, exchanges: Dict[str, ccxt.Exchange], config: Config):
        self.exchanges = exchanges
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.recovery_history: List[RecoveryResult] = []
        
        # Configuration
        self.stuck_threshold_minutes = 10  # Consider stuck after 10 minutes
        self.max_stuck_duration_minutes = 60  # Force recovery after 60 minutes
        self.price_deviation_threshold = 0.05  # 5% price deviation triggers recovery
        self.min_recovery_amount = 0.001  # Minimum amount to recover
        
        # Monitoring
        self.last_scan = datetime.now()
        self.scan_interval_minutes = 2
        
        logger.info("🚀 Stuck Position Recovery System initialized")
        logger.info(f"   Stuck threshold: {self.stuck_threshold_minutes} minutes")
        logger.info(f"   Max stuck duration: {self.max_stuck_duration_minutes} minutes")
        logger.info(f"   Price deviation threshold: {self.price_deviation_threshold*100:.1f}%")

    async def scan_for_stuck_positions(self) -> List[Position]:
        """
        Scan for stuck positions across all exchanges
        """
        stuck_positions = []
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                # Get current balance
                balance = await enhanced_retry_logic.execute_with_retry(
                    exchange.fetch_balance,
                    'fetch_balance',
                    exchange_name
                )
                
                if hasattr(balance, '__await__'):
                    balance = await balance
                
                # Check each crypto in the balance
                free_balances = balance.get('free', {})
                
                for currency, amount in free_balances.items():
                    if amount > self.min_recovery_amount:
                        # Check if this is a stuck position
                        position = await self._check_position_status(
                            exchange_name, currency, amount
                        )
                        
                        if position and position.status == PositionStatus.STUCK:
                            stuck_positions.append(position)
                            self.positions[position.position_id] = position
                
            except Exception as e:
                logger.error(f"❌ Error scanning {exchange_name} for stuck positions: {str(e)}")
        
        if stuck_positions:
            logger.warning(f"🚨 Found {len(stuck_positions)} stuck positions")
            for position in stuck_positions:
                logger.warning(f"   {position.symbol} on {position.exchange}: {position.amount:.6f} "
                             f"(stuck for {position.stuck_duration_minutes:.1f} minutes)")
        
        return stuck_positions

    async def _check_position_status(self, 
                                   exchange_name: str, 
                                   currency: str, 
                                   amount: float) -> Optional[Position]:
        """
        Check if a position is stuck
        """
        try:
            # Create position ID
            position_id = f"{exchange_name}_{currency}_{int(time.time())}"
            
            # Get current price
            symbol = f"{currency}/USD"
            ticker = await enhanced_retry_logic.execute_with_retry(
                self.exchanges[exchange_name].fetch_ticker,
                'fetch_ticker',
                exchange_name,
                symbol
            )
            
            if hasattr(ticker, '__await__'):
                ticker = await ticker
            
            current_price = float(ticker['last'])
            
            # Check if position exists in our tracking
            existing_position = None
            for pos in self.positions.values():
                if (pos.exchange == exchange_name and 
                    pos.symbol == symbol and 
                    pos.status in [PositionStatus.ACTIVE, PositionStatus.STUCK]):
                    existing_position = pos
                    break
            
            if existing_position:
                # Update existing position
                existing_position.updated_at = datetime.now()
                existing_position.current_price = current_price
                existing_position.amount = amount
                
                # Calculate stuck duration
                stuck_duration = (datetime.now() - existing_position.created_at).total_seconds() / 60
                existing_position.stuck_duration_minutes = stuck_duration
                
                # Determine if position is stuck
                if stuck_duration > self.stuck_threshold_minutes:
                    existing_position.status = PositionStatus.STUCK
                    existing_position.risk_level = self._assess_risk_level(existing_position)
                
                return existing_position
            else:
                # Create new position
                position = Position(
                    position_id=position_id,
                    symbol=symbol,
                    exchange=exchange_name,
                    side='sell',  # We want to sell stuck positions
                    amount=amount,
                    entry_price=current_price,  # Use current price as entry
                    current_price=current_price,
                    status=PositionStatus.ACTIVE,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                return position
                
        except Exception as e:
            logger.warning(f"⚠️ Error checking position status for {currency} on {exchange_name}: {str(e)}")
            return None

    def _assess_risk_level(self, position: Position) -> str:
        """
        Assess the risk level of a stuck position
        """
        # Calculate price deviation
        price_deviation = abs(position.current_price - position.entry_price) / position.entry_price
        
        # Calculate estimated loss
        position.estimated_loss = position.amount * (position.entry_price - position.current_price)
        
        # Determine risk level
        if position.stuck_duration_minutes > 120 or price_deviation > 0.1:
            return "high"
        elif position.stuck_duration_minutes > 60 or price_deviation > 0.05:
            return "medium"
        else:
            return "low"

    async def recover_stuck_position(self, position: Position) -> RecoveryResult:
        """
        Recover a stuck position using the best strategy
        """
        start_time = datetime.now()
        
        try:
            # Determine recovery strategy
            strategy = self._determine_recovery_strategy(position)
            position.recovery_strategy = strategy
            
            logger.info(f"🔄 Recovering {position.symbol} on {position.exchange} "
                       f"using {strategy.value} strategy")
            
            # Execute recovery
            if strategy == RecoveryStrategy.MARKET_SELL:
                result = await self._market_sell_recovery(position)
            elif strategy == RecoveryStrategy.LIMIT_SELL:
                result = await self._limit_sell_recovery(position)
            elif strategy == RecoveryStrategy.TRANSFER_AND_SELL:
                result = await self._transfer_and_sell_recovery(position)
            else:
                result = await self._wait_and_recover(position)
            
            # Calculate recovery time
            recovery_time = (datetime.now() - start_time).total_seconds() / 60
            
            # Create recovery result
            recovery_result = RecoveryResult(
                success=result['success'],
                recovered_amount=result.get('amount', 0),
                recovered_price=result.get('price', 0),
                recovery_time_minutes=recovery_time,
                strategy_used=strategy,
                error_message=result.get('error')
            )
            
            # Update position status
            if recovery_result.success:
                position.status = PositionStatus.RECOVERED
                logger.info(f"✅ Successfully recovered {position.symbol} on {position.exchange}")
            else:
                position.status = PositionStatus.FAILED
                position.recovery_attempts += 1
                logger.error(f"❌ Failed to recover {position.symbol} on {position.exchange}")
            
            # Store recovery result
            self.recovery_history.append(recovery_result)
            
            return recovery_result
            
        except Exception as e:
            logger.error(f"❌ Error recovering position {position.position_id}: {str(e)}")
            
            recovery_result = RecoveryResult(
                success=False,
                recovered_amount=0,
                recovered_price=0,
                recovery_time_minutes=(datetime.now() - start_time).total_seconds() / 60,
                strategy_used=position.recovery_strategy or RecoveryStrategy.MARKET_SELL,
                error_message=str(e)
            )
            
            position.status = PositionStatus.FAILED
            position.recovery_attempts += 1
            
            self.recovery_history.append(recovery_result)
            return recovery_result

    def _determine_recovery_strategy(self, position: Position) -> RecoveryStrategy:
        """
        Determine the best recovery strategy for a position
        """
        # High risk positions: immediate market sell
        if position.risk_level == "high":
            return RecoveryStrategy.MARKET_SELL
        
        # Medium risk positions: try limit sell first
        elif position.risk_level == "medium":
            return RecoveryStrategy.LIMIT_SELL
        
        # Low risk positions: wait and recover
        else:
            return RecoveryStrategy.WAIT_AND_RECOVER

    async def _market_sell_recovery(self, position: Position) -> Dict[str, Any]:
        """
        Recover position using market sell
        """
        try:
            exchange = self.exchanges[position.exchange]
            
            logger.info(f"💰 Market selling {position.amount:.6f} {position.symbol} on {position.exchange}")
            
            # Place market sell order
            if position.exchange == 'coinbase':
                order = await enhanced_retry_logic.execute_with_retry(
                    exchange.create_order,
                    'create_order',
                    position.exchange,
                    symbol=position.symbol,
                    type='market',
                    side='sell',
                    amount=position.amount,
                    price=position.current_price
                )
            else:  # gemini
                # Gemini requires limit orders, use slightly below market
                order = await enhanced_retry_logic.execute_with_retry(
                    exchange.create_limit_order,
                    'create_order',
                    position.exchange,
                    symbol=position.symbol,
                    side='sell',
                    amount=position.amount,
                    price=position.current_price * 0.99
                )
            
            if hasattr(order, '__await__'):
                order = await order
            
            order_id = order.get('id', 'unknown')
            logger.info(f"✅ Market sell order placed: {order_id}")
            
            # Wait for fill
            await asyncio.sleep(5)
            
            # Check order status
            order_status = await enhanced_retry_logic.execute_with_retry(
                exchange.fetch_order,
                'fetch_order',
                position.exchange,
                order_id,
                position.symbol
            )
            
            if hasattr(order_status, '__await__'):
                order_status = await order_status
            
            filled_amount = float(order_status.get('filled', 0))
            average_price = float(order_status.get('average', position.current_price))
            
            return {
                'success': True,
                'amount': filled_amount,
                'price': average_price
            }
            
        except Exception as e:
            logger.error(f"❌ Market sell recovery failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _limit_sell_recovery(self, position: Position) -> Dict[str, Any]:
        """
        Recover position using limit sell
        """
        try:
            exchange = self.exchanges[position.exchange]
            
            # Use slightly below market price for quick fill
            limit_price = position.current_price * 0.98
            
            logger.info(f"💰 Limit selling {position.amount:.6f} {position.symbol} at ${limit_price:.4f} on {position.exchange}")
            
            # Place limit sell order
            order = await enhanced_retry_logic.execute_with_retry(
                exchange.create_limit_order,
                'create_order',
                position.exchange,
                symbol=position.symbol,
                side='sell',
                amount=position.amount,
                price=limit_price
            )
            
            if hasattr(order, '__await__'):
                order = await order
            
            order_id = order.get('id', 'unknown')
            logger.info(f"✅ Limit sell order placed: {order_id}")
            
            # Wait for fill (up to 2 minutes)
            max_wait_time = 120
            check_interval = 10
            elapsed = 0
            
            while elapsed < max_wait_time:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                # Check order status
                order_status = await enhanced_retry_logic.execute_with_retry(
                    exchange.fetch_order,
                    'fetch_order',
                    position.exchange,
                    order_id,
                    position.symbol
                )
                
                if hasattr(order_status, '__await__'):
                    order_status = await order_status
                
                status = order_status.get('status', 'unknown')
                
                if status in ['closed', 'filled']:
                    filled_amount = float(order_status.get('filled', 0))
                    average_price = float(order_status.get('average', limit_price))
                    
                    return {
                        'success': True,
                        'amount': filled_amount,
                        'price': average_price
                    }
                elif status in ['canceled', 'cancelled']:
                    # Order was cancelled, fall back to market sell
                    logger.warning(f"⚠️ Limit sell order cancelled, falling back to market sell")
                    return await self._market_sell_recovery(position)
            
            # Timeout - cancel order and fall back to market sell
            logger.warning(f"⚠️ Limit sell order timeout, cancelling and falling back to market sell")
            
            try:
                await enhanced_retry_logic.execute_with_retry(
                    exchange.cancel_order,
                    'cancel_order',
                    position.exchange,
                    order_id,
                    position.symbol
                )
            except:
                pass  # Ignore cancellation errors
            
            return await self._market_sell_recovery(position)
            
        except Exception as e:
            logger.error(f"❌ Limit sell recovery failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _transfer_and_sell_recovery(self, position: Position) -> Dict[str, Any]:
        """
        Recover position by transferring to other exchange and selling
        """
        try:
            # Find the other exchange
            other_exchange = None
            for exchange_name in self.exchanges:
                if exchange_name != position.exchange:
                    other_exchange = exchange_name
                    break
            
            if not other_exchange:
                logger.error("❌ No other exchange available for transfer")
                return {
                    'success': False,
                    'error': 'No other exchange available'
                }
            
            logger.info(f"🔄 Transferring {position.amount:.6f} {position.symbol} "
                       f"from {position.exchange} to {other_exchange}")
            
            # This would implement the transfer logic
            # For now, fall back to market sell
            logger.warning("⚠️ Transfer and sell not implemented, falling back to market sell")
            return await self._market_sell_recovery(position)
            
        except Exception as e:
            logger.error(f"❌ Transfer and sell recovery failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _wait_and_recover(self, position: Position) -> Dict[str, Any]:
        """
        Wait for better price and then recover
        """
        try:
            logger.info(f"⏳ Waiting for better price for {position.symbol} on {position.exchange}")
            
            # Wait for 5 minutes and check price
            await asyncio.sleep(300)
            
            # Get current price
            ticker = await enhanced_retry_logic.execute_with_retry(
                self.exchanges[position.exchange].fetch_ticker,
                'fetch_ticker',
                position.exchange,
                position.symbol
            )
            
            if hasattr(ticker, '__await__'):
                ticker = await ticker
            
            current_price = float(ticker['last'])
            
            # If price improved, use limit sell, otherwise market sell
            if current_price > position.current_price * 1.01:  # 1% improvement
                logger.info(f"📈 Price improved to ${current_price:.4f}, using limit sell")
                position.current_price = current_price
                return await self._limit_sell_recovery(position)
            else:
                logger.info(f"📉 Price didn't improve, using market sell")
                position.current_price = current_price
                return await self._market_sell_recovery(position)
                
        except Exception as e:
            logger.error(f"❌ Wait and recover failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def recover_all_stuck_positions(self) -> List[RecoveryResult]:
        """
        Recover all stuck positions
        """
        logger.info("🔍 Scanning for stuck positions...")
        
        stuck_positions = await self.scan_for_stuck_positions()
        
        if not stuck_positions:
            logger.info("✅ No stuck positions found")
            return []
        
        recovery_results = []
        
        for position in stuck_positions:
            if position.recovery_attempts < position.max_recovery_attempts:
                logger.info(f"🔄 Recovering position: {position.symbol} on {position.exchange}")
                
                result = await self.recover_stuck_position(position)
                recovery_results.append(result)
                
                # Brief delay between recoveries
                await asyncio.sleep(2)
            else:
                logger.warning(f"⚠️ Position {position.position_id} has exceeded max recovery attempts")
        
        return recovery_results

    def get_recovery_stats(self) -> Dict[str, Any]:
        """
        Get recovery statistics
        """
        total_recoveries = len(self.recovery_history)
        successful_recoveries = sum(1 for r in self.recovery_history if r.success)
        success_rate = (successful_recoveries / total_recoveries * 100) if total_recoveries > 0 else 0
        
        # Strategy breakdown
        strategy_stats = {}
        for result in self.recovery_history:
            strategy = result.strategy_used.value
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'total': 0, 'successful': 0}
            strategy_stats[strategy]['total'] += 1
            if result.success:
                strategy_stats[strategy]['successful'] += 1
        
        return {
            'total_recoveries': total_recoveries,
            'successful_recoveries': successful_recoveries,
            'success_rate': success_rate,
            'strategy_stats': strategy_stats,
            'active_positions': len([p for p in self.positions.values() if p.status == PositionStatus.ACTIVE]),
            'stuck_positions': len([p for p in self.positions.values() if p.status == PositionStatus.STUCK])
        }

    async def run_recovery_cycle(self):
        """
        Run periodic recovery cycle
        """
        while True:
            try:
                await self.recover_all_stuck_positions()
                
                # Log statistics
                stats = self.get_recovery_stats()
                logger.info(f"📊 Recovery stats: {stats['successful_recoveries']}/{stats['total_recoveries']} "
                           f"successful ({stats['success_rate']:.1f}% success rate)")
                
            except Exception as e:
                logger.error(f"❌ Error in recovery cycle: {str(e)}")
            
            # Wait for next cycle
            await asyncio.sleep(self.scan_interval_minutes * 60)

# Example usage
async def test_stuck_position_recovery():
    """
    Test the stuck position recovery system
    """
    # This would be called from the main bot
    pass

if __name__ == "__main__":
    asyncio.run(test_stuck_position_recovery())
