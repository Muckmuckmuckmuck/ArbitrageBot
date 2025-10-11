#!/usr/bin/env python3
"""
Aggressive Arbitrage Bot with FULL AUTOMATED TRANSFERS
TRUE Cross-Exchange Arbitrage: Buy → Transfer → Sell → Rebalance
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
from auto_sizing_manager import AutoSizingManager, TradeResult as AutoSizerTradeResult
from dynamic_spread_manager import DynamicSpreadManager, SpreadOpportunity
from dynamic_slippage_detector import DynamicSlippageDetector
from smart_rate_limiter import SmartRateLimiter
from balance_validator import BalanceValidator
from fixed_percentage_balance_manager import FixedPercentageBalanceManager
from comprehensive_error_handler import ComprehensiveErrorHandler
from thread_safe_exchange_manager import ThreadSafeExchangeManager
from transfer_manager_fixed import TransferManager, TransferResult
from auto_recovery_system import AutoRecoverySystem, StuckPosition

logger = logging.getLogger(__name__)

# Constants
MIN_PROFIT_USD = 1.00  # Minimum $1 profit per trade
ORDER_TIMEOUT_SECONDS = 10.0  # Order timeout
TRANSFER_TIMEOUT_SECONDS = 300.0  # 5 minute transfer timeout
BALANCE_REFRESH_INTERVAL = 30  # Refresh balance every 30 seconds
MAX_RATE_LIMIT_BACKOFF = 60.0  # Max backoff time

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
class CompleteArbitrageResult:
    """Result of complete arbitrage cycle (buy → transfer → sell)"""
    success: bool
    symbol: str
    buy_exchange: str
    sell_exchange: str
    
    # Buy phase
    buy_price: float
    buy_amount: float
    buy_cost: float
    buy_fee: float
    buy_success: bool
    
    # Transfer phase
    transfer_time_seconds: float
    transfer_success: bool
    transfer_tx_id: Optional[str]
    
    # Sell phase  
    sell_price: float
    sell_amount: float
    sell_revenue: float
    sell_fee: float
    sell_success: bool
    
    # Overall
    gross_profit: float
    net_profit: float
    total_fees: float
    total_time_seconds: float
    spread_percent: float
    slippage_percent: float
    
    error_message: Optional[str] = None

class AggressiveArbitrageBotWithTransfers:
    """Arbitrage bot with automated cross-exchange transfers"""
    
    def __init__(self):
        """Initialize the bot"""
        self.config = AggressiveConfig()
        self.logger = setup_logging()
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Statistics
        self.stats = {
            'total_arbitrages': 0,
            'successful_arbitrages': 0,
            'failed_arbitrages': 0,
            'total_profit_usd': 0.0,
            'total_fees_usd': 0.0,
            'net_profit_usd': 0.0,
            'total_transfer_time': 0.0,
            'avg_transfer_time': 0.0,
            'start_time': None,
            'arbitrages_by_symbol': {},
            'opportunities_found': 0,
            'opportunities_rejected': 0,
        }
        
        # Track initial balance
        self.initial_balance = 0.0
        
        # Initialize components
        self.exchanges = {}
        self.auto_sizer = None
        self.spread_manager = None
        self.slippage_detector = None
        self.rate_limiter = None
        self.balance_validator = None
        self.balance_manager = None
        self.error_handler = None
        self.exchange_manager = None
        self.transfer_manager = None
        self.recovery_system = None
        
        self.logger.info("AggressiveArbitrageBotWithTransfers instance created")
    
    async def initialize(self):
        """Initialize all components"""
        try:
            self.logger.info("=" * 80)
            self.logger.info("INITIALIZING ARBITRAGE BOT WITH AUTOMATED TRANSFERS")
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
            
            # Initialize transfer manager
            self.transfer_manager = TransferManager(self.exchanges, self.config)
            
            # Initialize auto-recovery system
            self.recovery_system = AutoRecoverySystem(self.exchanges, self.config)
            
            self.logger.info("✓ All components initialized")
            
            # Calculate initial balance
            self.logger.info("Calculating initial balance...")
            self.initial_balance = await self._calculate_total_balance()
            self.logger.info(f"✓ Initial balance: ${self.initial_balance:.2f}")
            
            # Check initial balances
            self.logger.info("Checking initial balances...")
            await self._check_initial_balances()
            self.logger.info("✓ Initial balances verified")
            
            # Setup signal handlers
            self._setup_signal_handlers()
            self.logger.info("✓ Signal handlers configured")
            
            # Record start time
            self.stats['start_time'] = datetime.now()
            
            self.logger.info("=" * 80)
            self.logger.info("BOT INITIALIZATION COMPLETE - READY FOR CROSS-EXCHANGE ARBITRAGE")
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
    
    async def _calculate_total_balance(self) -> float:
        """Calculate total balance across all exchanges in USD"""
        total = 0.0
        
        try:
            for exchange_name, exchange in self.exchanges.items():
                balance = await exchange.fetch_balance()
                
                # Add USDT/USD
                total += balance.get('USDT', {}).get('free', 0)
                total += balance.get('USD', {}).get('free', 0)
                
                # Add crypto holdings (convert to USD)
                for symbol in self.config.CURRENCY_PAIRS:
                    base = symbol.split('/')[0]
                    crypto_amount = balance.get(base, {}).get('free', 0)
                    
                    if crypto_amount > 0:
                        try:
                            ticker = await exchange.fetch_ticker(symbol)
                            price = ticker['last']
                            total += crypto_amount * price
                        except Exception as e:
                            self.logger.warning(f"Could not get price for {symbol}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error calculating total balance: {e}", exc_info=True)
        
        return total
    
    async def _check_initial_balances(self):
        """Check and log initial balances"""
        try:
            for exchange_name, exchange in self.exchanges.items():
                balance = await exchange.fetch_balance()
                
                # Get USDT balance
                usdt_balance = balance.get('USDT', {}).get('free', 0)
                usd_balance = balance.get('USD', {}).get('free', 0)
                total_stable = usdt_balance + usd_balance
                
                self.logger.info(f"{exchange_name.upper()} Balance:")
                self.logger.info(f"  USDT/USD: ${total_stable:.2f}")
                
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
                if total_stable < self.config.RISK_MANAGEMENT['min_account_balance_usd']:
                    self.logger.warning(f"⚠️  {exchange_name} balance below minimum "
                                      f"(${total_stable:.2f} < ${self.config.RISK_MANAGEMENT['min_account_balance_usd']})")
            
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
    
    def _should_emergency_stop(self) -> bool:
        """Check if emergency stop should be triggered"""
        if not self.stats['start_time'] or self.initial_balance == 0:
            return False
        
        if self.stats['net_profit_usd'] < 0:
            drawdown_percent = abs(self.stats['net_profit_usd']) / self.initial_balance
            
            if drawdown_percent >= self.config.RISK_MANAGEMENT['emergency_stop_drawdown']:
                self.logger.critical(f"🚨 EMERGENCY STOP: Drawdown {drawdown_percent*100:.1f}% >= "
                                   f"{self.config.RISK_MANAGEMENT['emergency_stop_drawdown']*100:.0f}%")
                return True
            
            if drawdown_percent >= self.config.RISK_MANAGEMENT['max_daily_drawdown']:
                self.logger.error(f"⚠️  Daily drawdown limit reached: {drawdown_percent*100:.1f}%")
                return True
        
        return False
    
    async def start(self):
        """Start the arbitrage bot"""
        try:
            if self.running:
                self.logger.warning("Bot is already running")
                return
            
            self.running = True
            self.logger.info("=" * 80)
            self.logger.info("STARTING ARBITRAGE BOT WITH AUTOMATED TRANSFERS")
            self.logger.info("Strategy: Buy → Transfer → Sell → Rebalance")
            self.logger.info("=" * 80)
            
            # Start main trading loop
            trading_task = asyncio.create_task(self._trading_loop())
            
            # Start monitoring tasks
            monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # Start balance refresh loop
            balance_refresh_task = asyncio.create_task(self._balance_refresh_loop())
            
            # Start recovery loop  
            recovery_task = asyncio.create_task(self._recovery_loop())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel tasks
            trading_task.cancel()
            monitoring_task.cancel()
            balance_refresh_task.cancel()
            recovery_task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(
                trading_task, monitoring_task, balance_refresh_task, recovery_task,
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
            
            pionex_backoff = 0.1
            coinbase_backoff = 0.1
            
            while self.running and not self.shutdown_event.is_set():
                try:
                    # Check emergency stop
                    if self._should_emergency_stop():
                        self.logger.critical("Emergency stop triggered - shutting down")
                        await self.shutdown()
                        return
                    
                    # Rate limit check with exponential backoff
                    while not await self.rate_limiter.can_make_request('pionex'):
                        await asyncio.sleep(pionex_backoff)
                        pionex_backoff = min(pionex_backoff * 2, MAX_RATE_LIMIT_BACKOFF)
                        if pionex_backoff > 10:
                            self.logger.warning(f"Pionex rate limit backoff: {pionex_backoff:.1f}s")
                    pionex_backoff = 0.1
                    
                    while not await self.rate_limiter.can_make_request('coinbasepro'):
                        await asyncio.sleep(coinbase_backoff)
                        coinbase_backoff = min(coinbase_backoff * 2, MAX_RATE_LIMIT_BACKOFF)
                        if coinbase_backoff > 10:
                            self.logger.warning(f"Coinbase rate limit backoff: {coinbase_backoff:.1f}s")
                    coinbase_backoff = 0.1
                    
                    # Scan for opportunities
                    opportunities = await self._scan_opportunities()
                    
                    if opportunities:
                        self.logger.info(f"Found {len(opportunities)} arbitrage opportunities")
                        
                        # Execute best opportunity (one at a time for transfers)
                        for opp in opportunities[:1]:  # Only one at a time due to transfers
                            if not self.running:
                                break
                            
                            # Execute complete arbitrage cycle
                            for attempt in range(3):
                                try:
                                    result = await self._execute_complete_arbitrage(opp)
                                    
                                    if result.success:
                                        self.logger.info(f"✅ Arbitrage successful: {result.symbol} - "
                                                       f"Profit: ${result.net_profit:.2f} in {result.total_time_seconds:.0f}s")
                                    else:
                                        self.logger.warning(f"✗ Arbitrage failed: {result.symbol} - "
                                                          f"{result.error_message}")
                                    break
                                    
                                except (ccxt.NetworkError, ccxt.RequestTimeout) as e:
                                    if attempt < 2:
                                        self.logger.warning(f"Network error (attempt {attempt+1}/3): {e}")
                                        await asyncio.sleep(1 * (attempt + 1))
                                        continue
                                    else:
                                        self.logger.error(f"Network error after 3 attempts: {e}")
                                        break
                    
                    # Wait before next iteration
                    await asyncio.sleep(self.config.CHECK_INTERVALS['price_check_seconds'])
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in trading loop: {e}", exc_info=True)
                    await asyncio.sleep(5)
            
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
                    min_spread = self.spread_manager.get_min_spread(symbol)
                    
                    # Check if spread is profitable
                    if spread_percent >= (min_spread * 100):
                        # Get position size
                        position_size = await self.balance_manager.get_adaptive_position_size(
                            symbol, spread_percent / 100, volatility=0.02
                        )
                        
                        if position_size > 0:
                            # Estimate profit
                            estimated_profit = self._estimate_profit(
                                symbol, buy_price, sell_price, position_size,
                                buy_exchange, sell_exchange
                            )
                            
                            if estimated_profit >= MIN_PROFIT_USD:
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
            amount = position_size_usd / buy_price
            
            buy_fee_rate = self.config.EXCHANGE_FEES[buy_exchange]['trading_fee']
            sell_fee_rate = self.config.EXCHANGE_FEES[sell_exchange]['trading_fee']
            
            buy_fee = position_size_usd * buy_fee_rate
            sell_value = amount * sell_price
            sell_fee = sell_value * sell_fee_rate
            
            total_fees = buy_fee + sell_fee
            
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
    
    async def _execute_complete_arbitrage(self, opp: TradeOpportunity) -> CompleteArbitrageResult:
        """
        Execute complete cross-exchange arbitrage cycle:
        1. Buy crypto on cheaper exchange
        2. Transfer crypto to expensive exchange  
        3. Sell crypto on expensive exchange
        4. (Rebalance USDT back - done periodically)
        """
        
        cycle_start_time = time.time()
        
        self.logger.info("=" * 80)
        self.logger.info(f"STARTING COMPLETE ARBITRAGE CYCLE: {opp.symbol}")
        self.logger.info(f"  Buy on {opp.buy_exchange} @ ${opp.buy_price:.6f}")
        self.logger.info(f"  Sell on {opp.sell_exchange} @ ${opp.sell_price:.6f}")
        self.logger.info(f"  Spread: {opp.spread_percent:.3f}%")
        self.logger.info(f"  Position: ${opp.position_size_usd:.2f}")
        self.logger.info(f"  Est. profit: ${opp.estimated_profit:.2f}")
        self.logger.info("=" * 80)
        
        base_currency = opp.symbol.split('/')[0]
        amount = opp.position_size_usd / opp.buy_price
        
        # PHASE 1: BUY on cheaper exchange
        self.logger.info(f"[PHASE 1] Buying {amount:.8f} {base_currency} on {opp.buy_exchange}...")
        
        try:
            buy_order = await asyncio.wait_for(
                self.exchanges[opp.buy_exchange].create_market_buy_order(opp.symbol, amount),
                timeout=ORDER_TIMEOUT_SECONDS
            )
            
            actual_buy_amount = float(buy_order.get('filled', amount))
            actual_buy_price = float(buy_order.get('average', opp.buy_price))
            buy_cost = actual_buy_price * actual_buy_amount
            buy_fee = float(buy_order.get('fee', {}).get('cost', 0))
            
            if buy_fee == 0:
                buy_fee = buy_cost * self.config.EXCHANGE_FEES[opp.buy_exchange]['trading_fee']
            
            self.logger.info(f"✅ Buy successful: {actual_buy_amount:.8f} {base_currency} @ ${actual_buy_price:.6f}")
            self.logger.info(f"   Cost: ${buy_cost:.2f}, Fee: ${buy_fee:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Buy failed: {e}")
            return CompleteArbitrageResult(
                success=False,
                symbol=opp.symbol,
                buy_exchange=opp.buy_exchange,
                sell_exchange=opp.sell_exchange,
                buy_price=opp.buy_price,
                buy_amount=0,
                buy_cost=0,
                buy_fee=0,
                buy_success=False,
                transfer_time_seconds=0,
                transfer_success=False,
                transfer_tx_id=None,
                sell_price=opp.sell_price,
                sell_amount=0,
                sell_revenue=0,
                sell_fee=0,
                sell_success=False,
                gross_profit=0,
                net_profit=0,
                total_fees=0,
                total_time_seconds=(time.time() - cycle_start_time),
                spread_percent=opp.spread_percent,
                slippage_percent=0,
                error_message=f"Buy failed: {e}"
            )
        
        # PHASE 2: TRANSFER crypto to sell exchange
        self.logger.info(f"[PHASE 2] Transferring {actual_buy_amount:.8f} {base_currency} "
                       f"from {opp.buy_exchange} → {opp.sell_exchange}...")
        
        transfer_start = time.time()
        
        try:
            transfer_result = await self.transfer_manager.transfer_crypto(
                from_exchange=opp.buy_exchange,
                to_exchange=opp.sell_exchange,
                currency=base_currency,
                amount=actual_buy_amount
            )
            
            transfer_time = transfer_result.duration_seconds()
            
            if transfer_result.success:
                self.logger.info(f"✅ Transfer successful in {transfer_time:.1f}s")
                self.logger.info(f"   TX ID: {transfer_result.tx_id}")
            else:
                self.logger.error(f"❌ Transfer failed: {transfer_result.error_message}")
                return CompleteArbitrageResult(
                    success=False,
                    symbol=opp.symbol,
                    buy_exchange=opp.buy_exchange,
                    sell_exchange=opp.sell_exchange,
                    buy_price=actual_buy_price,
                    buy_amount=actual_buy_amount,
                    buy_cost=buy_cost,
                    buy_fee=buy_fee,
                    buy_success=True,
                    transfer_time_seconds=transfer_time,
                    transfer_success=False,
                    transfer_tx_id=transfer_result.tx_id,
                    sell_price=opp.sell_price,
                    sell_amount=0,
                    sell_revenue=0,
                    sell_fee=0,
                    sell_success=False,
                    gross_profit=0,
                    net_profit=-buy_fee,  # Lost buy fee
                    total_fees=buy_fee,
                    total_time_seconds=(time.time() - cycle_start_time),
                    spread_percent=opp.spread_percent,
                    slippage_percent=0,
                    error_message=f"Transfer failed: {transfer_result.error_message}"
                )
                
        except Exception as e:
            self.logger.error(f"❌ Transfer error: {e}")
            return CompleteArbitrageResult(
                success=False,
                symbol=opp.symbol,
                buy_exchange=opp.buy_exchange,
                sell_exchange=opp.sell_exchange,
                buy_price=actual_buy_price,
                buy_amount=actual_buy_amount,
                buy_cost=buy_cost,
                buy_fee=buy_fee,
                buy_success=True,
                transfer_time_seconds=0,
                transfer_success=False,
                transfer_tx_id=None,
                sell_price=opp.sell_price,
                sell_amount=0,
                sell_revenue=0,
                sell_fee=0,
                sell_success=False,
                gross_profit=0,
                net_profit=-buy_fee,
                total_fees=buy_fee,
                total_time_seconds=(time.time() - cycle_start_time),
                spread_percent=opp.spread_percent,
                slippage_percent=0,
                error_message=f"Transfer exception: {e}"
            )
        
        # PHASE 3: SELL on expensive exchange
        self.logger.info(f"[PHASE 3] Selling {actual_buy_amount:.8f} {base_currency} on {opp.sell_exchange}...")
        
        try:
            # Get current sell price (may have changed during transfer!)
            current_ticker = await self.exchanges[opp.sell_exchange].fetch_ticker(opp.symbol)
            current_sell_price = current_ticker['last']
            
            # Check if still profitable
            spread_now = ((current_sell_price - actual_buy_price) / actual_buy_price) * 100
            
            if spread_now < 0.5:  # Less than 0.5% spread remaining
                self.logger.warning(f"⚠️  Spread decreased during transfer: {opp.spread_percent:.2f}% → {spread_now:.2f}%")
                self.logger.warning(f"   Selling anyway to complete cycle...")
            else:
                self.logger.info(f"   Current spread: {spread_now:.2f}% (was {opp.spread_percent:.2f}%)")
            
            sell_order = await asyncio.wait_for(
                self.exchanges[opp.sell_exchange].create_market_sell_order(opp.symbol, actual_buy_amount),
                timeout=ORDER_TIMEOUT_SECONDS
            )
            
            actual_sell_amount = float(sell_order.get('filled', actual_buy_amount))
            actual_sell_price = float(sell_order.get('average', current_sell_price))
            sell_revenue = actual_sell_price * actual_sell_amount
            sell_fee = float(sell_order.get('fee', {}).get('cost', 0))
            
            if sell_fee == 0:
                sell_fee = sell_revenue * self.config.EXCHANGE_FEES[opp.sell_exchange]['trading_fee']
            
            self.logger.info(f"✅ Sell successful: {actual_sell_amount:.8f} {base_currency} @ ${actual_sell_price:.6f}")
            self.logger.info(f"   Revenue: ${sell_revenue:.2f}, Fee: ${sell_fee:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Sell failed: {e}")
            return CompleteArbitrageResult(
                success=False,
                symbol=opp.symbol,
                buy_exchange=opp.buy_exchange,
                sell_exchange=opp.sell_exchange,
                buy_price=actual_buy_price,
                buy_amount=actual_buy_amount,
                buy_cost=buy_cost,
                buy_fee=buy_fee,
                buy_success=True,
                transfer_time_seconds=transfer_time,
                transfer_success=True,
                transfer_tx_id=transfer_result.tx_id,
                sell_price=opp.sell_price,
                sell_amount=0,
                sell_revenue=0,
                sell_fee=0,
                sell_success=False,
                gross_profit=0,
                net_profit=-buy_fee,  # Lost buy fee
                total_fees=buy_fee,
                total_time_seconds=(time.time() - cycle_start_time),
                spread_percent=opp.spread_percent,
                slippage_percent=0,
                error_message=f"Sell failed: {e} (crypto stuck on {opp.sell_exchange}!)"
            )
        
        # Calculate final results
        total_fees = buy_fee + sell_fee
        gross_profit = sell_revenue - buy_cost
        net_profit = gross_profit - total_fees
        
        total_time = time.time() - cycle_start_time
        
        # Calculate slippage
        buy_slippage = abs(actual_buy_price - opp.buy_price) / opp.buy_price
        sell_slippage = abs(actual_sell_price - opp.sell_price) / opp.sell_price
        avg_slippage = (buy_slippage + sell_slippage) / 2
        
        # Update statistics
        self.stats['total_arbitrages'] += 1
        if net_profit > 0:
            self.stats['successful_arbitrages'] += 1
        else:
            self.stats['failed_arbitrages'] += 1
        
        self.stats['total_profit_usd'] += gross_profit
        self.stats['total_fees_usd'] += total_fees
        self.stats['net_profit_usd'] += net_profit
        self.stats['total_transfer_time'] += transfer_time
        
        if self.stats['successful_arbitrages'] > 0:
            self.stats['avg_transfer_time'] = self.stats['total_transfer_time'] / self.stats['successful_arbitrages']
        
        if opp.symbol not in self.stats['arbitrages_by_symbol']:
            self.stats['arbitrages_by_symbol'][opp.symbol] = {
                'count': 0,
                'profit': 0,
                'wins': 0,
                'avg_transfer_time': 0
            }
        
        self.stats['arbitrages_by_symbol'][opp.symbol]['count'] += 1
        self.stats['arbitrages_by_symbol'][opp.symbol]['profit'] += net_profit
        if net_profit > 0:
            self.stats['arbitrages_by_symbol'][opp.symbol]['wins'] += 1
        
        # Update auto-sizer
        trade_result_obj = AutoSizerTradeResult(
            symbol=opp.symbol,
            timestamp=datetime.now(),
            position_size=opp.position_size_usd,
            entry_price=actual_buy_price,
            exit_price=actual_sell_price,
            profit=net_profit,
            profit_percent=net_profit / opp.position_size_usd if opp.position_size_usd > 0 else 0,
            success=net_profit > 0,
            slippage=avg_slippage
        )
        self.auto_sizer.record_trade(trade_result_obj)
        
        # Update spread manager
        spread_opp = SpreadOpportunity(
            symbol=opp.symbol,
            timestamp=datetime.now(),
            spread=opp.spread_percent / 100,
            traded=True,
            success=net_profit > 0,
            profit=net_profit
        )
        self.spread_manager.record_spread_opportunity(spread_opp)
        
        # PHASE 4: REBALANCE - Transfer USDT back to buy exchange
        self.logger.info(f"[PHASE 4] Rebalancing: Transfer USDT from {opp.sell_exchange} → {opp.buy_exchange}...")
        
        rebalance_start = time.time()
        
        try:
            # Calculate amount to transfer back
            # We sold crypto for USDT, now need to move USDT back
            usdt_to_transfer = sell_revenue - sell_fee  # Amount we received from sell
            
            self.logger.info(f"Transferring ${usdt_to_transfer:.2f} USDT for rebalancing...")
            
            rebalance_result = await self.transfer_manager.transfer_crypto(
                from_exchange=opp.sell_exchange,  # From sell exchange (has USDT)
                to_exchange=opp.buy_exchange,      # To buy exchange (needs USDT)
                currency='USDT',
                amount=usdt_to_transfer
            )
            
            rebalance_time = rebalance_result.duration_seconds()
            
            if rebalance_result.success:
                self.logger.info(f"✅ Rebalancing successful in {rebalance_time:.1f}s")
                self.logger.info(f"   Account is now balanced and ready for next arbitrage!")
            else:
                self.logger.warning(f"⚠️  Rebalancing failed: {rebalance_result.error_message}")
                self.logger.warning(f"   USDT accumulated on {opp.sell_exchange}")
                self.logger.warning(f"   Will need manual rebalancing or will rebalance on next opposite-direction trade")
                
        except Exception as e:
            self.logger.warning(f"⚠️  Rebalancing error: {e}")
            self.logger.warning(f"   USDT on {opp.sell_exchange}, crypto on {opp.buy_exchange}")
            self.logger.warning(f"   Account will rebalance naturally on opposite-direction trades")
        
        # Update total time to include rebalancing
        total_time = time.time() - cycle_start_time
        
        # Log summary
        self.logger.info("=" * 80)
        self.logger.info(f"COMPLETE ARBITRAGE CYCLE FINISHED: {opp.symbol}")
        self.logger.info(f"  Buy:       ${buy_cost:.2f} on {opp.buy_exchange}")
        self.logger.info(f"  Transfer:  {transfer_time:.1f}s ({base_currency})")
        self.logger.info(f"  Sell:      ${sell_revenue:.2f} on {opp.sell_exchange}")
        self.logger.info(f"  Rebalance: {rebalance_time if 'rebalance_time' in locals() else 'N/A'}s (USDT)")
        self.logger.info(f"  Fees:      ${total_fees:.2f}")
        self.logger.info(f"  Profit:    ${net_profit:.2f} ({(net_profit/buy_cost)*100:.2f}%)")
        self.logger.info(f"  Total Time: {total_time:.1f}s")
        self.logger.info("=" * 80)
        
        return CompleteArbitrageResult(
            success=True,
            symbol=opp.symbol,
            buy_exchange=opp.buy_exchange,
            sell_exchange=opp.sell_exchange,
            buy_price=actual_buy_price,
            buy_amount=actual_buy_amount,
            buy_cost=buy_cost,
            buy_fee=buy_fee,
            buy_success=True,
            transfer_time_seconds=transfer_time,
            transfer_success=True,
            transfer_tx_id=transfer_result.tx_id,
            sell_price=actual_sell_price,
            sell_amount=actual_sell_amount,
            sell_revenue=sell_revenue,
            sell_fee=sell_fee,
            sell_success=True,
            gross_profit=gross_profit,
            net_profit=net_profit,
            total_fees=total_fees,
            total_time_seconds=total_time,
            spread_percent=opp.spread_percent,
            slippage_percent=avg_slippage * 100
        )
    
    async def _monitoring_loop(self):
        """Monitoring loop"""
        try:
            self.logger.info("Monitoring loop started")
            
            while self.running and not self.shutdown_event.is_set():
                try:
                    await asyncio.sleep(300)  # Every 5 minutes
                    self._log_statistics()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
            
            self.logger.info("Monitoring loop stopped")
        except asyncio.CancelledError:
            self.logger.info("Monitoring loop cancelled")
    
    async def _balance_refresh_loop(self):
        """Balance refresh loop"""
        try:
            self.logger.info("Balance refresh loop started")
            
            while self.running and not self.shutdown_event.is_set():
                try:
                    await asyncio.sleep(BALANCE_REFRESH_INTERVAL)
                    
                    for exchange_name in self.exchanges.keys():
                        try:
                            await self.exchanges[exchange_name].fetch_balance()
                        except Exception as e:
                            self.logger.error(f"Error refreshing {exchange_name} balance: {e}")
                    
                    self.logger.debug("Balances refreshed")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in balance refresh loop: {e}")
            
            self.logger.info("Balance refresh loop stopped")
        except asyncio.CancelledError:
            self.logger.info("Balance refresh loop cancelled")
    
    async def _recovery_loop(self):
        """Auto-recovery loop - runs every 5 minutes"""
        try:
            self.logger.info("Auto-recovery loop started")
            
            while self.running and not self.shutdown_event.is_set():
                try:
                    await asyncio.sleep(300)  # Check every 5 minutes
                    
                    self.logger.info("Running auto-recovery checks...")
                    
                    # Run health check
                    health = await self.recovery_system.run_health_check()
                    
                    # If issues found, attempt recovery
                    if health['overall_status'] != 'healthy':
                        self.logger.warning(f"Health check found {health['issues_found']} issues")
                        
                        # Check for stuck positions
                        if health['stuck_positions'] > 0:
                            self.logger.info("Attempting to recover stuck positions...")
                            recovered = await self.recovery_system.auto_recover_all_stuck_positions()
                            self.logger.info(f"Recovered {recovered}/{health['stuck_positions']} stuck positions")
                        
                        # Check exchange health
                        for exchange_name, is_healthy in health['exchanges_healthy'].items():
                            if not is_healthy:
                                self.logger.warning(f"{exchange_name} appears down, waiting for recovery...")
                                await self.recovery_system.wait_for_exchange_recovery(exchange_name, max_wait_minutes=5)
                    
                    # Log recovery stats
                    recovery_stats = self.recovery_system.get_recovery_statistics()
                    if recovery_stats['total_issues_detected'] > 0:
                        self.logger.info(f"Recovery stats: {recovery_stats['auto_recovered']}/{recovery_stats['total_issues_detected']} "
                                       f"issues auto-recovered ({recovery_stats['recovery_success_rate']*100:.1f}%)")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in recovery loop: {e}", exc_info=True)
            
            self.logger.info("Auto-recovery loop stopped")
        except asyncio.CancelledError:
            self.logger.info("Auto-recovery loop cancelled")
    
    def _log_statistics(self):
        """Log statistics"""
        try:
            runtime = datetime.now() - self.stats['start_time']
            hours = runtime.total_seconds() / 3600
            
            self.logger.info("=" * 80)
            self.logger.info("STATISTICS UPDATE")
            self.logger.info("=" * 80)
            self.logger.info(f"Runtime: {runtime}")
            self.logger.info(f"Total arbitrage cycles: {self.stats['total_arbitrages']}")
            self.logger.info(f"Successful: {self.stats['successful_arbitrages']}")
            self.logger.info(f"Failed: {self.stats['failed_arbitrages']}")
            
            if self.stats['total_arbitrages'] > 0:
                success_rate = (self.stats['successful_arbitrages'] / self.stats['total_arbitrages']) * 100
                self.logger.info(f"Success rate: {success_rate:.1f}%")
            
            self.logger.info(f"Gross profit: ${self.stats['total_profit_usd']:.2f}")
            self.logger.info(f"Total fees: ${self.stats['total_fees_usd']:.2f}")
            self.logger.info(f"Net profit: ${self.stats['net_profit_usd']:.2f}")
            self.logger.info(f"Avg transfer time: {self.stats['avg_transfer_time']:.1f}s")
            
            if self.initial_balance > 0:
                current_balance = self.initial_balance + self.stats['net_profit_usd']
                profit_percent = (self.stats['net_profit_usd'] / self.initial_balance) * 100
                self.logger.info(f"Current balance: ${current_balance:.2f} ({profit_percent:+.2f}%)")
            
            if hours > 0:
                hourly_profit = self.stats['net_profit_usd'] / hours
                self.logger.info(f"Hourly profit: ${hourly_profit:.2f}")
                daily_profit = hourly_profit * 24
                self.logger.info(f"Projected daily: ${daily_profit:.2f}")
            
            self.logger.info(f"Opportunities found: {self.stats['opportunities_found']}")
            self.logger.info(f"Opportunities rejected: {self.stats['opportunities_rejected']}")
            
            if self.stats['arbitrages_by_symbol']:
                self.logger.info("\nPer-symbol statistics:")
                for symbol, data in sorted(self.stats['arbitrages_by_symbol'].items(), 
                                          key=lambda x: x[1]['profit'], reverse=True):
                    success_rate = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0
                    self.logger.info(f"  {symbol}: {data['count']} cycles, "
                                   f"${data['profit']:.2f} profit, "
                                   f"{success_rate:.1f}% success")
            
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"Error logging statistics: {e}")
    
    async def shutdown(self):
        """Graceful shutdown"""
        try:
            self.logger.info("=" * 80)
            self.logger.info("SHUTTING DOWN BOT")
            self.logger.info("=" * 80)
            
            self.running = False
            
            # Log final statistics
            self._log_statistics()
            
            # Log transfer statistics
            transfer_stats = self.transfer_manager.get_transfer_statistics()
            self.logger.info("\nTransfer Statistics:")
            self.logger.info(f"  Total transfers: {transfer_stats['total_transfers']}")
            self.logger.info(f"  Success rate: {transfer_stats['success_rate']*100:.1f}%")
            self.logger.info(f"  Avg time: {transfer_stats['avg_transfer_time_seconds']:.1f}s")
            
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
        bot = AggressiveArbitrageBotWithTransfers()
        await bot.initialize()
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

