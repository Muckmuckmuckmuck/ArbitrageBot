#!/usr/bin/env python3
"""
Arbitrage Trading Bot for Binance and OKX
Supports TON, VET, ALGO, FTM, XLM cryptocurrencies
"""

import asyncio
import signal
import sys
import time
from typing import List
from config import Config, setup_logging
from exchanges import ExchangeManager
from price_monitor import PriceMonitor
from arbitrage_engine import ArbitrageEngine
from transfer_manager import TransferManager
from risk_manager import RiskManager
from monitoring import MonitoringSystem
from smart_position_sizing import SmartPositionSizer
from volume_analysis import VolumeAnalyzer
from dynamic_spreads import DynamicSpreadManager
from competition_detection import CompetitionDetector
from profit_optimization import ProfitOptimizer
from basic_ml_models import BasicMLModels
from enhanced_reporting import EnhancedReporter
from websocket_manager import WebSocketManager
from slippage_protection import SlippageProtection
from advanced_risk_manager import AdvancedRiskManager
from performance_optimizer import PerformanceOptimizer
from database_manager import DatabaseManager
from dynamic_spread_optimizer import DynamicSpreadOptimizer
from smart_position_optimizer import SmartPositionOptimizer
from transfer_timing_optimizer import TransferTimingOptimizer
from market_timing_optimizer import MarketTimingOptimizer
from smart_order_router import SmartOrderRouter
from competition_detector import CompetitionDetector
from multi_timeframe_analyzer import MultiTimeframeAnalyzer
from triangular_arbitrage_engine import TriangularArbitrageEngine
import logging

logger = logging.getLogger(__name__)

