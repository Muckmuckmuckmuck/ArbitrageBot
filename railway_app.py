#!/usr/bin/env python3
"""
Railway deployment entry point for the arbitrage trading bot
"""

import asyncio
import logging
import signal
import sys
from main import ArbitrageBot
from railway_config import RailwayConfig
import json

# Configure logging for Railway
logging.basicConfig(
    level=getattr(logging, RailwayConfig.LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

class RailwayArbitrageBot:
    """Railway-optimized arbitrage bot"""
    
    def __init__(self):
        self.bot = None
        self.shutdown_event = asyncio.Event()
        self.health_check_task = None
        
    async def start(self):
        """Start the bot with Railway-specific configuration"""
        try:
            logger.info("Starting Arbitrage Bot on Railway...")
            logger.info(f"Environment: {RailwayConfig.RAILWAY_ENVIRONMENT}")
            logger.info(f"Project ID: {RailwayConfig.RAILWAY_PROJECT_ID}")
            
            # Initialize bot
            self.bot = ArbitrageBot()
            
            # Start health check monitoring
            self.health_check_task = asyncio.create_task(self._health_check_monitor())
            
            # Start the main bot
            await self.bot.start()
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the bot gracefully"""
        try:
            logger.info("Stopping Arbitrage Bot...")
            
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            if self.bot:
                await self.bot.shutdown()
            
            self.shutdown_event.set()
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
    
    async def _health_check_monitor(self):
        """Monitor bot health and log status"""
        try:
            while not self.shutdown_event.is_set():
                try:
                    if self.bot:
                        # Run health check
                        await self.bot.run_health_check()
                        
                        # Log resource usage
                        self._log_resource_usage()
                        
                        # Check emergency stop conditions
                        if hasattr(self.bot, 'error_handler'):
                            if self.bot.error_handler.check_emergency_stop_conditions():
                                logger.critical("Emergency stop conditions detected!")
                                await self.stop()
                                return
                    
                    # Wait for next health check
                    await asyncio.sleep(RailwayConfig.HEALTH_CHECK_INTERVAL)
                    
                except Exception as e:
                    logger.error(f"Error in health check: {str(e)}")
                    await asyncio.sleep(60)  # Wait 1 minute before retry
                    
        except asyncio.CancelledError:
            logger.info("Health check monitor cancelled")
        except Exception as e:
            logger.error(f"Error in health check monitor: {str(e)}")
    
    def _log_resource_usage(self):
        """Log resource usage for Railway monitoring"""
        try:
            import psutil
            
            # Get system resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Log resource usage
            logger.info(f"Resource usage - CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%, Disk: {disk.percent:.1f}%")
            
            # Check resource limits
            if cpu_percent > RailwayConfig.MAX_CPU_PERCENT:
                logger.warning(f"CPU usage ({cpu_percent:.1f}%) exceeds limit ({RailwayConfig.MAX_CPU_PERCENT}%)")
            
            memory_mb = memory.used / (1024 * 1024)
            if memory_mb > RailwayConfig.MAX_MEMORY_MB:
                logger.warning(f"Memory usage ({memory_mb:.1f}MB) exceeds limit ({RailwayConfig.MAX_MEMORY_MB}MB)")
            
            # Log bot-specific metrics
            if self.bot:
                try:
                    # Get trade statistics
                    trade_stats = self.bot.arbitrage_engine.get_trade_statistics()
                    logger.info(f"Bot metrics - Trades: {trade_stats['total_trades']}, Profit: ${trade_stats['total_profit']:.2f}")
                    
                    # Get performance metrics
                    if hasattr(self.bot, 'performance_optimizer'):
                        perf_summary = self.bot.performance_optimizer.get_performance_summary()
                        for operation, stats in perf_summary.items():
                            logger.info(f"Performance - {operation}: {stats.get('avg_latency_ms', 0):.1f}ms avg")
                    
                except Exception as e:
                    logger.debug(f"Could not get bot metrics: {str(e)}")
                    
        except ImportError:
            logger.debug("psutil not available for resource monitoring")
        except Exception as e:
            logger.error(f"Error logging resource usage: {str(e)}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    if 'bot_instance' in globals():
        asyncio.create_task(bot_instance.stop())

async def main():
    """Main entry point for Railway deployment"""
    global bot_instance
    
    try:
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create and start bot
        bot_instance = RailwayArbitrageBot()
        
        # Start the bot
        await bot_instance.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        if 'bot_instance' in globals():
            await bot_instance.stop()

if __name__ == "__main__":
    # Check if running on Railway
    if RailwayConfig.RAILWAY_ENVIRONMENT:
        logger.info("Running on Railway platform")
        
        # Log configuration
        logger.info("Configuration:")
        logger.info(f"  Environment: {RailwayConfig.RAILWAY_ENVIRONMENT}")
        logger.info(f"  Database: {RailwayConfig.get_database_config()['type']}")
        logger.info(f"  WebSocket: {RailwayConfig.WEBSOCKET_ENABLED}")
        logger.info(f"  ML Models: {RailwayConfig.ML_MODELS_ENABLED}")
        logger.info(f"  Performance Monitoring: {RailwayConfig.PERFORMANCE_MONITORING}")
        
        # Run the bot
        asyncio.run(main())
    else:
        logger.error("Railway environment not detected")
        sys.exit(1)

