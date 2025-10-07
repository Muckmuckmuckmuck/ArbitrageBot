import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from exchanges import ExchangeManager
from price_monitor import ArbitrageDetector, PriceMonitor
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """Data class for arbitrage opportunity"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    timestamp: float
    estimated_profit: float = 0.0
    trade_amount: float = 0.0

@dataclass
class TradeExecution:
    """Data class for trade execution"""
    symbol: str
    buy_order_id: str
    sell_order_id: str
    buy_exchange: str
    sell_exchange: str
    amount: float
    buy_price: float
    sell_price: float
    timestamp: float
    status: str = "pending"

class ArbitrageEngine:
    """Main arbitrage trading engine"""
    
    def __init__(self, exchange_manager: ExchangeManager, price_monitor: PriceMonitor):
        self.exchange_manager = exchange_manager
        self.price_monitor = price_monitor
        self.arbitrage_detector = ArbitrageDetector(price_monitor, Config.MIN_SPREAD_PERCENT)
        self.active_trades: Dict[str, TradeExecution] = {}
        self.completed_trades: List[TradeExecution] = []
        self.daily_trade_count = 0
        self.last_trade_reset = time.time()
        self.running = False
        self.balance_manager = None  # Will be set by main bot
        self.percentage_balance_manager = None  # Will be set by main bot
        
    async def start(self, symbols: List[str]):
        """Start the arbitrage engine"""
        if self.running:
            logger.warning("Arbitrage engine is already running")
            return
        
        self.running = True
        logger.info(f"Starting arbitrage engine for symbols: {symbols}")
        
        # Start price monitoring
        await self.price_monitor.start_monitoring(symbols)
        
        # Start arbitrage monitoring
        await self.arbitrage_detector.monitor_arbitrage_opportunities(
            symbols, self.handle_arbitrage_opportunity
        )
        
        logger.info("Arbitrage engine started successfully")
    
    async def stop(self):
        """Stop the arbitrage engine"""
        if not self.running:
            logger.warning("Arbitrage engine is not running")
            return
        
        self.running = False
        logger.info("Stopping arbitrage engine")
        
        # Stop price monitoring
        await self.price_monitor.stop_monitoring()
        
        # Cancel any pending trades
        for trade_id, trade in self.active_trades.items():
            await self.cancel_trade(trade_id)
        
        logger.info("Arbitrage engine stopped")
    
    async def handle_arbitrage_opportunity(self, opportunity_data: Dict):
        """Handle detected arbitrage opportunity"""
        try:
            # Check daily trade limit
            if not self._check_daily_trade_limit():
                logger.warning("Daily trade limit reached")
                return
            
            # Check if opportunity is still valid
            if not self._is_opportunity_valid(opportunity_data):
                logger.info("Arbitrage opportunity no longer valid")
                return
            
            # Calculate optimal trade amount (adaptive to balance)
            trade_amount = await self._calculate_adaptive_trade_amount(opportunity_data)
            if trade_amount <= 0:
                logger.warning("Cannot calculate valid trade amount")
                return
            
            # Execute arbitrage trade
            await self.execute_arbitrage_trade(opportunity_data, trade_amount)
            
        except Exception as e:
            logger.error(f"Error handling arbitrage opportunity: {str(e)}")
    
    def _check_daily_trade_limit(self) -> bool:
        """Check if daily trade limit is reached"""
        # Reset daily counter if new day
        current_time = time.time()
        if current_time - self.last_trade_reset > 86400:  # 24 hours
            self.daily_trade_count = 0
            self.last_trade_reset = current_time
        
        return self.daily_trade_count < Config.MAX_DAILY_TRADES
    
    def _is_opportunity_valid(self, opportunity_data: Dict) -> bool:
        """Check if arbitrage opportunity is still valid"""
        symbol = opportunity_data['symbol']
        
        # Get strategy configuration for this asset
        strategy_config = Config.TRANSFER_SPEEDS.get(symbol, {})
        min_spread = strategy_config.get('min_spread', Config.MIN_SPREAD_PERCENT)
        
        # Check if opportunity is recent (within 5 seconds for fast assets, 10 seconds for slower ones)
        transfer_speed = strategy_config.get('speed', 300)
        max_age = 5 if transfer_speed <= 60 else 10
        
        if time.time() - opportunity_data['timestamp'] > max_age:
            return False
        
        # Re-check current prices
        spreads = self.price_monitor.get_price_spread(symbol)
        
        if not spreads:
            return False
        
        # Find current spread
        current_spread = None
        for spread_data in spreads.values():
            if (spread_data['lower_price_exchange'] == opportunity_data['buy_exchange'] and
                spread_data['higher_price_exchange'] == opportunity_data['sell_exchange']):
                current_spread = spread_data
                break
        
        if not current_spread:
            return False
        
        # Check if spread is still above asset-specific minimum
        return current_spread['spread_percent'] >= min_spread
    
    async def _calculate_adaptive_trade_amount(self, opportunity_data: Dict) -> float:
        """Calculate adaptive trade amount based on percentage of total account value"""
        try:
            symbol = opportunity_data['symbol']
            spread_percent = opportunity_data['spread_percent']
            
            # Use percentage-based balance manager if available
            if self.percentage_balance_manager:
                try:
                    # Get adaptive position size based on current conditions
                    position_size = await self.percentage_balance_manager.get_adaptive_position_size(
                        symbol=symbol,
                        spread_percent=spread_percent,
                        volatility=0.02  # Default volatility, could be calculated dynamically
                    )
                    
                    if position_size > 0:
                        logger.info(f"Percentage-based position size for {symbol}: ${position_size:,.2f}")
                        return position_size
                        
                except Exception as e:
                    logger.error(f"Error with percentage balance manager: {str(e)}")
            
            # Fallback to original balance manager
            if self.balance_manager:
                # Get position allocation from balance manager
                position_allocations = await self.balance_manager.calculate_position_allocations()
                allocation = position_allocations.get(symbol)
                
                if allocation:
                    # Use recommended position size from balance manager
                    recommended_amount = allocation.recommended_position_usd
                    
                    # Scale based on opportunity quality
                    if spread_percent > 0.02:  # > 2% spread
                        scale_factor = 1.0  # Full amount
                    elif spread_percent > 0.01:  # > 1% spread
                        scale_factor = 0.8  # 80% of recommended
                    else:
                        scale_factor = 0.6  # 60% of recommended
                    
                    return recommended_amount * scale_factor
            
            # Final fallback to original calculation
            return self._calculate_optimal_trade_amount(opportunity_data)
            
        except Exception as e:
            logger.error(f"Error calculating adaptive trade amount: {str(e)}")
            return self._calculate_optimal_trade_amount(opportunity_data)
    
    def _calculate_optimal_trade_amount(self, opportunity_data: Dict) -> float:
        """Calculate optimal trade amount based on available balance and risk management"""
        try:
            # Get balances from both exchanges
            buy_exchange = self.exchange_manager.get_exchange(opportunity_data['buy_exchange'])
            sell_exchange = self.exchange_manager.get_exchange(opportunity_data['sell_exchange'])
            
            # Get symbol info
            symbol = opportunity_data['symbol']
            base_currency = symbol.split('/')[0]
            
            # Get position limits for this asset
            max_position = Config.POSITION_LIMITS.get(symbol, Config.MAX_POSITION_SIZE)
            
            # Get available balance for buying (USDT balance on buy exchange)
            buy_balance = buy_exchange.balances.get('USDT', {}).get('free', 0)
            
            # Get available balance for selling (base currency balance on sell exchange)
            sell_balance = sell_exchange.balances.get(base_currency, {}).get('free', 0)
            
            # Calculate maximum trade amount based on balances
            max_buy_amount = buy_balance / opportunity_data['buy_price']
            max_sell_amount = sell_balance
            
            # Use the smaller of the two
            max_trade_amount = min(max_buy_amount, max_sell_amount)
            
            # Apply position size limits (asset-specific)
            max_trade_amount = min(max_trade_amount, max_position / opportunity_data['buy_price'])
            
            # Apply minimum trade amount (e.g., $10)
            min_trade_amount = 10 / opportunity_data['buy_price']
            
            if max_trade_amount < min_trade_amount:
                return 0
            
            return max_trade_amount
            
        except Exception as e:
            logger.error(f"Error calculating trade amount: {str(e)}")
            return 0
    
    async def execute_arbitrage_trade(self, opportunity_data: Dict, amount: float):
        """Execute arbitrage trade using optimal strategy for each asset"""
        try:
            symbol = opportunity_data['symbol']
            buy_exchange_name = opportunity_data['buy_exchange']
            sell_exchange_name = opportunity_data['sell_exchange']
            
            # Get strategy configuration for this asset
            strategy_config = Config.TRANSFER_SPEEDS.get(symbol, {})
            strategy = strategy_config.get('strategy', 'transfer_first')
            
            if strategy == 'transfer_first':
                return await self._execute_transfer_first_strategy(opportunity_data, amount)
            else:
                return await self._execute_simultaneous_strategy(opportunity_data, amount)
            
        except Exception as e:
            logger.error(f"Error executing arbitrage trade: {str(e)}")
    
    async def _execute_transfer_first_strategy(self, opportunity_data: Dict, amount: float):
        """Execute transfer-first arbitrage strategy"""
        try:
            symbol = opportunity_data['symbol']
            buy_exchange_name = opportunity_data['buy_exchange']
            sell_exchange_name = opportunity_data['sell_exchange']
            
            buy_exchange = self.exchange_manager.get_exchange(buy_exchange_name)
            sell_exchange = self.exchange_manager.get_exchange(sell_exchange_name)
            
            logger.info(f"Executing transfer-first arbitrage: {amount} {symbol}")
            logger.info(f"Buy on {buy_exchange_name} @ {opportunity_data['buy_price']}")
            logger.info(f"Transfer to {sell_exchange_name} and sell @ {opportunity_data['sell_price']}")
            
            # Step 1: Buy on cheaper exchange
            try:
                buy_order = await buy_exchange.place_market_order(symbol, 'buy', amount)
                logger.info(f"Buy order executed: {buy_order['id']}")
            except Exception as e:
                logger.error(f"Failed to execute buy order: {str(e)}")
                return
            
            # Step 2: Transfer to expensive exchange
            try:
                base_currency = symbol.split('/')[0]
                # Import transfer manager here to avoid circular import
                from transfer_manager import TransferManager
                transfer_manager = TransferManager(self.exchange_manager)
                await transfer_manager.initialize()
                
                transfer_success = await transfer_manager.transfer_currency(
                    base_currency, amount, buy_exchange_name, sell_exchange_name
                )
                if not transfer_success:
                    logger.error("Transfer failed")
                    return
                logger.info(f"Transfer initiated: {amount} {base_currency} to {sell_exchange_name}")
            except Exception as e:
                logger.error(f"Transfer failed: {str(e)}")
                return
            
            # Step 3: Wait for transfer completion (for fast networks, this is minimal)
            transfer_timeout = Config.TRANSFER_SPEEDS.get(symbol, {}).get('speed', 300)  # seconds
            await asyncio.sleep(min(transfer_timeout, 300))  # Max 5 minutes wait
            
            # Step 4: Sell on expensive exchange
            try:
                sell_order = await sell_exchange.place_market_order(symbol, 'sell', amount)
                logger.info(f"Sell order executed: {sell_order['id']}")
            except Exception as e:
                logger.error(f"Failed to execute sell order: {str(e)}")
                return
            
            # Create trade execution record
            trade_execution = TradeExecution(
                symbol=symbol,
                buy_order_id=buy_order['id'],
                sell_order_id=sell_order['id'],
                buy_exchange=buy_exchange_name,
                sell_exchange=sell_exchange_name,
                amount=amount,
                buy_price=opportunity_data['buy_price'],
                sell_price=opportunity_data['sell_price'],
                timestamp=time.time(),
                status="completed"
            )
            
            self.active_trades[f"{symbol}_{int(time.time())}"] = trade_execution
            self.completed_trades.append(trade_execution)
            self.daily_trade_count += 1
            
            # Calculate and log profit
            profit = (opportunity_data['sell_price'] - opportunity_data['buy_price']) * amount
            logger.info(f"Transfer-first arbitrage completed. Profit: ${profit:.2f}")
            
        except Exception as e:
            logger.error(f"Error in transfer-first strategy: {str(e)}")
    
    async def _execute_simultaneous_strategy(self, opportunity_data: Dict, amount: float):
        """Execute simultaneous buy/sell arbitrage strategy"""
        try:
            symbol = opportunity_data['symbol']
            buy_exchange_name = opportunity_data['buy_exchange']
            sell_exchange_name = opportunity_data['sell_exchange']
            
            buy_exchange = self.exchange_manager.get_exchange(buy_exchange_name)
            sell_exchange = self.exchange_manager.get_exchange(sell_exchange_name)
            
            logger.info(f"Executing simultaneous arbitrage: {amount} {symbol}")
            logger.info(f"Buy on {buy_exchange_name} @ {opportunity_data['buy_price']}")
            logger.info(f"Sell on {sell_exchange_name} @ {opportunity_data['sell_price']}")
            
            # Create trade execution record
            trade_execution = TradeExecution(
                symbol=symbol,
                buy_order_id="",
                sell_order_id="",
                buy_exchange=buy_exchange_name,
                sell_exchange=sell_exchange_name,
                amount=amount,
                buy_price=opportunity_data['buy_price'],
                sell_price=opportunity_data['sell_price'],
                timestamp=time.time()
            )
            
            # Execute buy order
            try:
                buy_order = await buy_exchange.place_market_order(symbol, 'buy', amount)
                trade_execution.buy_order_id = buy_order['id']
                trade_execution.status = "buy_executed"
                logger.info(f"Buy order executed: {buy_order['id']}")
            except Exception as e:
                logger.error(f"Failed to execute buy order: {str(e)}")
                return
            
            # Execute sell order
            try:
                sell_order = await sell_exchange.place_market_order(symbol, 'sell', amount)
                trade_execution.sell_order_id = sell_order['id']
                trade_execution.status = "sell_executed"
                logger.info(f"Sell order executed: {sell_order['id']}")
            except Exception as e:
                logger.error(f"Failed to execute sell order: {str(e)}")
                # Try to cancel buy order if sell fails
                try:
                    await buy_exchange.cancel_order(trade_execution.buy_order_id, symbol)
                    logger.info("Buy order cancelled due to sell order failure")
                except:
                    pass
                return
            
            # Mark trade as completed
            trade_execution.status = "completed"
            self.active_trades[f"{symbol}_{int(time.time())}"] = trade_execution
            self.completed_trades.append(trade_execution)
            self.daily_trade_count += 1
            
            # Calculate and log profit
            profit = (opportunity_data['sell_price'] - opportunity_data['buy_price']) * amount
            logger.info(f"Simultaneous arbitrage completed. Profit: ${profit:.2f}")
            
        except Exception as e:
            logger.error(f"Error in simultaneous strategy: {str(e)}")
    
    async def cancel_trade(self, trade_id: str):
        """Cancel a pending trade"""
        try:
            if trade_id not in self.active_trades:
                logger.warning(f"Trade {trade_id} not found")
                return
            
            trade = self.active_trades[trade_id]
            buy_exchange = self.exchange_manager.get_exchange(trade.buy_exchange)
            sell_exchange = self.exchange_manager.get_exchange(trade.sell_exchange)
            
            # Cancel buy order if not executed
            if trade.buy_order_id and trade.status in ["pending", "buy_executed"]:
                try:
                    await buy_exchange.cancel_order(trade.buy_order_id, trade.symbol)
                    logger.info(f"Buy order {trade.buy_order_id} cancelled")
                except:
                    pass
            
            # Cancel sell order if not executed
            if trade.sell_order_id and trade.status in ["pending", "sell_executed"]:
                try:
                    await sell_exchange.cancel_order(trade.sell_order_id, trade.symbol)
                    logger.info(f"Sell order {trade.sell_order_id} cancelled")
                except:
                    pass
            
            trade.status = "cancelled"
            logger.info(f"Trade {trade_id} cancelled")
            
        except Exception as e:
            logger.error(f"Error cancelling trade {trade_id}: {str(e)}")
    
    def get_trade_statistics(self) -> Dict:
        """Get trading statistics"""
        total_trades = len(self.completed_trades)
        successful_trades = len([t for t in self.completed_trades if t.status == "completed"])
        
        total_profit = 0
        for trade in self.completed_trades:
            if trade.status == "completed":
                profit = (trade.sell_price - trade.buy_price) * trade.amount
                total_profit += profit
        
        return {
            'total_trades': total_trades,
            'successful_trades': successful_trades,
            'success_rate': (successful_trades / total_trades * 100) if total_trades > 0 else 0,
            'total_profit': total_profit,
            'daily_trades': self.daily_trade_count,
            'active_trades': len(self.active_trades)
        }
