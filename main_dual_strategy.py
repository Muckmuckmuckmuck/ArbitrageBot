#!/usr/bin/env python3
"""
Dual Strategy Trading Bot
Runs two independent strategies concurrently:

🔵 COINBASE: Intra-Exchange Arbitrage (USD/USDC/USDT pairs)
   - Strategy: Buy on one pair, sell on another (same exchange)
   - Pairs: USD/USDC/USDT quote currencies only
   - Execution: Immediate mode (trades execute as soon as found)

🟢 GEMINI: Market Making (Top 10 pairs)
   - Strategy: Passive market making with grid orders
   - Pairs: ARB/USD, OP/USD, LINK/USD, etc. (filtered by availability)
   - Execution: Continuous loop with 15s updates

Both strategies run concurrently on Railway with independent loops.
"""

import asyncio
import logging
import signal
import sys
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from intra_exchange_arbitrage_engine import IntraExchangeArbitrageEngine
from gemini_market_making_engine import GeminiMarketMakingEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DualStrategyBot:
    """Manages both strategies running concurrently"""
    
    def __init__(self):
        self.exchange_manager = None
        self.arbitrage_engine = None
        self.market_making_engine = None
        self.running = False
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Initialize both strategies"""
        logger.info("=" * 80)
        logger.info("🚀 INITIALIZING DUAL STRATEGY BOT")
        logger.info("=" * 80)
        logger.info("   Strategy 1: Coinbase Intra-Exchange Arbitrage")
        logger.info("   Strategy 2: Gemini Market Making")
        logger.info("=" * 80)
        
        # Initialize exchange manager
        self.exchange_manager = CoinbaseGeminiExchangeManager()
        await self.exchange_manager.initialize()
        
        # ====================================================================
        # 🔵 COINBASE STRATEGY: Intra-Exchange Arbitrage
        # ====================================================================
        # Initialize Coinbase arbitrage engine
        logger.info("\n📊 Initializing Coinbase Intra-Exchange Arbitrage Engine...")
        # Note: IntraExchangeArbitrageEngine creates its own exchange_manager internally
        self.arbitrage_engine = IntraExchangeArbitrageEngine(
            min_profit_threshold=0.002,  # 0.2% minimum
            max_position_size_usd=50.0    # $50 max per trade
        )
        await self.arbitrage_engine.initialize()
        
        # ====================================================================
        # 🟢 GEMINI STRATEGY: Market Making
        # ====================================================================
        # Initialize Gemini market-making engine
        logger.info("\n📊 Initializing Gemini Market-Making Engine...")
        self.market_making_engine = GeminiMarketMakingEngine(
            exchange_manager=self.exchange_manager,
            capital_per_pair=50.0,  # $50 per pair (increased from $10 to allow meaningful orders)
            grid_spacing_percent=0.20,  # 0.20% spacing
            order_size_percent=0.10,  # 10% of capital per order (increased from 1% to $5 per order)
            min_spread_percent=0.12,  # Skip if spread < 0.12%
            max_inventory_percent=0.25,  # Max 25% in one asset
            requote_interval_seconds=15,  # Update every 15s
            stop_loss_percent=0.02,  # -2% stop loss
            take_profit_interval_minutes=60,  # Flatten every hour
        )
        await self.market_making_engine.initialize()
        
        logger.info("\n✅ Both strategies initialized successfully!")
        logger.info("=" * 80)
    
    # ========================================================================
    # 🔵 COINBASE STRATEGY: Intra-Exchange Arbitrage Loop
    # ========================================================================
    async def run_arbitrage_strategy(self):
        """🔵 Run Coinbase intra-exchange arbitrage strategy"""
        logger.info("\n🚀 Starting Coinbase Intra-Exchange Arbitrage Strategy...")
        
        while self.running:
            try:
                # Scan and execute on Coinbase
                result = await self.arbitrage_engine.scan_and_execute_immediately(
                    exchange_id='coinbase',
                    max_cryptos=200
                )
                
                # Log summary
                logger.info(f"\n📊 Coinbase Arbitrage Summary:")
                logger.info(f"   Opportunities found: {result.get('opportunities_found', 0)}")
                logger.info(f"   Trades executed: {result.get('trades_executed', 0)}")
                logger.info(f"   Trades skipped: {result.get('trades_skipped', 0)}")
                
                # Wait before next scan
                await asyncio.sleep(60)  # Scan every 60 seconds
                
            except asyncio.CancelledError:
                logger.info("   🛑 Arbitrage strategy cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in arbitrage strategy: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(60)
    
    # ========================================================================
    # 🟢 GEMINI STRATEGY: Market Making Loop
    # ========================================================================
    async def run_market_making_strategy(self):
        """🟢 Run Gemini market-making strategy"""
        logger.info("\n🚀 Starting Gemini Market-Making Strategy...")
        
        try:
            await self.market_making_engine.run_market_making_loop()
        except asyncio.CancelledError:
            logger.info("   🛑 Market-making strategy cancelled")
        except Exception as e:
            logger.error(f"❌ Error in market-making strategy: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def run(self):
        """Run both strategies concurrently"""
        self.running = True
        
        # Start both strategies as concurrent tasks
        arbitrage_task = asyncio.create_task(self.run_arbitrage_strategy())
        market_making_task = asyncio.create_task(self.run_market_making_strategy())
        
        # Wait for shutdown signal or any task to complete/fail
        try:
            # Use asyncio.wait to monitor both tasks
            done, pending = await asyncio.wait(
                [arbitrage_task, market_making_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # If a task completed (or failed), log it
            for task in done:
                try:
                    await task  # This will raise if task failed
                except Exception as e:
                    logger.error(f"❌ Strategy task failed: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # If we're still running, wait for shutdown signal
            if self.running:
                await self.shutdown_event.wait()
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutdown signal received...")
        except Exception as e:
            logger.error(f"❌ Error in dual strategy runner: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # Stop both strategies
            self.running = False
            self.market_making_engine.stop()
            
            # Cancel all tasks
            arbitrage_task.cancel()
            market_making_task.cancel()
            
            # Wait for cancellation
            try:
                await arbitrage_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Arbitrage task error during cleanup: {e}")
            
            try:
                await market_making_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Market making task error during cleanup: {e}")
            
            logger.info("✅ Both strategies stopped")
    
    def stop(self):
        """Stop the bot"""
        self.shutdown_event.set()

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

