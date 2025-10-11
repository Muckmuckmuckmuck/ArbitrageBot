#!/usr/bin/env python3
"""
Aggressive Arbitrage Trading Bot for Pionex.US and Coinbase Pro
Production-ready with comprehensive error handling and safety mechanisms
"""

import asyncio
import ccxt
import logging
import signal
import sys
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

# Import configuration and components
from aggressive_config import AggressiveConfig, setup_logging
from auto_sizing_manager import AutoSizingManager
from dynamic_spread_manager import DynamicSpreadManager
from dynamic_slippage_detector import DynamicSlippageDetector
from smart_rate_limiter import SmartRateLimiter
from balance_validator import BalanceValidator
from fixed_percentage_balance_manager import FixedPercentageBalanceManager
from comprehensive_error_handler import ComprehensiveErrorHandler
from thread_safe_exchange_manager import ThreadSafeExchangeManager

logger = logging.getLogger(__name__)

@dataclass
class TradeOpportunity:
    """Represents an arbitrage opportunity"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread: float
    spread_percent: float
    position_size_usd: float
    estimated_profit: float
    timestamp: datetime

@dataclass
class TradeResult:
    """Represents the result of an executed trade"""
    success: bool
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    amount: float
    profit_usd: float
    fees_usd: float
    net_profit_usd: float
    spread_percent: float
    slippage_percent: float
    execution_time_ms: float
    error_message: Optional[str] = None

class AggressiveArbitrageBot:
    """Main aggressive arbitrage trading bot"""
    
    def __init__(self):
        """Initialize the bot"""
        self.config = AggressiveConfig()
        self.logger = setup_logging()
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Statistics
        self.stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_profit_usd': 0.0,
            'total_fees_usd': 0.0,
            'net_profit_usd': 0.0,
            'start_time': None,
            'trades_by_symbol': {},
            'opportunities_found': 0,
            'opportunities_rejected': 0,
        }
        
        # Initialize components (will be done in initialize())
        self.exchanges = {}
        self.auto_sizer = None
        self.spread_manager = None
        self.slippage_detector = None
        self.rate_limiter = None
        self.balance_validator = None
        self.balance_manager = None
        self.error_handler = None
        self.exchange_manager = None
        
        self.logger.info("AggressiveArbitrageBot instance created")
    
    async def initialize(self):
        """Initialize all components"""
        try:
            self.logger.info("=" * 80)
            self.logger.info("INITIALIZING AGGRESSIVE ARBITRAGE BOT")
            self.logger.info("=" * 80)
            
            # Validate API keys
            if not self.config.PIONEX_API_KEY or not self.config.COINBASE_API_KEY:
                raise ValueError("API keys not configured. Please set up .env file.")
            
            self.logger.info("✓ API keys validated")
            
            # Initialize exchanges
            self.logger.info("Initializing exchanges...")
            await self._initialize_exchanges()
            self.logger.info("✓ Exchanges initialized")
            
            # Initialize components
            self.logger.info("Initializing components...")
            self.auto_sizer = AutoSizingManager(self.config)
            self.spread_manager = DynamicSpreadManager(self.config)
            self.slippage_detector = DynamicSlippageDetector(self.config)
            self.rate_limiter = SmartRateLimiter(self.config)
            self.balance_validator = BalanceValidator(self.exchanges, self.config)
            self.error_handler = ComprehensiveErrorHandler(self.config)
            
            # Initialize balance manager
            self.balance_manager = FixedPercentageBalanceManager(
                self.exchanges,
                self.config
            )
            
            # Initialize thread-safe exchange manager
            self.exchange_manager = ThreadSafeExchangeManager(self.exchanges)
            
            self.logger.info("✓ All components initialized")
            
            # Initial balance check
            self.logger.info("Checking initial balances...")
            await self._check_initial_balances()
            self.logger.info("✓ Initial balances verified")
            
            # Setup signal handlers
            self._setup_signal_handlers()
            self.logger.info("✓ Signal handlers configured")
            
            # Record start time
            self.stats['start_time'] = datetime.now()
            
            self.logger.info("=" * 80)
            self.logger.info("BOT INITIALIZATION COMPLETE - READY TO TRADE")
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}", exc_info=True)
            raise
    
    async def _initialize_exchanges(self):
        """Initialize exchange connections"""
        try:
            # Initialize Pionex
            self.logger.info("Connecting to Pionex.US...")
            self.exchanges['pionex'] = ccxt.pionex({
                'apiKey': self.config.PIONEX_API_KEY,
                'secret': self.config.PIONEX_SECRET_KEY,
                'enableRateLimit': True,
                'rateLimit': 100,
                'options': {
                    'adjustForTimeDifference': True,
                    'recvWindow': 10000,
                }
            })
            
            if self.config.PIONEX_TESTNET:
                self.exchanges['pionex'].set_sandbox_mode(True)
                self.logger.info("  → Pionex testnet mode enabled")
            
            # Test Pionex connection
            await self.exchanges['pionex'].load_markets()
            self.logger.info(f"  ✓ Pionex connected ({len(self.exchanges['pionex'].markets)} markets)")
            
            # Initialize Coinbase Pro
            self.logger.info("Connecting to Coinbase Pro...")
            self.exchanges['coinbasepro'] = ccxt.coinbasepro({
                'apiKey': self.config.COINBASE_API_KEY,
                'secret': self.config.COINBASE_SECRET_KEY,
                'password': self.config.COINBASE_PASSPHRASE,
                'enableRateLimit': True,
                'rateLimit': 100,
                'options': {
                    'adjustForTimeDifference': True,
                }
            })
            
            if self.config.COINBASE_SANDBOX:
                self.exchanges['coinbasepro'].set_sandbox_mode(True)
                self.logger.info("  → Coinbase sandbox mode enabled")
            
            # Test Coinbase connection
            await self.exchanges['coinbasepro'].load_markets()
            self.logger.info(f"  ✓ Coinbase Pro connected ({len(self.exchanges['coinbasepro'].markets)} markets)")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize exchanges: {e}", exc_info=True)
            raise
    
    async def _check_initial_balances(self):
        """Check and log initial balances"""
        try:
            for exchange_name, exchange in self.exchanges.items():
                balance = await exchange.fetch_balance()
                
                # Get USDT balance
                usdt_balance = balance.get('USDT', {}).get('free', 0)
                
                self.logger.info(f"{exchange_name.upper()} Balance:")
                self.logger.info(f"  USDT: {usdt_balance:.2f}")
                
                # Log top 5 crypto balances
                crypto_balances = []
                for symbol in self.config.CURRENCY_PAIRS:
                    base = symbol.split('/')[0]
                    crypto_balance = balance.get(base, {}).get('free', 0)
                    if crypto_balance > 0:
                        crypto_balances.append((base, crypto_balance))
                
                if crypto_balances:
                    crypto_balances.sort(key=lambda x: x[1], reverse=True)
                    for base, amount in crypto_balances[:5]:
                        self.logger.info(f"  {base}: {amount:.8f}")
                
                # Check minimum balance
                if usdt_balance < self.config.RISK_MANAGEMENT['min_account_balance_usd']:
                    self.logger.warning(f"⚠️  {exchange_name} balance below minimum "
                                      f"(${usdt_balance:.2f} < ${self.config.RISK_MANAGEMENT['min_account_balance_usd']})")
            
        except Exception as e:
            self.logger.error(f"Failed to check initial balances: {e}", exc_info=True)
            raise
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the arbitrage bot"""
        try:
            if self.running:
                self.logger.warning("Bot is already running")
                return
            
            self.running = True
            self.logger.info("=" * 80)
            self.logger.info("STARTING AGGRESSIVE ARBITRAGE BOT")
            self.logger.info("=" * 80)
            
            # Start main trading loop
            trading_task = asyncio.create_task(self._trading_loop())
            
            # Start monitoring tasks
            monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # Start spread adjustment task
            spread_task = asyncio.create_task(self._spread_adjustment_loop())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel tasks
            trading_task.cancel()
            monitoring_task.cancel()
            spread_task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(
                trading_task, monitoring_task, spread_task,
                return_exceptions=True
            )
            
            self.logger.info("Bot stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error in start(): {e}", exc_info=True)
            raise
    
    async def _trading_loop(self):
        """Main trading loop"""
        try:
            self.logger.info("Trading loop started")
            
            while self.running and not self.shutdown_event.is_set():
                try:
                    # Check rate limits before proceeding
                    if not await self.rate_limiter.can_make_request('pionex'):
                        await asyncio.sleep(0.1)
                        continue
                    
                    if not await self.rate_limiter.can_make_request('coinbasepro'):
                        await asyncio.sleep(0.1)
                        continue
                    
                    # Scan for opportunities
                    opportunities = await self._scan_opportunities()
                    
                    if opportunities:
                        self.logger.info(f"Found {len(opportunities)} opportunities")
                        
                        # Execute best opportunities
                        for opp in opportunities[:self.config.RISK_MANAGEMENT['max_concurrent_trades']]:
                            if not self.running:
                                break
                            
                            # Execute trade
                            result = await self._execute_trade(opp)
                            
                            if result.success:
                                self.logger.info(f"✓ Trade successful: {result.symbol} - "
                                               f"Profit: ${result.net_profit_usd:.2f}")
                            else:
                                self.logger.warning(f"✗ Trade failed: {result.symbol} - "
                                                  f"{result.error_message}")
                    
                    # Wait before next iteration
                    await asyncio.sleep(self.config.CHECK_INTERVALS['price_check_seconds'])
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in trading loop: {e}", exc_info=True)
                    await asyncio.sleep(5)  # Wait before retry
            
            self.logger.info("Trading loop stopped")
            
        except asyncio.CancelledError:
            self.logger.info("Trading loop cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in trading loop: {e}", exc_info=True)
    
    async def _scan_opportunities(self) -> List[TradeOpportunity]:
        """Scan for arbitrage opportunities"""
        opportunities = []
        
        try:
            for symbol in self.config.CURRENCY_PAIRS:
                try:
                    # Fetch prices from both exchanges
                    pionex_ticker = await self.exchanges['pionex'].fetch_ticker(symbol)
                    coinbase_ticker = await self.exchanges['coinbasepro'].fetch_ticker(symbol)
                    
                    # Record rate limit usage
                    await self.rate_limiter.record_request('pionex')
                    await self.rate_limiter.record_request('coinbasepro')
                    
                    pionex_price = pionex_ticker['last']
                    coinbase_price = coinbase_ticker['last']
                    
                    # Calculate spread
                    if pionex_price < coinbase_price:
                        buy_exchange = 'pionex'
                        sell_exchange = 'coinbasepro'
                        buy_price = pionex_price
                        sell_price = coinbase_price
                    else:
                        buy_exchange = 'coinbasepro'
                        sell_exchange = 'pionex'
                        buy_price = coinbase_price
                        sell_price = pionex_price
                    
                    spread = sell_price - buy_price
                    spread_percent = (spread / buy_price) * 100
                    
                    # Get minimum spread requirement
                    min_spread = self.spread_manager.get_current_spread(symbol)
                    
                    # Check if spread is profitable
                    if spread_percent >= (min_spread * 100):
                        # Get position size
                        position_size = await self.balance_manager.get_adaptive_position_size(
                            symbol, spread_percent / 100
                        )
                        
                        if position_size > 0:
                            # Estimate profit
                            estimated_profit = self._estimate_profit(
                                symbol, buy_price, sell_price, position_size,
                                buy_exchange, sell_exchange
                            )
                            
                            if estimated_profit > 0:
                                opp = TradeOpportunity(
                                    symbol=symbol,
                                    buy_exchange=buy_exchange,
                                    sell_exchange=sell_exchange,
                                    buy_price=buy_price,
                                    sell_price=sell_price,
                                    spread=spread,
                                    spread_percent=spread_percent,
                                    position_size_usd=position_size,
                                    estimated_profit=estimated_profit,
                                    timestamp=datetime.now()
                                )
                                opportunities.append(opp)
                                self.stats['opportunities_found'] += 1
                            else:
                                self.stats['opportunities_rejected'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error scanning {symbol}: {e}")
                    continue
            
            # Sort by estimated profit (highest first)
            opportunities.sort(key=lambda x: x.estimated_profit, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error in _scan_opportunities(): {e}", exc_info=True)
        
        return opportunities
    
    def _estimate_profit(self, symbol: str, buy_price: float, sell_price: float,
                        position_size_usd: float, buy_exchange: str, sell_exchange: str) -> float:
        """Estimate profit for a trade"""
        try:
            # Calculate amount
            amount = position_size_usd / buy_price
            
            # Calculate fees
            buy_fee_rate = self.config.EXCHANGE_FEES[buy_exchange]['trading_fee']
            sell_fee_rate = self.config.EXCHANGE_FEES[sell_exchange]['trading_fee']
            
            buy_fee = position_size_usd * buy_fee_rate
            sell_value = amount * sell_price
            sell_fee = sell_value * sell_fee_rate
            
            total_fees = buy_fee + sell_fee
            
            # Calculate profit
            gross_profit = sell_value - position_size_usd
            net_profit = gross_profit - total_fees
            
            # Subtract estimated slippage
            slippage_estimate = self.config.SLIPPAGE_ESTIMATES.get(symbol, 0.001)
            slippage_cost = position_size_usd * slippage_estimate
            
            net_profit -= slippage_cost
            
            return net_profit
            
        except Exception as e:
            self.logger.error(f"Error estimating profit: {e}")
            return 0.0
    
    async def _execute_trade(self, opp: TradeOpportunity) -> TradeResult:
        """Execute an arbitrage trade"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing trade: {opp.symbol}")
            self.logger.info(f"  Buy on {opp.buy_exchange} @ ${opp.buy_price:.6f}")
            self.logger.info(f"  Sell on {opp.sell_exchange} @ ${opp.sell_price:.6f}")
            self.logger.info(f"  Spread: {opp.spread_percent:.3f}%")
            self.logger.info(f"  Position size: ${opp.position_size_usd:.2f}")
            self.logger.info(f"  Estimated profit: ${opp.estimated_profit:.2f}")
            
            # Calculate amount
            amount = opp.position_size_usd / opp.buy_price
            
            # Validate balances
            if not await self.balance_validator.validate_trade_balance(
                opp.buy_exchange, opp.sell_exchange, opp.symbol, amount, opp.buy_price
            ):
                return TradeResult(
                    success=False,
                    symbol=opp.symbol,
                    buy_exchange=opp.buy_exchange,
                    sell_exchange=opp.sell_exchange,
                    buy_price=opp.buy_price,
                    sell_price=opp.sell_price,
                    amount=amount,
                    profit_usd=0,
                    fees_usd=0,
                    net_profit_usd=0,
                    spread_percent=opp.spread_percent,
                    slippage_percent=0,
                    execution_time_ms=0,
                    error_message="Insufficient balance"
                )
            
            # Check slippage
            predicted_slippage = await self.slippage_detector.predict_slippage(
                opp.symbol, amount, opp.buy_exchange
            )
            
            if predicted_slippage > self.config.DYNAMIC_SLIPPAGE['max_acceptable_slippage']:
                self.logger.warning(f"Predicted slippage too high: {predicted_slippage*100:.2f}%")
                return TradeResult(
                    success=False,
                    symbol=opp.symbol,
                    buy_exchange=opp.buy_exchange,
                    sell_exchange=opp.sell_exchange,
                    buy_price=opp.buy_price,
                    sell_price=opp.sell_price,
                    amount=amount,
                    profit_usd=0,
                    fees_usd=0,
                    net_profit_usd=0,
                    spread_percent=opp.spread_percent,
                    slippage_percent=predicted_slippage * 100,
                    execution_time_ms=0,
                    error_message=f"Slippage too high: {predicted_slippage*100:.2f}%"
                )
            
            # Execute buy order
            self.logger.info(f"Placing buy order on {opp.buy_exchange}...")
            buy_order = await self.exchanges[opp.buy_exchange].create_market_buy_order(
                opp.symbol, amount
            )
            await self.rate_limiter.record_request(opp.buy_exchange)
            
            # Execute sell order
            self.logger.info(f"Placing sell order on {opp.sell_exchange}...")
            sell_order = await self.exchanges[opp.sell_exchange].create_market_sell_order(
                opp.symbol, amount
            )
            await self.rate_limiter.record_request(opp.sell_exchange)
            
            # Calculate actual results
            actual_buy_price = float(buy_order['average'])
            actual_sell_price = float(sell_order['average'])
            actual_amount = float(buy_order['filled'])
            
            buy_cost = actual_buy_price * actual_amount
            sell_revenue = actual_sell_price * actual_amount
            
            # Calculate fees
            buy_fee = float(buy_order.get('fee', {}).get('cost', 0))
            sell_fee = float(sell_order.get('fee', {}).get('cost', 0))
            total_fees = buy_fee + sell_fee
            
            # Calculate profit
            gross_profit = sell_revenue - buy_cost
            net_profit = gross_profit - total_fees
            
            # Calculate actual slippage
            expected_buy_price = opp.buy_price
            expected_sell_price = opp.sell_price
            buy_slippage = abs(actual_buy_price - expected_buy_price) / expected_buy_price
            sell_slippage = abs(actual_sell_price - expected_sell_price) / expected_sell_price
            avg_slippage = (buy_slippage + sell_slippage) / 2
            
            execution_time = (time.time() - start_time) * 1000  # ms
            
            # Update statistics
            self.stats['total_trades'] += 1
            if net_profit > 0:
                self.stats['successful_trades'] += 1
            else:
                self.stats['failed_trades'] += 1
            
            self.stats['total_profit_usd'] += gross_profit
            self.stats['total_fees_usd'] += total_fees
            self.stats['net_profit_usd'] += net_profit
            
            if opp.symbol not in self.stats['trades_by_symbol']:
                self.stats['trades_by_symbol'][opp.symbol] = {
                    'count': 0,
                    'profit': 0,
                    'wins': 0,
                    'losses': 0
                }
            
            self.stats['trades_by_symbol'][opp.symbol]['count'] += 1
            self.stats['trades_by_symbol'][opp.symbol]['profit'] += net_profit
            if net_profit > 0:
                self.stats['trades_by_symbol'][opp.symbol]['wins'] += 1
            else:
                self.stats['trades_by_symbol'][opp.symbol]['losses'] += 1
            
            # Update auto-sizer
            self.auto_sizer.record_trade(opp.symbol, net_profit > 0, net_profit, opp.position_size_usd)
            
            # Update spread manager
            self.spread_manager.record_opportunity(opp.symbol, opp.spread_percent / 100, net_profit > 0)
            
            # Update slippage detector
            self.slippage_detector.record_trade(opp.symbol, avg_slippage, amount)
            
            return TradeResult(
                success=True,
                symbol=opp.symbol,
                buy_exchange=opp.buy_exchange,
                sell_exchange=opp.sell_exchange,
                buy_price=actual_buy_price,
                sell_price=actual_sell_price,
                amount=actual_amount,
                profit_usd=gross_profit,
                fees_usd=total_fees,
                net_profit_usd=net_profit,
                spread_percent=opp.spread_percent,
                slippage_percent=avg_slippage * 100,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}", exc_info=True)
            self.stats['failed_trades'] += 1
            
            return TradeResult(
                success=False,
                symbol=opp.symbol,
                buy_exchange=opp.buy_exchange,
                sell_exchange=opp.sell_exchange,
                buy_price=opp.buy_price,
                sell_price=opp.sell_price,
                amount=amount,
                profit_usd=0,
                fees_usd=0,
                net_profit_usd=0,
                spread_percent=opp.spread_percent,
                slippage_percent=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def _monitoring_loop(self):
        """Monitoring loop for logging statistics"""
        try:
            self.logger.info("Monitoring loop started")
            
            while self.running and not self.shutdown_event.is_set():
                try:
                    await asyncio.sleep(300)  # Log every 5 minutes
                    
                    self._log_statistics()
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            
            self.logger.info("Monitoring loop stopped")
            
        except asyncio.CancelledError:
            self.logger.info("Monitoring loop cancelled")
    
    async def _spread_adjustment_loop(self):
        """Loop for adjusting spread requirements"""
        try:
            self.logger.info("Spread adjustment loop started")
            
            while self.running and not self.shutdown_event.is_set():
                try:
                    await asyncio.sleep(3600)  # Adjust every hour
                    
                    self.logger.info("Adjusting spread requirements...")
                    for symbol in self.config.CURRENCY_PAIRS:
                        self.spread_manager.adjust_spread(symbol)
                    
                    self.logger.info("Spread adjustments complete")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in spread adjustment loop: {e}", exc_info=True)
            
            self.logger.info("Spread adjustment loop stopped")
            
        except asyncio.CancelledError:
            self.logger.info("Spread adjustment loop cancelled")
    
    def _log_statistics(self):
        """Log current statistics"""
        try:
            runtime = datetime.now() - self.stats['start_time']
            hours = runtime.total_seconds() / 3600
            
            self.logger.info("=" * 80)
            self.logger.info("STATISTICS UPDATE")
            self.logger.info("=" * 80)
            self.logger.info(f"Runtime: {runtime}")
            self.logger.info(f"Total trades: {self.stats['total_trades']}")
            self.logger.info(f"Successful: {self.stats['successful_trades']}")
            self.logger.info(f"Failed: {self.stats['failed_trades']}")
            
            if self.stats['total_trades'] > 0:
                win_rate = (self.stats['successful_trades'] / self.stats['total_trades']) * 100
                self.logger.info(f"Win rate: {win_rate:.1f}%")
            
            self.logger.info(f"Gross profit: ${self.stats['total_profit_usd']:.2f}")
            self.logger.info(f"Total fees: ${self.stats['total_fees_usd']:.2f}")
            self.logger.info(f"Net profit: ${self.stats['net_profit_usd']:.2f}")
            
            if hours > 0:
                hourly_profit = self.stats['net_profit_usd'] / hours
                self.logger.info(f"Hourly profit: ${hourly_profit:.2f}")
                daily_profit = hourly_profit * 24
                self.logger.info(f"Projected daily: ${daily_profit:.2f}")
            
            self.logger.info(f"Opportunities found: {self.stats['opportunities_found']}")
            self.logger.info(f"Opportunities rejected: {self.stats['opportunities_rejected']}")
            
            # Per-symbol statistics
            if self.stats['trades_by_symbol']:
                self.logger.info("\nPer-symbol statistics:")
                for symbol, data in sorted(self.stats['trades_by_symbol'].items(), 
                                          key=lambda x: x[1]['profit'], reverse=True):
                    win_rate = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
                    self.logger.info(f"  {symbol}: {data['count']} trades, "
                                   f"${data['profit']:.2f} profit, "
                                   f"{win_rate:.1f}% win rate")
            
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"Error logging statistics: {e}", exc_info=True)
    
    async def shutdown(self):
        """Graceful shutdown"""
        try:
            self.logger.info("=" * 80)
            self.logger.info("SHUTTING DOWN BOT")
            self.logger.info("=" * 80)
            
            self.running = False
            
            # Log final statistics
            self._log_statistics()
            
            # Close exchange connections
            for exchange_name, exchange in self.exchanges.items():
                try:
                    await exchange.close()
                    self.logger.info(f"✓ Closed {exchange_name} connection")
                except Exception as e:
                    self.logger.error(f"Error closing {exchange_name}: {e}")
            
            self.shutdown_event.set()
            
            self.logger.info("=" * 80)
            self.logger.info("SHUTDOWN COMPLETE")
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)
            self.shutdown_event.set()

async def main():
    """Main entry point"""
    try:
        # Create and initialize bot
        bot = AggressiveArbitrageBot()
        await bot.initialize()
        
        # Start bot
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

