#!/usr/bin/env python3
"""
High-Frequency Arbitrage Engine
Optimized for continuous trading with maximum profit
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
from high_frequency_config import HighFrequencyConfig
from rate_limit_manager import RateLimitManager
from exchanges import ExchangeManager
from price_monitor import PriceMonitor

logger = logging.getLogger(__name__)

@dataclass
class HighFrequencyOpportunity:
    """High-frequency arbitrage opportunity"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    min_spread_required: float
    profit_after_fees: float
    profit_percent: float
    transfer_time: int
    strategy: str
    priority: int
    timestamp: float
    confidence: float
    risk_score: float

@dataclass
class HighFrequencyTrade:
    """High-frequency trade execution"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    amount: float
    profit_expected: float
    profit_actual: float
    fees_paid: float
    slippage: float
    execution_time: float
    transfer_time: float
    total_time: float
    status: str
    timestamp: float
    trade_id: str

class HighFrequencyArbitrageEngine:
    """High-frequency arbitrage engine optimized for continuous trading"""
    
    def __init__(self, exchange_manager: ExchangeManager, price_monitor: PriceMonitor):
        self.exchange_manager = exchange_manager
        self.price_monitor = price_monitor
        self.config = HighFrequencyConfig()
        self.rate_limit_manager = RateLimitManager()
        
        # Trading state
        self.running = False
        self.active_trades: Dict[str, HighFrequencyTrade] = {}
        self.completed_trades: List[HighFrequencyTrade] = []
        self.opportunities_queue: List[HighFrequencyOpportunity] = []
        
        # Performance tracking
        self.performance_metrics = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_profit': 0.0,
            'total_fees': 0.0,
            'total_slippage': 0.0,
            'avg_execution_time': 0.0,
            'avg_transfer_time': 0.0,
            'success_rate': 0.0,
            'profit_per_trade': 0.0,
            'trades_per_hour': 0.0,
            'start_time': time.time(),
        }
        
        # Loggers
        self.trade_logger = logging.getLogger('trade_executions')
        self.perf_logger = logging.getLogger('performance_metrics')
        self.profit_logger = logging.getLogger('profit_analysis')
        self.error_logger = logging.getLogger('error_analysis')
        
        logger.info("High-frequency arbitrage engine initialized")
    
    async def start(self):
        """Start the high-frequency arbitrage engine"""
        if self.running:
            logger.warning("High-frequency arbitrage engine is already running")
            return
        
        self.running = True
        logger.info("Starting high-frequency arbitrage engine")
        
        # Start price monitoring
        await self.price_monitor.start_monitoring(self.config.CURRENCY_PAIRS)
        
        # Start opportunity scanning
        asyncio.create_task(self._scan_opportunities_continuously())
        
        # Start trade execution
        asyncio.create_task(self._execute_trades_continuously())
        
        # Start performance monitoring
        asyncio.create_task(self._monitor_performance())
        
        logger.info("High-frequency arbitrage engine started successfully")
    
    async def stop(self):
        """Stop the high-frequency arbitrage engine"""
        if not self.running:
            logger.warning("High-frequency arbitrage engine is not running")
            return
        
        self.running = False
        logger.info("Stopping high-frequency arbitrage engine")
        
        # Stop price monitoring
        await self.price_monitor.stop_monitoring()
        
        # Cancel active trades
        for trade_id, trade in self.active_trades.items():
            await self._cancel_trade(trade_id)
        
        # Log final performance metrics
        await self._log_final_performance()
        
        logger.info("High-frequency arbitrage engine stopped")
    
    async def _scan_opportunities_continuously(self):
        """Continuously scan for arbitrage opportunities"""
        while self.running:
            try:
                await self._scan_opportunities()
                await asyncio.sleep(self.config.PERFORMANCE_CONFIG['opportunity_scan_interval'])
            except Exception as e:
                logger.error(f"Error scanning opportunities: {str(e)}")
                await asyncio.sleep(1.0)
    
    async def _scan_opportunities(self):
        """Scan for arbitrage opportunities across all currency pairs"""
        try:
            for symbol in self.config.CURRENCY_PAIRS:
                try:
                    # Get price spreads
                    spreads = self.price_monitor.get_price_spread(symbol)
                    
                    if not spreads:
                        continue
                    
                    # Analyze each spread
                    for spread_data in spreads.values():
                        opportunity = await self._analyze_opportunity(symbol, spread_data)
                        
                        if opportunity and self._is_opportunity_valid(opportunity):
                            await self._add_opportunity_to_queue(opportunity)
                
                except Exception as e:
                    logger.error(f"Error scanning opportunities for {symbol}: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in opportunity scanning: {str(e)}")
    
    async def _analyze_opportunity(self, symbol: str, spread_data: Dict) -> Optional[HighFrequencyOpportunity]:
        """Analyze a price spread for arbitrage opportunity"""
        try:
            # Get spread configuration
            spread_config = self.config.OPTIMIZED_SPREAD_REQUIREMENTS.get(symbol)
            if not spread_config:
                return None
            
            # Calculate spread percentage
            buy_price = spread_data['lower_price']
            sell_price = spread_data['higher_price']
            spread_percent = (sell_price - buy_price) / buy_price
            
            # Check if spread meets minimum requirement
            if spread_percent < spread_config['min_spread']:
                return None
            
            # Calculate profit after fees and slippage
            buy_exchange = spread_data['lower_price_exchange']
            sell_exchange = spread_data['higher_price_exchange']
            
            # Get fees for both exchanges
            buy_fee = self.config.EXCHANGE_FEES[buy_exchange]['trading_fee']
            sell_fee = self.config.EXCHANGE_FEES[sell_exchange]['trading_fee']
            
            # Get slippage estimate
            slippage = self.config.SLIPPAGE_ESTIMATES.get(symbol, 0.0003)
            
            # Calculate total costs
            total_fees = buy_fee + sell_fee + slippage
            profit_after_fees = spread_percent - total_fees
            profit_percent = profit_after_fees * 100
            
            # Check if profitable after costs
            if profit_after_fees <= 0:
                return None
            
            # Calculate confidence and risk scores
            confidence = self._calculate_confidence(symbol, spread_percent, spread_config)
            risk_score = self._calculate_risk_score(symbol, spread_percent, spread_config)
            
            return HighFrequencyOpportunity(
                symbol=symbol,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                spread_percent=spread_percent,
                min_spread_required=spread_config['min_spread'],
                profit_after_fees=profit_after_fees,
                profit_percent=profit_percent,
                transfer_time=spread_config['transfer_time'],
                strategy=spread_config['strategy'],
                priority=spread_config['priority'],
                timestamp=time.time(),
                confidence=confidence,
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity for {symbol}: {str(e)}")
            return None
    
    def _calculate_confidence(self, symbol: str, spread_percent: float, spread_config: Dict) -> float:
        """Calculate confidence score for an opportunity"""
        try:
            # Base confidence on spread quality
            target_spread = spread_config['target_spread']
            max_spread = spread_config['max_spread']
            
            if spread_percent >= target_spread:
                confidence = 0.9  # High confidence
            elif spread_percent >= spread_config['min_spread'] * 1.5:
                confidence = 0.7  # Medium confidence
            else:
                confidence = 0.5  # Low confidence
            
            # Adjust for priority
            priority = spread_config['priority']
            if priority == 1:  # Tier 1 assets
                confidence += 0.1
            elif priority == 2:  # Tier 2 assets
                confidence += 0.05
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5
    
    def _calculate_risk_score(self, symbol: str, spread_percent: float, spread_config: Dict) -> float:
        """Calculate risk score for an opportunity"""
        try:
            # Base risk on spread volatility
            spread_volatility = abs(spread_percent - spread_config['target_spread'])
            
            # Higher volatility = higher risk
            if spread_volatility > 0.01:  # > 1% deviation
                risk_score = 0.8
            elif spread_volatility > 0.005:  # > 0.5% deviation
                risk_score = 0.6
            else:
                risk_score = 0.3
            
            # Adjust for priority
            priority = spread_config['priority']
            if priority >= 3:  # Lower priority = higher risk
                risk_score += 0.2
            
            return min(1.0, max(0.0, risk_score))
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 0.5
    
    def _is_opportunity_valid(self, opportunity: HighFrequencyOpportunity) -> bool:
        """Check if an opportunity is still valid"""
        try:
            # Check if opportunity is recent
            max_age = 5 if opportunity.transfer_time <= 60 else 10
            if time.time() - opportunity.timestamp > max_age:
                return False
            
            # Check confidence threshold
            if opportunity.confidence < 0.5:
                return False
            
            # Check risk threshold
            if opportunity.risk_score > 0.8:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating opportunity: {str(e)}")
            return False
    
    async def _add_opportunity_to_queue(self, opportunity: HighFrequencyOpportunity):
        """Add opportunity to execution queue"""
        try:
            # Check if we already have an active trade for this symbol
            for trade in self.active_trades.values():
                if trade.symbol == opportunity.symbol:
                    return  # Skip if already trading this symbol
            
            # Add to queue
            self.opportunities_queue.append(opportunity)
            
            # Sort by priority and confidence
            self.opportunities_queue.sort(
                key=lambda x: (x.priority, x.confidence, x.profit_percent),
                reverse=True
            )
            
            # Keep only top opportunities
            max_queue_size = self.config.MAX_CONCURRENT_TRADES * 2
            if len(self.opportunities_queue) > max_queue_size:
                self.opportunities_queue = self.opportunities_queue[:max_queue_size]
            
            logger.debug(f"Added opportunity to queue: {opportunity.symbol} - {opportunity.profit_percent:.2f}%")
            
        except Exception as e:
            logger.error(f"Error adding opportunity to queue: {str(e)}")
    
    async def _execute_trades_continuously(self):
        """Continuously execute trades from the queue"""
        while self.running:
            try:
                # Check if we can execute more trades
                if len(self.active_trades) >= self.config.MAX_CONCURRENT_TRADES:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get next opportunity
                if not self.opportunities_queue:
                    await asyncio.sleep(0.1)
                    continue
                
                opportunity = self.opportunities_queue.pop(0)
                
                # Execute trade
                await self._execute_trade(opportunity)
                
            except Exception as e:
                logger.error(f"Error in trade execution: {str(e)}")
                await asyncio.sleep(1.0)
    
    async def _execute_trade(self, opportunity: HighFrequencyOpportunity):
        """Execute a high-frequency arbitrage trade"""
        try:
            # Check rate limits
            buy_can_proceed, buy_wait = await self.rate_limit_manager.check_rate_limit(
                opportunity.buy_exchange, 'order'
            )
            sell_can_proceed, sell_wait = await self.rate_limit_manager.check_rate_limit(
                opportunity.sell_exchange, 'order'
            )
            
            if not buy_can_proceed or not sell_can_proceed:
                max_wait = max(buy_wait, sell_wait)
                logger.warning(f"Rate limited, waiting {max_wait:.2f} seconds")
                await asyncio.sleep(max_wait)
                return
            
            # Calculate position size
            position_size = await self._calculate_position_size(opportunity)
            if position_size <= 0:
                logger.warning(f"Invalid position size for {opportunity.symbol}")
                return
            
            # Create trade
            trade = HighFrequencyTrade(
                symbol=opportunity.symbol,
                buy_exchange=opportunity.buy_exchange,
                sell_exchange=opportunity.sell_exchange,
                buy_price=opportunity.buy_price,
                sell_price=opportunity.sell_price,
                amount=position_size,
                profit_expected=opportunity.profit_after_fees * position_size,
                profit_actual=0.0,
                fees_paid=0.0,
                slippage=0.0,
                execution_time=0.0,
                transfer_time=0.0,
                total_time=0.0,
                status='pending',
                timestamp=time.time(),
                trade_id=f"{opportunity.symbol}_{int(time.time() * 1000)}"
            )
            
            # Add to active trades
            self.active_trades[trade.trade_id] = trade
            
            # Execute trade
            await self._execute_trade_orders(trade)
            
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            self.error_logger.error(f"Trade execution error: {str(e)}")
    
    async def _calculate_position_size(self, opportunity: HighFrequencyOpportunity) -> float:
        """Calculate optimal position size for an opportunity"""
        try:
            # Get account balance
            total_balance = await self._get_total_balance()
            if total_balance <= 0:
                return 0.0
            
            # Get position percentage for this symbol
            position_percent = self.config.POSITION_PERCENTAGES.get(opportunity.symbol, 0.05)
            
            # Calculate base position size
            base_position = total_balance * position_percent
            
            # Adjust based on opportunity quality
            if opportunity.confidence > 0.8:
                position_multiplier = 1.2
            elif opportunity.confidence > 0.6:
                position_multiplier = 1.0
            else:
                position_multiplier = 0.8
            
            # Adjust based on risk
            if opportunity.risk_score < 0.3:
                position_multiplier *= 1.1
            elif opportunity.risk_score > 0.7:
                position_multiplier *= 0.9
            
            # Calculate final position size
            final_position = base_position * position_multiplier
            
            # Apply limits
            max_position = total_balance * self.config.RISK_MANAGEMENT['max_position_percent']
            min_position = total_balance * self.config.RISK_MANAGEMENT['min_position_percent']
            
            final_position = min(final_position, max_position)
            final_position = max(final_position, min_position)
            
            return final_position
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0.0
    
    async def _get_total_balance(self) -> float:
        """Get total account balance across all exchanges"""
        try:
            total_balance = 0.0
            
            for exchange_name in ['binance', 'okx']:
                exchange = getattr(self.exchange_manager, exchange_name, None)
                if exchange:
                    balance = await exchange.get_balance()
                    for currency, amount in balance.items():
                        if currency in ['USDT', 'USDC', 'DAI', 'BUSD']:
                            total_balance += amount
                        else:
                            # Get current price for crypto
                            try:
                                price = await exchange.get_ticker(f"{currency}/USDT")
                                total_balance += amount * price
                            except:
                                continue
            
            return total_balance
            
        except Exception as e:
            logger.error(f"Error getting total balance: {str(e)}")
            return 0.0
    
    async def _execute_trade_orders(self, trade: HighFrequencyTrade):
        """Execute the actual trade orders"""
        try:
            start_time = time.time()
            
            # Get exchanges
            buy_exchange = getattr(self.exchange_manager, trade.buy_exchange, None)
            sell_exchange = getattr(self.exchange_manager, trade.sell_exchange, None)
            
            if not buy_exchange or not sell_exchange:
                raise ValueError("Exchange not found")
            
            # Execute buy order
            buy_order = await buy_exchange.create_order(
                symbol=trade.symbol,
                type='market',
                side='buy',
                amount=trade.amount,
                price=trade.buy_price
            )
            
            # Record rate limit usage
            await self.rate_limit_manager.record_request(trade.buy_exchange, 'order')
            
            # Execute sell order
            sell_order = await sell_exchange.create_order(
                symbol=trade.symbol,
                type='market',
                side='sell',
                amount=trade.amount,
                price=trade.sell_price
            )
            
            # Record rate limit usage
            await self.rate_limit_manager.record_request(trade.sell_exchange, 'order')
            
            # Calculate execution time
            execution_time = time.time() - start_time
            trade.execution_time = execution_time
            
            # Update trade status
            trade.status = 'completed'
            
            # Calculate actual profit
            await self._calculate_actual_profit(trade)
            
            # Move to completed trades
            self.completed_trades.append(trade)
            del self.active_trades[trade.trade_id]
            
            # Update performance metrics
            await self._update_performance_metrics(trade)
            
            # Log trade
            await self._log_trade_execution(trade)
            
        except Exception as e:
            logger.error(f"Error executing trade orders: {str(e)}")
            trade.status = 'failed'
            await self._log_trade_error(trade, str(e))
    
    async def _calculate_actual_profit(self, trade: HighFrequencyTrade):
        """Calculate actual profit after execution"""
        try:
            # This would need to be implemented based on actual order execution
            # For now, use expected profit as placeholder
            trade.profit_actual = trade.profit_expected
            
            # Calculate fees paid
            buy_fee = self.config.EXCHANGE_FEES[trade.buy_exchange]['trading_fee']
            sell_fee = self.config.EXCHANGE_FEES[trade.sell_exchange]['trading_fee']
            trade.fees_paid = trade.amount * (buy_fee + sell_fee)
            
            # Calculate slippage
            slippage = self.config.SLIPPAGE_ESTIMATES.get(trade.symbol, 0.0003)
            trade.slippage = trade.amount * slippage
            
        except Exception as e:
            logger.error(f"Error calculating actual profit: {str(e)}")
    
    async def _update_performance_metrics(self, trade: HighFrequencyTrade):
        """Update performance metrics"""
        try:
            self.performance_metrics['total_trades'] += 1
            
            if trade.status == 'completed':
                self.performance_metrics['successful_trades'] += 1
                self.performance_metrics['total_profit'] += trade.profit_actual
                self.performance_metrics['total_fees'] += trade.fees_paid
                self.performance_metrics['total_slippage'] += trade.slippage
            else:
                self.performance_metrics['failed_trades'] += 1
            
            # Calculate averages
            if self.performance_metrics['total_trades'] > 0:
                self.performance_metrics['success_rate'] = (
                    self.performance_metrics['successful_trades'] / 
                    self.performance_metrics['total_trades']
                )
                
                if self.performance_metrics['successful_trades'] > 0:
                    self.performance_metrics['profit_per_trade'] = (
                        self.performance_metrics['total_profit'] / 
                        self.performance_metrics['successful_trades']
                    )
            
            # Calculate trades per hour
            elapsed_time = time.time() - self.performance_metrics['start_time']
            if elapsed_time > 0:
                self.performance_metrics['trades_per_hour'] = (
                    self.performance_metrics['total_trades'] / (elapsed_time / 3600)
                )
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {str(e)}")
    
    async def _log_trade_execution(self, trade: HighFrequencyTrade):
        """Log trade execution details"""
        try:
            trade_data = {
                'trade_id': trade.trade_id,
                'symbol': trade.symbol,
                'buy_exchange': trade.buy_exchange,
                'sell_exchange': trade.sell_exchange,
                'amount': trade.amount,
                'buy_price': trade.buy_price,
                'sell_price': trade.sell_price,
                'profit_expected': trade.profit_expected,
                'profit_actual': trade.profit_actual,
                'fees_paid': trade.fees_paid,
                'slippage': trade.slippage,
                'execution_time': trade.execution_time,
                'status': trade.status,
                'timestamp': trade.timestamp
            }
            
            self.trade_logger.info(f"TRADE_EXECUTED: {trade_data}")
            
            # Log profit analysis
            if trade.status == 'completed':
                self.profit_logger.info(
                    f"PROFIT: {trade.symbol} - "
                    f"Expected: ${trade.profit_expected:.2f}, "
                    f"Actual: ${trade.profit_actual:.2f}, "
                    f"Fees: ${trade.fees_paid:.2f}, "
                    f"Slippage: ${trade.slippage:.2f}"
                )
            
        except Exception as e:
            logger.error(f"Error logging trade execution: {str(e)}")
    
    async def _log_trade_error(self, trade: HighFrequencyTrade, error: str):
        """Log trade error"""
        try:
            self.error_logger.error(
                f"TRADE_ERROR: {trade.symbol} - {error} - "
                f"Trade ID: {trade.trade_id}"
            )
        except Exception as e:
            logger.error(f"Error logging trade error: {str(e)}")
    
    async def _monitor_performance(self):
        """Monitor and log performance metrics"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Log every minute
                
                # Log performance metrics
                self.perf_logger.info(f"PERFORMANCE: {self.performance_metrics}")
                
                # Log rate limit status
                rate_limit_status = self.rate_limit_manager.get_rate_limit_summary()
                logger.info(f"Rate limit status: {rate_limit_status}")
                
            except Exception as e:
                logger.error(f"Error monitoring performance: {str(e)}")
    
    async def _log_final_performance(self):
        """Log final performance metrics"""
        try:
            final_metrics = {
                'total_trades': self.performance_metrics['total_trades'],
                'successful_trades': self.performance_metrics['successful_trades'],
                'failed_trades': self.performance_metrics['failed_trades'],
                'success_rate': self.performance_metrics['success_rate'],
                'total_profit': self.performance_metrics['total_profit'],
                'total_fees': self.performance_metrics['total_fees'],
                'total_slippage': self.performance_metrics['total_slippage'],
                'profit_per_trade': self.performance_metrics['profit_per_trade'],
                'trades_per_hour': self.performance_metrics['trades_per_hour'],
                'total_runtime': time.time() - self.performance_metrics['start_time']
            }
            
            self.perf_logger.info(f"FINAL_PERFORMANCE: {final_metrics}")
            
        except Exception as e:
            logger.error(f"Error logging final performance: {str(e)}")
    
    async def _cancel_trade(self, trade_id: str):
        """Cancel an active trade"""
        try:
            if trade_id in self.active_trades:
                trade = self.active_trades[trade_id]
                trade.status = 'cancelled'
                
                # Move to completed trades
                self.completed_trades.append(trade)
                del self.active_trades[trade_id]
                
                logger.info(f"Cancelled trade: {trade_id}")
                
        except Exception as e:
            logger.error(f"Error cancelling trade {trade_id}: {str(e)}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        return self.performance_metrics.copy()
    
    def get_active_trades(self) -> Dict[str, HighFrequencyTrade]:
        """Get active trades"""
        return self.active_trades.copy()
    
    def get_completed_trades(self) -> List[HighFrequencyTrade]:
        """Get completed trades"""
        return self.completed_trades.copy()

if __name__ == "__main__":
    # Test high-frequency arbitrage engine
    async def test_engine():
        from exchanges import ExchangeManager
        from price_monitor import PriceMonitor
        
        # Initialize components
        exchange_manager = ExchangeManager()
        price_monitor = PriceMonitor(exchange_manager)
        
        # Create engine
        engine = HighFrequencyArbitrageEngine(exchange_manager, price_monitor)
        
        # Start engine
        await engine.start()
        
        # Run for 10 seconds
        await asyncio.sleep(10)
        
        # Stop engine
        await engine.stop()
        
        # Print performance
        print(f"Performance: {engine.get_performance_summary()}")
    
    # Run test
    asyncio.run(test_engine())
