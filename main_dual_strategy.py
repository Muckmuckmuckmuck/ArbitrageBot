#!/usr/bin/env python3
"""
Dual Market Making Bot
Runs market making on both exchanges concurrently:

🔵 COINBASE: Market Making (Top pairs)
   - Strategy: Passive market making with dynamic grid orders
   - Pairs: BTC/USD, ETH/USD, SOL/USD, etc. (high liquidity pairs)
   - Execution: Continuous loop with 15s updates
   - Dynamic: Adjusts order size and spacing based on spread and performance

🟢 GEMINI: Market Making (Top pairs)
   - Strategy: Passive market making with dynamic grid orders
   - Pairs: ARB/USD, OP/USD, LINK/USD, etc. (filtered by availability)
   - Execution: Continuous loop with 15s updates
   - Dynamic: Adjusts order size and spacing based on spread and performance

Both strategies run concurrently on Railway with independent loops.
Both systems dynamically adjust order sizes, grid spacing, and focus on profitable pairs.
"""

import asyncio
import logging
import signal
import sys
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from coinbase_market_making_engine import CoinbaseMarketMakingEngine
from gemini_market_making_engine import GeminiMarketMakingEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DualStrategyBot:
    """Manages both market making strategies running concurrently"""
    
    def __init__(self):
        self.exchange_manager = None
        self.coinbase_market_making_engine = None
        self.gemini_market_making_engine = None
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.portfolio_baseline = None
        self.portfolio_peak_value = None
        self.portfolio_monitor_task = None
        self.portfolio_monitor_interval = 180  # seconds
        
    async def initialize(self):
        """Initialize both market making strategies"""
        logger.info("=" * 80)
        logger.info("🚀 INITIALIZING DUAL MARKET MAKING BOT")
        logger.info("=" * 80)
        logger.info("   Strategy 1: 🔵 Coinbase Market Making")
        logger.info("   Strategy 2: 🟢 Gemini Market Making")
        logger.info("=" * 80)
        
        # Initialize exchange manager
        self.exchange_manager = CoinbaseGeminiExchangeManager()
        await self.exchange_manager.initialize()
        
        # ====================================================================
        # 🔵 COINBASE STRATEGY: Market Making
        # ====================================================================
        logger.info("\n📊 Initializing Coinbase Market-Making Engine...")
        try:
            self.coinbase_market_making_engine = CoinbaseMarketMakingEngine(
                exchange_manager=self.exchange_manager,
                capital_per_pair=50.0,  # $50 per pair
                grid_spacing_percent=0.20,  # 0.20% base spacing (dynamically adjusted)
                order_size_percent=0.10,  # 10% of capital per order = $5 per order
                min_spread_percent=1.00,  # 🔵 1.00% minimum - Ensures profitability (0.80% fees + 0.20% profit buffer)
                max_inventory_percent=0.25,  # Max 25% in one asset
                requote_interval_seconds=15,  # Update every 15s
                stop_loss_percent=0.02,  # -2% stop loss
                take_profit_interval_minutes=60,  # Flatten every hour
            )
            await self.coinbase_market_making_engine.initialize()
            logger.info("   ✅ Coinbase Market-Making Engine initialized successfully")
        except Exception as e:
            logger.error(f"   ❌ Failed to initialize Coinbase Market-Making Engine: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        # ====================================================================
        # 🟢 GEMINI STRATEGY: Market Making (OPTIONAL - only if Gemini is available)
        # ====================================================================
        self.gemini_market_making_engine = None
        if self.exchange_manager.is_exchange_available('gemini'):
            logger.info("\n📊 Initializing Gemini Market-Making Engine...")
            try:
                self.gemini_market_making_engine = GeminiMarketMakingEngine(
                    exchange_manager=self.exchange_manager,
                    capital_per_pair=50.0,  # $50 per pair
                    grid_spacing_percent=0.20,  # 0.20% base spacing (dynamically adjusted)
                    order_size_percent=0.10,  # 10% of capital per order = $5 per order
                    min_spread_percent=0.30,  # 🟢 0.30% minimum (0.10% maker fee × 2 = 0.20% + 0.10% buffer)
                    max_inventory_percent=0.25,  # Max 25% in one asset
                    requote_interval_seconds=15,  # Update every 15s
                    stop_loss_percent=0.02,  # -2% stop loss
                    take_profit_interval_minutes=60,  # Flatten every hour
                )
                await self.gemini_market_making_engine.initialize()
                logger.info("   ✅ Gemini Market-Making Engine initialized successfully")
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to initialize Gemini Market-Making Engine: {e}")
                logger.warning(f"   💡 Bot will continue with Coinbase market making only")
                self.gemini_market_making_engine = None
        else:
            logger.warning("\n⚠️ Gemini exchange not available - skipping Market-Making Engine initialization")
            logger.warning("   💡 Bot will run with Coinbase market making only")
        
        if self.gemini_market_making_engine:
            logger.info("\n✅ Both market making strategies initialized successfully!")
        else:
            logger.info("\n✅ Coinbase market making strategy initialized successfully!")
        logger.info("=" * 80)
    
    # ========================================================================
    # 🔵 COINBASE STRATEGY: Market Making Loop
    # ========================================================================
    async def run_coinbase_market_making(self):
        """🔵 Run Coinbase market-making strategy"""
        logger.info("\n🚀 Starting Coinbase Market-Making Strategy...")
        
        try:
            await self.coinbase_market_making_engine.run_market_making_loop()
        except asyncio.CancelledError:
            logger.info("   🛑 Coinbase market-making strategy cancelled")
        except Exception as e:
            logger.error(f"❌ Error in Coinbase market-making strategy: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # ========================================================================
    # 🟢 GEMINI STRATEGY: Market Making Loop
    # ========================================================================
    async def run_gemini_market_making(self):
        """🟢 Run Gemini market-making strategy"""
        if not self.gemini_market_making_engine:
            logger.warning("   ⚠️ Gemini market-making strategy skipped - Gemini not available")
            return
        
        logger.info("\n🚀 Starting Gemini Market-Making Strategy...")
        
        try:
            await self.gemini_market_making_engine.run_market_making_loop()
        except asyncio.CancelledError:
            logger.info("   🛑 Gemini market-making strategy cancelled")
        except Exception as e:
            logger.error(f"❌ Error in Gemini market-making strategy: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def run(self):
        """Run both market making strategies concurrently"""
        self.running = True
        
        # Start strategies as concurrent tasks
        coinbase_task = asyncio.create_task(self.run_coinbase_market_making())
        tasks = [coinbase_task]
        
        if self.gemini_market_making_engine:
            gemini_task = asyncio.create_task(self.run_gemini_market_making())
            tasks.append(gemini_task)
        else:
            logger.info("   ⚠️ Gemini market-making strategy not started - Gemini unavailable")

        # Start portfolio monitor
        self.portfolio_monitor_task = asyncio.create_task(self.monitor_portfolio())
        
        # Wait for shutdown signal or any task to complete/fail
        try:
            # Use asyncio.wait to monitor all tasks
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # If a task completed (or failed), log it
            for task in done:
                try:
                    await task  # This will raise if task failed
                except Exception as e:
                    logger.error(f"❌ Market making task failed: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # If we're still running, wait for shutdown signal
            if self.running:
                await self.shutdown_event.wait()
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutdown signal received...")
        except Exception as e:
            logger.error(f"❌ Error in dual market making runner: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # Stop both strategies
            self.running = False
            if self.coinbase_market_making_engine:
                self.coinbase_market_making_engine.stop()
            if self.gemini_market_making_engine:
                self.gemini_market_making_engine.stop()
            
            # Cancel all tasks
            coinbase_task.cancel()
            if self.gemini_market_making_engine:
                gemini_task.cancel()
            if self.portfolio_monitor_task:
                self.portfolio_monitor_task.cancel()
            
            # Wait for cancellation
            try:
                await coinbase_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Coinbase task error during cleanup: {e}")
            
            if self.gemini_market_making_engine:
                try:
                    await gemini_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.debug(f"Gemini task error during cleanup: {e}")
            if self.portfolio_monitor_task:
                try:
                    await self.portfolio_monitor_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.debug(f"Portfolio monitor error during cleanup: {e}")
            
            logger.info("✅ Both market making strategies stopped")
    
    def stop(self):
        """Stop the bot"""
        self.shutdown_event.set()

    async def monitor_portfolio(self):
        """Periodically log comprehensive portfolio analytics."""
        while not self.exchange_manager:
            await asyncio.sleep(1)
        while True:
            try:
                snapshot = await self.exchange_manager.compute_portfolio_snapshot()
                total_value = snapshot.get('total_value_usd', 0.0)
                if self.portfolio_baseline is None:
                    self.portfolio_baseline = total_value
                    self.portfolio_peak_value = total_value
                    logger.info(
                        f"💰 Portfolio baseline established: ${total_value:,.2f}"
                    )
                delta = total_value - self.portfolio_baseline
                delta_pct = (delta / self.portfolio_baseline * 100) if self.portfolio_baseline else 0.0
                if self.portfolio_peak_value is None or total_value > self.portfolio_peak_value:
                    self.portfolio_peak_value = total_value
                drawdown = ((total_value - self.portfolio_peak_value) / self.portfolio_peak_value * 100) if self.portfolio_peak_value else 0.0
                coinbase_realized = getattr(self.coinbase_market_making_engine, 'net_profit_usd', 0.0) if self.coinbase_market_making_engine else 0.0
                gemini_realized = getattr(self.gemini_market_making_engine, 'net_profit_usd', 0.0) if self.gemini_market_making_engine else 0.0
                logger.info("📈 PORTFOLIO SNAPSHOT")
                logger.info(
                    f"   Total value: ${total_value:,.2f} | Δ vs start: ${delta:,.2f} ({delta_pct:+.2f}%)"
                )
                logger.info(
                    f"   Realized PnL -> Coinbase: ${coinbase_realized:.2f}, Gemini: ${gemini_realized:.2f}, Combined: ${coinbase_realized + gemini_realized:.2f}"
                )
                if drawdown < 0:
                    logger.info(f"   Drawdown from peak: {drawdown:.2f}%")
                for exchange_id, data in snapshot.get('exchanges', {}).items():
                    logger.info(
                        f"   {exchange_id.upper()} holdings: ${data.get('total_value_usd', 0.0):,.2f} "
                        f"(stable ${data.get('stable_value_usd', 0.0):,.2f} / crypto ${data.get('crypto_value_usd', 0.0):,.2f})"
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"   ⚠️ Portfolio monitor error: {e}")
            await asyncio.sleep(self.portfolio_monitor_interval)

async def main():
    """Main entry point"""
    bot = DualStrategyBot()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("\n🛑 Shutdown signal received...")
        bot.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.initialize()
        await bot.run()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("👋 Bot stopped")

if __name__ == '__main__':
    asyncio.run(main())