class ArbitrageBot:
    """Main arbitrage trading bot class"""
    
    def __init__(self):
        self.config = Config
        self.logger = setup_logging()
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Initialize components
        self.exchange_manager = ExchangeManager()
        self.price_monitor = PriceMonitor(self.exchange_manager)
        self.arbitrage_engine = ArbitrageEngine(self.exchange_manager, self.price_monitor)
        self.transfer_manager = TransferManager(self.exchange_manager)
        self.risk_manager = RiskManager(self.exchange_manager)
        
        # Initialize enhanced features
        self.smart_position_sizer = SmartPositionSizer()
        self.volume_analyzer = VolumeAnalyzer()
        self.dynamic_spread_manager = DynamicSpreadManager()
        self.competition_detector = CompetitionDetector()
        self.profit_optimizer = ProfitOptimizer()
        self.basic_ml_models = BasicMLModels()
        self.enhanced_reporter = EnhancedReporter()
        
        # Initialize advanced features
        self.websocket_manager = WebSocketManager()
        self.slippage_protection = SlippageProtection(self.exchange_manager)
        self.advanced_risk_manager = AdvancedRiskManager(self.exchange_manager)
        self.performance_optimizer = PerformanceOptimizer()
        self.database_manager = DatabaseManager()
        
        # Initialize optimization features
        self.dynamic_spread_optimizer = DynamicSpreadOptimizer(self.exchange_manager)
        self.smart_position_optimizer = SmartPositionOptimizer(self.exchange_manager)
        self.transfer_timing_optimizer = TransferTimingOptimizer(self.exchange_manager)
        self.market_timing_optimizer = MarketTimingOptimizer()
        self.smart_order_router = SmartOrderRouter(self.exchange_manager)
        self.competition_detector = CompetitionDetector(self.exchange_manager)
        self.multi_timeframe_analyzer = MultiTimeframeAnalyzer(self.exchange_manager)
        self.triangular_arbitrage_engine = TriangularArbitrageEngine(self.exchange_manager)
        
        # Initialize dynamic balance management
        from dynamic_balance_manager import DynamicBalanceManager
        from adaptive_profit_calculator import AdaptiveProfitCalculator
        from percentage_balance_manager import PercentageBalanceManager
        self.balance_manager = DynamicBalanceManager(self.exchange_manager)
        self.percentage_balance_manager = PercentageBalanceManager(self.exchange_manager)
        self.adaptive_profit_calculator = AdaptiveProfitCalculator(self.exchange_manager)
        
        # Connect balance managers to arbitrage engine
        self.arbitrage_engine.balance_manager = self.balance_manager
        self.arbitrage_engine.percentage_balance_manager = self.percentage_balance_manager
        
        self.monitoring_system = MonitoringSystem(
            self.exchange_manager, self.arbitrage_engine, 
            self.transfer_manager, self.risk_manager
        )
    
    async def initialize(self):
        """Initialize all components"""
        try:
            self.logger.info("Initializing Arbitrage Trading Bot...")
            
            # Initialize exchanges
            self.logger.info("Connecting to exchanges...")
            await self.exchange_manager.initialize_all()
            
            # Initialize transfer manager
            self.logger.info("Initializing transfer manager...")
            await self.transfer_manager.initialize()
            
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            self.logger.info("Bot initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {str(e)}")
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
            self.logger.info("Starting Arbitrage Trading Bot...")
            
            # Start monitoring system
            self.logger.info("Starting monitoring system...")
            monitoring_task = asyncio.create_task(self.monitoring_system.start_monitoring())
            
            # Start transfer monitoring
            self.logger.info("Starting transfer monitoring...")
            transfer_monitoring_task = asyncio.create_task(self.transfer_manager.monitor_pending_transfers())
            
            # Start WebSocket manager
            self.logger.info("Starting WebSocket manager...")
            symbols = [pair.split('/')[0] for pair in self.config.CURRENCY_PAIRS]
            self.websocket_manager.subscribe(self._on_price_update)
            websocket_task = asyncio.create_task(self.websocket_manager.start(symbols))
            
            # Start arbitrage engine
            self.logger.info("Starting arbitrage engine...")
            arbitrage_task = asyncio.create_task(self.arbitrage_engine.start(self.config.CURRENCY_PAIRS))
            
            # Initialize performance monitoring
            self.logger.info("Initializing performance monitoring...")
            performance_task = asyncio.create_task(self.performance_optimizer.run_performance_benchmark(
                self.exchange_manager, self.websocket_manager
            ))
            
            # Start optimization tasks
            self.logger.info("Starting optimization tasks...")
            optimization_task = asyncio.create_task(self._run_optimization_tasks())
            
            # Start triangular arbitrage scanning
            self.logger.info("Starting triangular arbitrage scanning...")
            triangular_task = asyncio.create_task(self._scan_triangular_arbitrage())
            
            # Start balance optimization
            self.logger.info("Starting balance optimization...")
            balance_task = asyncio.create_task(self._balance_optimization_loop())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel tasks
            monitoring_task.cancel()
            transfer_monitoring_task.cancel()
            websocket_task.cancel()
            arbitrage_task.cancel()
            performance_task.cancel()
            optimization_task.cancel()
            triangular_task.cancel()
            balance_task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(
                monitoring_task, transfer_monitoring_task, websocket_task, 
                arbitrage_task, performance_task, optimization_task, triangular_task, balance_task,
                return_exceptions=True
            )
            
            self.logger.info("Bot stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {str(e)}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown of the bot"""
        try:
            self.logger.info("Initiating graceful shutdown...")
            self.running = False
            
            # Stop arbitrage engine
            await self.arbitrage_engine.stop()
            
            # Generate enhanced final report
            self.enhanced_reporter.log_daily_summary()
            
            # Get final statistics
            trade_stats = self.arbitrage_engine.get_trade_statistics()
            transfer_stats = self.transfer_manager.get_transfer_statistics()
            risk_summary = self.risk_manager.get_risk_summary()
            
            # Stop WebSocket manager
            await self.websocket_manager.stop()
            
            # Get enhanced statistics
            performance_summary = self.smart_position_sizer.get_performance_summary()
            volume_summary = self.volume_analyzer.get_volume_summary()
            spread_summary = self.dynamic_spread_manager.get_spread_summary()
            competition_summary = self.competition_detector.get_competition_summary()
            ml_summary = self.basic_ml_models.get_ml_summary()
            
            # Get advanced statistics
            slippage_summary = self.slippage_protection.get_slippage_summary('XRP/USDT')
            risk_summary_advanced = self.advanced_risk_manager.get_risk_summary()
            performance_optimizer_summary = self.performance_optimizer.get_performance_summary()
            database_stats = self.database_manager.get_database_stats()
            
            self.logger.info("FINAL STATISTICS:")
            self.logger.info(f"Total trades: {trade_stats['total_trades']}")
            self.logger.info(f"Successful trades: {trade_stats['successful_trades']}")
            self.logger.info(f"Total profit: ${trade_stats['total_profit']:.2f}")
            self.logger.info(f"Total transfers: {transfer_stats['total_transfers']}")
            self.logger.info(f"Daily P&L: ${risk_summary.get('risk_metrics', {}).get('daily_pnl', 0):.2f}")
            self.logger.info(f"Average position size: ${sum(p.get('avg_trade_size', 0) for p in performance_summary.values()):.2f}")
            self.logger.info(f"Competition level: {sum(c.get('competition_level', 0.5) for c in competition_summary.values()) / len(competition_summary):.2f}")
            self.logger.info(f"ML model accuracy: {sum(m.get('performance', {}).get('accuracy', 0) for m in ml_summary.values()) / len(ml_summary):.2f}")
            
        # Log advanced statistics
        self.logger.info("ADVANCED STATISTICS:")
        self.logger.info(f"Average slippage: {slippage_summary.get('avg_slippage', 0):.4f}%")
        self.logger.info(f"Portfolio risk score: {risk_summary_advanced.get('risk_score', 0):.3f}")
        self.logger.info(f"Database size: {database_stats.get('database_size_mb', 0):.2f} MB")
        self.logger.info(f"Total records: {database_stats.get('trades_count', 0)}")
        
        # Log optimization statistics
        self.logger.info("OPTIMIZATION STATISTICS:")
        
        # Dynamic spread optimization
        spread_optimization_summary = self.dynamic_spread_optimizer.get_market_conditions_summary('XRP/USDT', 24)
        if spread_optimization_summary:
            self.logger.info(f"Dynamic spread optimization - Avg spread: {spread_optimization_summary.get('avg_spread', 0):.4f}%")
        
        # Smart position sizing
        position_sizing_summary = self.smart_position_optimizer.get_performance_summary('XRP/USDT', 30)
        if position_sizing_summary:
            self.logger.info(f"Smart position sizing - Success rate: {position_sizing_summary.get('success_rate', 0):.2f}%")
        
        # Market timing
        market_timing_recommendations = self.market_timing_optimizer.get_current_trading_recommendations()
        if market_timing_recommendations:
            current_conditions = market_timing_recommendations.get('current_conditions', {})
            self.logger.info(f"Market timing - Current sentiment: {current_conditions.get('recommended_action', 'unknown')}")
        
        # Competition detection
        competition_summary = self.competition_detector.get_competition_summary('XRP/USDT', 7)
        if competition_summary:
            self.logger.info(f"Competition detection - Avg competition level: {competition_summary.get('avg_competition_level', 0):.3f}")
        
        # Multi-timeframe analysis
        multi_timeframe_summary = self.multi_timeframe_analyzer.get_analysis_summary('XRP/USDT', 7)
        if multi_timeframe_summary:
            self.logger.info(f"Multi-timeframe analysis - Avg confidence: {multi_timeframe_summary.get('avg_confidence', 0):.3f}")
        
        # Triangular arbitrage
        triangular_summary = self.triangular_arbitrage_engine.get_arbitrage_summary(7)
        if triangular_summary:
            performance_metrics = triangular_summary.get('performance_metrics', {})
            self.logger.info(f"Triangular arbitrage - Success rate: {performance_metrics.get('overall_success_rate', 0):.2f}%")
        
        # Balance and adaptive profit analysis
        try:
            balance_summary = self.balance_manager.get_balance_summary()
            adaptive_summary = await self.adaptive_profit_calculator.get_adaptive_profit_summary()
            
            if balance_summary:
                self.logger.info("BALANCE MANAGEMENT:")
                self.logger.info(f"Total USD value: ${balance_summary.get('total_usd_value', 0):.2f}")
                self.logger.info(f"Available USD: ${balance_summary.get('available_usd', 0):.2f}")
                self.logger.info(f"Optimization score: {balance_summary.get('optimization_score', 0):.3f}")
            
            if adaptive_summary:
                self.logger.info("ADAPTIVE PROFIT ANALYSIS:")
                self.logger.info(f"Current balance: ${adaptive_summary.get('current_balance_usd', 0):.2f}")
                self.logger.info(f"Daily net profit: ${adaptive_summary.get('total_daily_net_profit', 0):.2f}")
                self.logger.info(f"Monthly growth rate: {adaptive_summary.get('monthly_growth_rate', 0):.1f}%")
                self.logger.info(f"Average scalability score: {adaptive_summary.get('avg_scalability_score', 0):.2f}")
        except Exception as e:
            self.logger.error(f"Error getting balance/adaptive analysis: {str(e)}")
        
        # Log performance optimization results
        for operation, stats in performance_optimizer_summary.items():
            self.logger.info(f"{operation} avg latency: {stats.get('avg_latency_ms', 0):.1f}ms")
            
            # Set shutdown event
            self.shutdown_event.set()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
            self.shutdown_event.set()
    
    async def _on_price_update(self, message):
        """Handle WebSocket price updates"""
        try:
            # Update slippage protection with new price data
            await self.slippage_protection.analyze_market_depth(
                message.symbol, [message.exchange]
            )
            
            # Update ML models with new data
            market_data = {
                'price': message.price,
                'volume': message.volume,
                'timestamp': message.timestamp
            }
            self.basic_ml_models.collect_training_data(message.symbol, market_data, 0.0)
            
            # Update optimization systems
            await self.dynamic_spread_optimizer.analyze_market_conditions(message.symbol)
            
        except Exception as e:
            self.logger.error(f"Error handling price update: {str(e)}")
    
    async def _run_optimization_tasks(self):
        """Run optimization tasks"""
        try:
            while not self.shutdown_event.is_set():
                try:
                    # Optimize spread thresholds
                    await self.dynamic_spread_optimizer.optimize_all_symbols(self.config.CURRENCY_PAIRS)
                    
                    # Analyze market timing
                    market_conditions = await self.market_timing_optimizer.analyze_current_market_conditions()
                    
                    # Analyze competition
                    for symbol in self.config.CURRENCY_PAIRS:
                        await self.competition_detector.analyze_competition(symbol)
                    
                    # Multi-timeframe analysis
                    for symbol in self.config.CURRENCY_PAIRS:
                        await self.multi_timeframe_analyzer.analyze_multi_timeframe(symbol)
                    
                    # Wait before next optimization cycle
                    await asyncio.sleep(300)  # 5 minutes
                    
                except Exception as e:
                    self.logger.error(f"Error in optimization tasks: {str(e)}")
                    await asyncio.sleep(60)  # Wait 1 minute before retry
                    
        except asyncio.CancelledError:
            self.logger.info("Optimization tasks cancelled")
        except Exception as e:
            self.logger.error(f"Error in optimization task loop: {str(e)}")
    
    async def _scan_triangular_arbitrage(self):
        """Scan for triangular arbitrage opportunities"""
        try:
            while not self.shutdown_event.is_set():
                try:
                    # Scan triangular arbitrage opportunities
                    triangular_opportunities = await self.triangular_arbitrage_engine.scan_triangular_opportunities()
                    
                    # Scan cross-asset arbitrage opportunities
                    cross_asset_opportunities = await self.triangular_arbitrage_engine.scan_cross_asset_opportunities()
                    
                    # Log findings
                    if triangular_opportunities:
                        self.logger.info(f"Found {len(triangular_opportunities)} triangular arbitrage opportunities")
                        for opp in triangular_opportunities[:3]:  # Log top 3
                            self.logger.info(f"Triangular: {opp.symbol1}->{opp.symbol2}->{opp.symbol3}, "
                                           f"Profit: {opp.profit_percent:.3f}%")
                    
                    if cross_asset_opportunities:
                        self.logger.info(f"Found {len(cross_asset_opportunities)} cross-asset arbitrage opportunities")
                        for opp in cross_asset_opportunities[:3]:  # Log top 3
                            self.logger.info(f"Cross-asset: {opp.base_asset}->{opp.intermediate_asset}->{opp.quote_asset}, "
                                           f"Profit: {opp.profit_percent:.3f}%")
                    
                    # Wait before next scan
                    await asyncio.sleep(600)  # 10 minutes
                    
                except Exception as e:
                    self.logger.error(f"Error in triangular arbitrage scan: {str(e)}")
                    await asyncio.sleep(60)  # Wait 1 minute before retry
                    
        except asyncio.CancelledError:
            self.logger.info("Triangular arbitrage scanning cancelled")
        except Exception as e:
            self.logger.error(f"Error in triangular arbitrage scan loop: {str(e)}")
    
    async def _balance_optimization_loop(self):
        """Balance optimization loop"""
        try:
            while not self.shutdown_event.is_set():
                try:
                    # Update account balances
                    await self.balance_manager.update_account_balances()
                    
                    # Optimize balance allocation
                    balance_optimization = await self.balance_manager.optimize_balance_allocation()
                    
                    # Calculate adaptive profits
                    adaptive_analysis = await self.adaptive_profit_calculator.calculate_adaptive_profits()
                    
                    # Log balance status
                    if balance_optimization.total_usd_value > 0:
                        self.logger.info(f"Balance optimization: Total=${balance_optimization.total_usd_value:.2f}, "
                                       f"Available=${balance_optimization.available_usd:.2f}, "
                                       f"Score={balance_optimization.optimization_score:.3f}")
                        
                        # Log recommendations
                        if balance_optimization.recommendations:
                            for rec in balance_optimization.recommendations[:3]:  # Top 3 recommendations
                                self.logger.info(f"Balance recommendation: {rec}")
                    
                    # Wait before next optimization cycle
                    await asyncio.sleep(600)  # 10 minutes
                    
                except Exception as e:
                    self.logger.error(f"Error in balance optimization: {str(e)}")
                    await asyncio.sleep(60)  # Wait 1 minute before retry
                    
        except asyncio.CancelledError:
            self.logger.info("Balance optimization cancelled")
        except Exception as e:
            self.logger.error(f"Error in balance optimization loop: {str(e)}")
    
    async def run_health_check(self):
        """Run health check on all components"""
        try:
            self.logger.info("Running health check...")
            
            # Check exchange connections
            for exchange_name in ['binance', 'okx']:
                exchange = self.exchange_manager.get_exchange(exchange_name)
                try:
                    await exchange.test_connection()
                    self.logger.info(f"{exchange_name} connection: OK")
                except Exception as e:
                    self.logger.error(f"{exchange_name} connection: FAILED - {str(e)}")
                    return False
            
            # Check price monitoring
            if self.price_monitor.running:
                self.logger.info("Price monitoring: OK")
            else:
                self.logger.warning("Price monitoring: NOT RUNNING")
            
            # Check arbitrage engine
            if self.arbitrage_engine.running:
                self.logger.info("Arbitrage engine: OK")
            else:
                self.logger.warning("Arbitrage engine: NOT RUNNING")
            
            # Check risk manager
            if not self.risk_manager.emergency_stop:
                self.logger.info("Risk manager: OK")
            else:
                self.logger.warning("Risk manager: EMERGENCY STOP ACTIVE")
            
            self.logger.info("Health check completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def run_performance_test(self):
        """Run performance test"""
        try:
            self.logger.info("Running performance test...")
            
            start_time = time.time()
            
            # Test price fetching
            for symbol in self.config.CURRENCY_PAIRS[:2]:  # Test first 2 symbols
                prices = await self.exchange_manager.get_prices(symbol)
                self.logger.info(f"Price fetch for {symbol}: {prices}")
            
            # Test balance fetching
            for exchange_name in ['binance', 'okx']:
                exchange = self.exchange_manager.get_exchange(exchange_name)
                balance = await exchange.get_balance()
                self.logger.info(f"Balance fetch for {exchange_name}: OK")
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.logger.info(f"Performance test completed in {duration:.2f} seconds")
            return True
            
        except Exception as e:
            self.logger.error(f"Performance test failed: {str(e)}")
            return False

async def main():
    """Main entry point"""
    try:
        # Create bot instance
        bot = ArbitrageBot()
        
        # Initialize bot
        await bot.initialize()
        
        # Run health check
        health_ok = await bot.run_health_check()
        if not health_ok:
            logger.error("Health check failed, exiting...")
            sys.exit(1)
        
        # Run performance test
        perf_ok = await bot.run_performance_test()
        if not perf_ok:
            logger.warning("Performance test failed, but continuing...")
        
        # Start bot
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {str(e)}")
        sys.exit(1)

def run_flask_app():
    """Run Flask app for Railway deployment"""
    try:
        bot = ArbitrageBot()
        bot.monitoring_system.run_flask_app()
    except Exception as e:
        logger.error(f"Failed to start Flask app: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if running in Railway environment
    if Config.RAILWAY_ENVIRONMENT == "production":
        logger.info("Running in Railway production environment")
        run_flask_app()
    else:
        logger.info("Running in development environment")
        asyncio.run(main())
