#!/usr/bin/env python3
"""
Coinbase + Gemini Arbitrage Bot
TRUE Cross-Exchange Arbitrage: Buy → Transfer → Sell → Rebalance
Optimized for US markets with one-time address whitelisting
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass

# Import configuration and components
from coinbase_gemini_config import Config
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from auto_sizing_manager import AutoSizingManager, TradeResult as AutoSizerTradeResult
from dynamic_spread_manager import DynamicSpreadManager
from dynamic_slippage_detector import DynamicSlippageDetector
from smart_rate_limiter import SmartRateLimiter
from balance_validator import BalanceValidator
from fixed_percentage_balance_manager import FixedPercentageBalanceManager
from comprehensive_error_handler import ComprehensiveErrorHandler
from transfer_manager_fixed import TransferManager, TransferResult
from auto_recovery_system import AutoRecoverySystem, StuckPosition

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
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
class CompleteArbitrageResult:
    """Result of complete arbitrage cycle"""
    success: bool
    symbol: str = ""
    buy_exchange: str = ""
    sell_exchange: str = ""
    buy_price: float = 0.0
    buy_amount: float = 0.0
    buy_cost: float = 0.0
    buy_fee: float = 0.0
    transfer_time_seconds: float = 0.0
    sell_price: float = 0.0
    sell_amount: float = 0.0
    sell_revenue: float = 0.0
    sell_fee: float = 0.0
    gross_profit: float = 0.0
    net_profit: float = 0.0
    total_fees: float = 0.0
    total_time_seconds: float = 0.0
    spread_percent: float = 0.0
    error_message: Optional[str] = None

class CoinbaseGeminiArbitrageBot:
    """Arbitrage bot for Coinbase + Gemini"""
    
    def __init__(self):
        """Initialize the bot"""
        self.logger = logger
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Components (will be initialized in initialize())
        self.exchange_manager = None
        self.auto_sizer = None
        self.spread_manager = None
        self.slippage_detector = None
        self.rate_limiter = None
        self.balance_validator = None
        self.balance_manager = None
        self.error_handler = None
        self.transfer_manager = None
        self.recovery_system = None
        
        # Statistics
        self.stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_profit': 0.0,
            'total_fees': 0.0,
            'opportunities_found': 0,
            'opportunities_executed': 0,
            'start_time': None,
            'initial_balance_usd': 0.0,
            'current_balance_usd': 0.0,
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.shutdown_event.set()
    
    async def initialize(self):
        """Initialize all components"""
        self.logger.info("=" * 80)
        self.logger.info("INITIALIZING COINBASE + GEMINI ARBITRAGE BOT")
        self.logger.info("=" * 80)
        
        # Validate API keys
        if not Config.COINBASE_API_KEY or not Config.GEMINI_API_KEY:
            raise ValueError("API keys not configured. Please set up .env file.")
        
        # Initialize exchange manager
        self.logger.info("Initializing exchange manager...")
        self.exchange_manager = CoinbaseGeminiExchangeManager()
        await self.exchange_manager.initialize()
        
        # Initialize components
        self.logger.info("Initializing trading components...")
        
        self.auto_sizer = AutoSizingManager(Config.BASE_POSITION_PERCENTAGES)
        self.spread_manager = DynamicSpreadManager(Config.CURRENCY_PAIR_SPREADS)
        self.slippage_detector = DynamicSlippageDetector(Config.SLIPPAGE_ESTIMATES)
        self.rate_limiter = SmartRateLimiter(Config.RATE_LIMITS)
        self.balance_validator = BalanceValidator(self.exchange_manager)
        self.balance_manager = FixedPercentageBalanceManager(
            self.exchange_manager,
            self.balance_validator,
            Config.BASE_POSITION_PERCENTAGES,
            Config.MAX_POSITION_PERCENT_PER_TRADE,
            Config.MAX_TOTAL_EXPOSURE_PERCENT,
            Config.RESERVE_PERCENT
        )
        self.error_handler = ComprehensiveErrorHandler()
        self.transfer_manager = TransferManager(self.exchange_manager)
        self.recovery_system = AutoRecoverySystem(self.exchange_manager)
        
        # Get initial balance
        self.logger.info("Fetching initial balances...")
        total_balance = await self.balance_manager.get_total_account_value_usd()
        self.stats['initial_balance_usd'] = total_balance
        self.stats['current_balance_usd'] = total_balance
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"✅ Initial balance: ${total_balance:,.2f}")
        self.logger.info("=" * 80)
        self.logger.info("BOT INITIALIZATION COMPLETE - READY FOR ARBITRAGE")
        self.logger.info("=" * 80)
        
        return True
    
    async def scan_for_opportunities(self) -> List[TradeOpportunity]:
        """Scan all currency pairs for arbitrage opportunities"""
        opportunities = []
        
        for symbol in Config.CURRENCY_PAIRS:
            try:
                # Check rate limits
                if not await self.rate_limiter.can_make_request('coinbase'):
                    await asyncio.sleep(0.1)
                if not await self.rate_limiter.can_make_request('gemini'):
                    await asyncio.sleep(0.1)
                
                # Fetch prices from both exchanges
                coinbase_ticker = await self.exchange_manager.fetch_ticker('coinbase', symbol)
                await self.rate_limiter.record_request('coinbase')
                
                gemini_ticker = await self.exchange_manager.fetch_ticker('gemini', symbol)
                await self.rate_limiter.record_request('gemini')
                
                # Get bid/ask prices
                coinbase_bid = coinbase_ticker.get('bid')
                coinbase_ask = coinbase_ticker.get('ask')
                gemini_bid = gemini_ticker.get('bid')
                gemini_ask = gemini_ticker.get('ask')
                
                if not all([coinbase_bid, coinbase_ask, gemini_bid, gemini_ask]):
                    continue
                
                # Calculate spreads both directions
                # Direction 1: Buy on Coinbase, sell on Gemini
                spread_cb_to_gem = gemini_bid - coinbase_ask
                spread_cb_to_gem_pct = (spread_cb_to_gem / coinbase_ask) * 100
                
                # Direction 2: Buy on Gemini, sell on Coinbase
                spread_gem_to_cb = coinbase_bid - gemini_ask
                spread_gem_to_cb_pct = (spread_gem_to_cb / gemini_ask) * 100
                
                # Get minimum required spread
                min_spread = self.spread_manager.get_min_spread(symbol)
                
                # Check if either direction is profitable
                if spread_cb_to_gem_pct >= min_spread * 100:
                    # Buy on Coinbase, sell on Gemini
                    position_size = await self.balance_manager.get_adaptive_position_size(
                        symbol, coinbase_ask
                    )
                    
                    estimated_profit = (spread_cb_to_gem * position_size) - \
                                     (coinbase_ask * position_size * (Config.EXCHANGE_FEES['coinbase']['taker'] + 
                                                                       Config.EXCHANGE_FEES['gemini']['taker']))
                    
                    if estimated_profit >= Config.MIN_PROFIT_USD:
                        opportunities.append(TradeOpportunity(
                            symbol=symbol,
                            buy_exchange='coinbase',
                            sell_exchange='gemini',
                            buy_price=coinbase_ask,
                            sell_price=gemini_bid,
                            spread=spread_cb_to_gem,
                            spread_percent=spread_cb_to_gem_pct,
                            position_size_usd=position_size,
                            estimated_profit=estimated_profit,
                            timestamp=datetime.now()
                        ))
                
                elif spread_gem_to_cb_pct >= min_spread * 100:
                    # Buy on Gemini, sell on Coinbase
                    position_size = await self.balance_manager.get_adaptive_position_size(
                        symbol, gemini_ask
                    )
                    
                    estimated_profit = (spread_gem_to_cb * position_size) - \
                                     (gemini_ask * position_size * (Config.EXCHANGE_FEES['gemini']['taker'] + 
                                                                     Config.EXCHANGE_FEES['coinbase']['taker']))
                    
                    if estimated_profit >= Config.MIN_PROFIT_USD:
                        opportunities.append(TradeOpportunity(
                            symbol=symbol,
                            buy_exchange='gemini',
                            sell_exchange='coinbase',
                            buy_price=gemini_ask,
                            sell_price=coinbase_bid,
                            spread=spread_gem_to_cb,
                            spread_percent=spread_gem_to_cb_pct,
                            position_size_usd=position_size,
                            estimated_profit=estimated_profit,
                            timestamp=datetime.now()
                        ))
                
            except Exception as e:
                self.logger.debug(f"Error scanning {symbol}: {e}")
                continue
        
        return opportunities
    
    async def execute_arbitrage(self, opp: TradeOpportunity) -> CompleteArbitrageResult:
        """Execute complete arbitrage cycle: Buy → Transfer → Sell → Rebalance"""
        
        start_time = time.time()
        self.logger.info("=" * 80)
        self.logger.info(f"🎯 EXECUTING ARBITRAGE: {opp.symbol}")
        self.logger.info(f"   Buy on {opp.buy_exchange} @ ${opp.buy_price:.6f}")
        self.logger.info(f"   Sell on {opp.sell_exchange} @ ${opp.sell_price:.6f}")
        self.logger.info(f"   Spread: {opp.spread_percent:.3f}%")
        self.logger.info(f"   Position: ${opp.position_size_usd:.2f}")
        self.logger.info(f"   Est. profit: ${opp.estimated_profit:.2f}")
        self.logger.info("=" * 80)
        
        # PHASE 1: BUY
        self.logger.info("[PHASE 1] Buying on {opp.buy_exchange}...")
        
        base_currency = opp.symbol.split('/')[0]
        buy_amount = opp.position_size_usd / opp.buy_price
        
        try:
            buy_order = await self.exchange_manager.create_order(
                exchange_id=opp.buy_exchange,
                symbol=opp.symbol,
                order_type='market',
                side='buy',
                amount=buy_amount
            )
            
            # Wait for order to fill
            await asyncio.sleep(1)
            filled_order = await self.exchange_manager.fetch_order(
                opp.buy_exchange, buy_order['id'], opp.symbol
            )
            
            actual_buy_amount = filled_order.get('filled', buy_amount)
            actual_buy_price = filled_order.get('average', opp.buy_price)
            buy_cost = filled_order.get('cost', actual_buy_amount * actual_buy_price)
            buy_fee = filled_order.get('fee', {}).get('cost', buy_cost * Config.EXCHANGE_FEES[opp.buy_exchange]['taker'])
            
            self.logger.info(f"✅ Buy complete: {actual_buy_amount:.8f} {base_currency} @ ${actual_buy_price:.6f}")
            
        except Exception as e:
            self.logger.error(f"❌ Buy failed: {e}")
            return CompleteArbitrageResult(success=False, error_message=f"Buy failed: {e}")
        
        # PHASE 2: TRANSFER
        self.logger.info(f"[PHASE 2] Transferring {actual_buy_amount:.8f} {base_currency} to {opp.sell_exchange}...")
        
        transfer_result = await self.transfer_manager.transfer_crypto(
            from_exchange=opp.buy_exchange,
            to_exchange=opp.sell_exchange,
            currency=base_currency,
            amount=actual_buy_amount
        )
        
        if not transfer_result.success:
            self.logger.error(f"❌ Transfer failed: {transfer_result.error_message}")
            # Record stuck position for recovery
            self.recovery_system.add_stuck_position(StuckPosition(
                symbol=opp.symbol,
                exchange=opp.buy_exchange,
                amount=actual_buy_amount,
                price=actual_buy_price,
                timestamp=datetime.now(),
                status='transfer_failed'
            ))
            return CompleteArbitrageResult(success=False, error_message=f"Transfer failed: {transfer_result.error_message}")
        
        transfer_time = transfer_result.duration_seconds()
        self.logger.info(f"✅ Transfer complete in {transfer_time:.1f}s")
        
        # PHASE 3: SELL
        self.logger.info(f"[PHASE 3] Selling on {opp.sell_exchange}...")
        
        try:
            sell_order = await self.exchange_manager.create_order(
                exchange_id=opp.sell_exchange,
                symbol=opp.symbol,
                order_type='market',
                side='sell',
                amount=actual_buy_amount
            )
            
            # Wait for order to fill
            await asyncio.sleep(1)
            filled_sell_order = await self.exchange_manager.fetch_order(
                opp.sell_exchange, sell_order['id'], opp.symbol
            )
            
            actual_sell_amount = filled_sell_order.get('filled', actual_buy_amount)
            actual_sell_price = filled_sell_order.get('average', opp.sell_price)
            sell_revenue = filled_sell_order.get('cost', actual_sell_amount * actual_sell_price)
            sell_fee = filled_sell_order.get('fee', {}).get('cost', sell_revenue * Config.EXCHANGE_FEES[opp.sell_exchange]['taker'])
            
            self.logger.info(f"✅ Sell complete: {actual_sell_amount:.8f} {base_currency} @ ${actual_sell_price:.6f}")
            
        except Exception as e:
            self.logger.error(f"❌ Sell failed: {e}")
            return CompleteArbitrageResult(success=False, error_message=f"Sell failed: {e}")
        
        # PHASE 4: REBALANCE (Transfer USD back)
        self.logger.info(f"[PHASE 4] Rebalancing: Transfer USD from {opp.sell_exchange} → {opp.buy_exchange}...")
        
        try:
            usdt_to_transfer = sell_revenue - sell_fee
            rebalance_result = await self.transfer_manager.transfer_crypto(
                from_exchange=opp.sell_exchange,
                to_exchange=opp.buy_exchange,
                currency='USD',
                amount=usdt_to_transfer
            )
            
            if rebalance_result.success:
                self.logger.info(f"✅ Rebalancing complete")
            else:
                self.logger.warning(f"⚠️ Rebalancing failed: {rebalance_result.error_message}")
        except Exception as e:
            self.logger.warning(f"⚠️ Rebalancing error: {e}")
        
        # Calculate results
        total_time = time.time() - start_time
        gross_profit = sell_revenue - buy_cost
        total_fees = buy_fee + sell_fee
        net_profit = gross_profit - total_fees
        
        # Log results
        self.logger.info("=" * 80)
        self.logger.info(f"✅ ARBITRAGE COMPLETE: {opp.symbol}")
        self.logger.info(f"   Buy cost: ${buy_cost:.2f}")
        self.logger.info(f"   Sell revenue: ${sell_revenue:.2f}")
        self.logger.info(f"   Gross profit: ${gross_profit:.2f}")
        self.logger.info(f"   Total fees: ${total_fees:.2f}")
        self.logger.info(f"   Net profit: ${net_profit:.2f}")
        self.logger.info(f"   Total time: {total_time:.1f}s")
        self.logger.info("=" * 80)
        
        # Update statistics
        self.stats['total_trades'] += 1
        self.stats['successful_trades'] += 1
        self.stats['total_profit'] += net_profit
        self.stats['total_fees'] += total_fees
        
        # Record trade for auto-sizing
        self.auto_sizer.record_trade(AutoSizerTradeResult(
            symbol=opp.symbol,
            profit=net_profit,
            success=True,
            spread=opp.spread_percent,
            timestamp=datetime.now()
        ))
        
        # Record opportunity for spread manager
        self.spread_manager.record_opportunity(opp.symbol, opp.spread_percent / 100, True)
        
        return CompleteArbitrageResult(
            success=True,
            symbol=opp.symbol,
            buy_exchange=opp.buy_exchange,
            sell_exchange=opp.sell_exchange,
            buy_price=actual_buy_price,
            buy_amount=actual_buy_amount,
            buy_cost=buy_cost,
            buy_fee=buy_fee,
            transfer_time_seconds=transfer_time,
            sell_price=actual_sell_price,
            sell_amount=actual_sell_amount,
            sell_revenue=sell_revenue,
            sell_fee=sell_fee,
            gross_profit=gross_profit,
            net_profit=net_profit,
            total_fees=total_fees,
            total_time_seconds=total_time,
            spread_percent=opp.spread_percent
        )
    
    async def trading_loop(self):
        """Main trading loop"""
        self.logger.info("🚀 Starting trading loop...")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Scan for opportunities
                opportunities = await self.scan_for_opportunities()
                
                if opportunities:
                    self.logger.info(f"📊 Found {len(opportunities)} opportunities")
                    self.stats['opportunities_found'] += len(opportunities)
                    
                    # Sort by estimated profit
                    opportunities.sort(key=lambda x: x.estimated_profit, reverse=True)
                    
                    # Execute best opportunity
                    best_opp = opportunities[0]
                    self.logger.info(f"🎯 Executing best opportunity: {best_opp.symbol} ({best_opp.spread_percent:.3f}%)")
                    
                    result = await self.execute_arbitrage(best_opp)
                    
                    if result.success:
                        self.stats['opportunities_executed'] += 1
                        self.logger.info(f"✅ Trade successful: ${result.net_profit:.2f} profit")
                    else:
                        self.stats['failed_trades'] += 1
                        self.logger.warning(f"⚠️ Trade failed: {result.error_message}")
                
                # Wait before next scan
                await asyncio.sleep(Config.CHECK_INTERVAL_SECONDS)
                
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(10)
    
    async def monitoring_loop(self):
        """Monitor performance and log statistics"""
        while self.running and not self.shutdown_event.is_set():
            try:
                # Update current balance
                total_balance = await self.balance_manager.get_total_account_value_usd()
                self.stats['current_balance_usd'] = total_balance
                
                # Calculate performance
                if self.stats['start_time']:
                    elapsed = (datetime.now() - self.stats['start_time']).total_seconds() / 3600
                    roi = ((total_balance - self.stats['initial_balance_usd']) / self.stats['initial_balance_usd']) * 100
                    
                    self.logger.info("=" * 80)
                    self.logger.info("📊 PERFORMANCE SUMMARY")
                    self.logger.info("=" * 80)
                    self.logger.info(f"Running time: {elapsed:.1f} hours")
                    self.logger.info(f"Initial balance: ${self.stats['initial_balance_usd']:,.2f}")
                    self.logger.info(f"Current balance: ${total_balance:,.2f}")
                    self.logger.info(f"Total profit: ${self.stats['total_profit']:.2f}")
                    self.logger.info(f"Total fees: ${self.stats['total_fees']:.2f}")
                    self.logger.info(f"ROI: {roi:.2f}%")
                    self.logger.info(f"Trades: {self.stats['successful_trades']}/{self.stats['total_trades']}")
                    self.logger.info(f"Opportunities: {self.stats['opportunities_executed']}/{self.stats['opportunities_found']}")
                    self.logger.info("=" * 80)
                
                # Wait 5 minutes before next update
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def balance_refresh_loop(self):
        """Periodically refresh balance cache"""
        while self.running and not self.shutdown_event.is_set():
            try:
                await self.balance_validator.refresh_balance_cache()
                await asyncio.sleep(30)
            except Exception as e:
                self.logger.error(f"Error refreshing balance: {e}")
                await asyncio.sleep(60)
    
    async def recovery_loop(self):
        """Auto-recovery loop"""
        while self.running and not self.shutdown_event.is_set():
            try:
                await self.recovery_system.run_health_check()
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in recovery loop: {e}")
                await asyncio.sleep(60)
    
    async def run(self):
        """Run the bot"""
        self.running = True
        
        try:
            # Initialize
            await self.initialize()
            
            self.logger.info("🚀 STARTING COINBASE + GEMINI ARBITRAGE BOT")
            self.logger.info("=" * 80)
            
            # Start all loops
            await asyncio.gather(
                self.trading_loop(),
                self.monitoring_loop(),
                self.balance_refresh_loop(),
                self.recovery_loop(),
            )
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            self.logger.error(f"Bot crashed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("=" * 80)
        self.logger.info("SHUTTING DOWN BOT")
        self.logger.info("=" * 80)
        
        self.running = False
        self.shutdown_event.set()
        
        # Close exchange connections
        if self.exchange_manager:
            await self.exchange_manager.close()
        
        # Final statistics
        self.logger.info("Final Statistics:")
        self.logger.info(f"  Total trades: {self.stats['total_trades']}")
        self.logger.info(f"  Successful: {self.stats['successful_trades']}")
        self.logger.info(f"  Failed: {self.stats['failed_trades']}")
        self.logger.info(f"  Total profit: ${self.stats['total_profit']:.2f}")
        self.logger.info(f"  Total fees: ${self.stats['total_fees']:.2f}")
        
        if self.stats['initial_balance_usd'] > 0:
            roi = ((self.stats['current_balance_usd'] - self.stats['initial_balance_usd']) / 
                   self.stats['initial_balance_usd']) * 100
            self.logger.info(f"  ROI: {roi:.2f}%")
        
        self.logger.info("=" * 80)
        self.logger.info("BOT SHUTDOWN COMPLETE")
        self.logger.info("=" * 80)

async def main():
    """Main entry point"""
    bot = CoinbaseGeminiArbitrageBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())

