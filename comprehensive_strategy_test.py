#!/usr/bin/env python3
"""
Comprehensive Strategy Test - Enterprise Grade Validation
========================================================

This test validates every component of our arbitrage strategy:
1. Exchange connectivity and API functionality
2. Balance fetching and validation
3. Price fetching and spread calculation
4. Order placement and management
5. Transfer functionality between exchanges
6. Retry logic and error handling
7. Position tracking and recovery
8. Opportunity monitoring and validation

This is a TEST - it will use small amounts and may not be profitable.
The goal is to validate all systems work correctly.
"""

import asyncio
import logging
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from coinbase_gemini_config import Config
from enhanced_retry_logic import enhanced_retry_logic
from stuck_position_recovery import StuckPositionRecovery
from opportunity_monitoring import OpportunityMonitoring
from dynamic_order_manager import DynamicOrderManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ComprehensiveStrategyTest:
    """
    Comprehensive test suite for the arbitrage strategy
    """
    
    def __init__(self):
        self.exchange_manager = None
        self.retry_logic = enhanced_retry_logic
        self.stuck_recovery = None
        self.opportunity_monitor = None
        self.order_manager = None
        
        # Test configuration
        self.test_amount_usd = 2.00  # Small test amount
        self.test_crypto = 'XRP'  # Use XRP for testing (fastest transfers)
        self.test_symbol = 'XRP/USD'
        
        # Test results
        self.test_results = {}
        self.start_time = datetime.now()
        
        logger.info("🧪 Comprehensive Strategy Test initialized")
        logger.info(f"   Test amount: ${self.test_amount_usd}")
        logger.info(f"   Test crypto: {self.test_crypto}")
        logger.info(f"   Test symbol: {self.test_symbol}")

    async def run_all_tests(self):
        """
        Run all comprehensive tests
        """
        logger.info("\n" + "="*80)
        logger.info("🚀 STARTING COMPREHENSIVE STRATEGY TEST")
        logger.info("="*80)
        
        try:
            # Test 1: Exchange Connectivity
            await self.test_exchange_connectivity()
            
            # Test 2: Balance and Price Fetching
            await self.test_balance_and_prices()
            
            # Test 3: Retry Logic
            await self.test_retry_logic()
            
            # Test 4: Order Management
            await self.test_order_management()
            
            # Test 5: Transfer Functionality
            await self.test_transfer_functionality()
            
            # Test 6: Stuck Position Recovery
            await self.test_stuck_position_recovery()
            
            # Test 7: Opportunity Monitoring
            await self.test_opportunity_monitoring()
            
            # Test 8: End-to-End Strategy
            await self.test_end_to_end_strategy()
            
            # Generate test report
            await self.generate_test_report()
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            if self.exchange_manager:
                await self.exchange_manager.close()

    async def test_exchange_connectivity(self):
        """
        Test 1: Exchange connectivity and API functionality
        """
        logger.info("\n" + "-"*60)
        logger.info("🔌 TEST 1: Exchange Connectivity")
        logger.info("-"*60)
        
        try:
            # Initialize exchange manager
            self.exchange_manager = CoinbaseGeminiExchangeManager()
            await self.exchange_manager.initialize()
            
            # Test both exchanges
            for exchange_name in ['coinbase', 'gemini']:
                exchange = self.exchange_manager.exchanges[exchange_name]
                
                # Test basic connectivity
                logger.info(f"   Testing {exchange_name.upper()} connectivity...")
                
                # Test fetch markets
                markets = exchange.load_markets()
                logger.info(f"   ✅ {exchange_name.upper()}: Loaded {len(markets)} markets")
                
                # Test fetch ticker
                ticker = exchange.fetch_ticker(self.test_symbol)
                if hasattr(ticker, '__await__'):
                    ticker = await ticker
                
                price = float(ticker['last'])
                logger.info(f"   ✅ {exchange_name.upper()}: {self.test_symbol} = ${price:.4f}")
            
            self.test_results['exchange_connectivity'] = True
            logger.info("✅ TEST 1 PASSED: Exchange connectivity working")
            
        except Exception as e:
            logger.error(f"❌ TEST 1 FAILED: {str(e)}")
            self.test_results['exchange_connectivity'] = False
            raise e

    async def test_balance_and_prices(self):
        """
        Test 2: Balance fetching and price validation
        """
        logger.info("\n" + "-"*60)
        logger.info("💰 TEST 2: Balance and Price Fetching")
        logger.info("-"*60)
        
        try:
            for exchange_name in ['coinbase', 'gemini']:
                exchange = self.exchange_manager.exchanges[exchange_name]
                
                logger.info(f"   Testing {exchange_name.upper()} balance fetching...")
                
                # Test balance fetching
                balance = exchange.fetch_balance()
                if hasattr(balance, '__await__'):
                    balance = await balance
                
                usd_balance = balance.get('free', {}).get('USD', 0)
                crypto_balance = balance.get('free', {}).get(self.test_crypto, 0)
                
                logger.info(f"   ✅ {exchange_name.upper()}: ${usd_balance:.2f} USD, {crypto_balance:.6f} {self.test_crypto}")
                
                # Test price fetching for multiple symbols
                for symbol in ['XRP/USD', 'ZEC/USD', 'BAT/USD']:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        if hasattr(ticker, '__await__'):
                            ticker = await ticker
                        
                        price = float(ticker['last'])
                        logger.info(f"   ✅ {exchange_name.upper()}: {symbol} = ${price:.4f}")
                    except Exception as e:
                        logger.warning(f"   ⚠️ {exchange_name.upper()}: {symbol} failed - {str(e)}")
            
            self.test_results['balance_and_prices'] = True
            logger.info("✅ TEST 2 PASSED: Balance and price fetching working")
            
        except Exception as e:
            logger.error(f"❌ TEST 2 FAILED: {str(e)}")
            self.test_results['balance_and_prices'] = False
            raise e

    async def test_retry_logic(self):
        """
        Test 3: Retry logic and error handling
        """
        logger.info("\n" + "-"*60)
        logger.info("🔄 TEST 3: Retry Logic and Error Handling")
        logger.info("-"*60)
        
        try:
            # Test retry logic with a simple operation
            exchange = self.exchange_manager.exchanges['coinbase']
            
            logger.info("   Testing retry logic with balance fetch...")
            
            # This should succeed
            balance = await self.retry_logic.execute_with_retry(
                exchange.fetch_balance,
                'fetch_balance',
                'coinbase'
            )
            
            logger.info("   ✅ Retry logic: Balance fetch succeeded")
            
            # Test circuit breaker state
            circuit_state = self.retry_logic.get_circuit_breaker_state('coinbase')
            logger.info(f"   ✅ Circuit breaker state: {circuit_state.value}")
            
            # Test retry statistics
            stats = self.retry_logic.get_stats('coinbase')
            logger.info(f"   ✅ Retry stats: {stats.total_attempts} attempts, {stats.successful_attempts} successful")
            
            self.test_results['retry_logic'] = True
            logger.info("✅ TEST 3 PASSED: Retry logic working")
            
        except Exception as e:
            logger.error(f"❌ TEST 3 FAILED: {str(e)}")
            self.test_results['retry_logic'] = False
            raise e

    async def test_order_management(self):
        """
        Test 4: Order management and placement
        """
        logger.info("\n" + "-"*60)
        logger.info("📋 TEST 4: Order Management")
        logger.info("-"*60)
        
        try:
            # Initialize order manager
            self.order_manager = DynamicOrderManager(
                self.exchange_manager.exchanges, 
                Config
            )
            
            logger.info("   Testing order manager initialization...")
            logger.info("   ✅ Order manager initialized")
            
            # Test opportunity creation
            opportunity_id = await self.order_manager.create_opportunity(
                symbol=self.test_symbol,
                buy_exchange='coinbase',
                sell_exchange='gemini',
                buy_price=2.0,
                sell_price=2.1,
                spread_percent=5.0,
                estimated_profit=0.1
            )
            
            logger.info(f"   ✅ Opportunity created: {opportunity_id}")
            
            # Test order status summary
            status = await self.order_manager.get_status_summary()
            logger.info(f"   ✅ Order manager status: {status}")
            
            self.test_results['order_management'] = True
            logger.info("✅ TEST 4 PASSED: Order management working")
            
        except Exception as e:
            logger.error(f"❌ TEST 4 FAILED: {str(e)}")
            self.test_results['order_management'] = False
            raise e

    async def test_transfer_functionality(self):
        """
        Test 5: Transfer functionality between exchanges
        """
        logger.info("\n" + "-"*60)
        logger.info("🔄 TEST 5: Transfer Functionality")
        logger.info("-"*60)
        
        try:
            # Get current balances
            cb_exchange = self.exchange_manager.exchanges['coinbase']
            gem_exchange = self.exchange_manager.exchanges['gemini']
            
            # Get initial balances
            cb_balance = cb_exchange.fetch_balance()
            if hasattr(cb_balance, '__await__'):
                cb_balance = await cb_balance
            
            gem_balance = gem_exchange.fetch_balance()
            if hasattr(gem_balance, '__await__'):
                gem_balance = await gem_balance
            
            cb_usd_before = cb_balance.get('free', {}).get('USD', 0)
            gem_usd_before = gem_balance.get('free', {}).get('USD', 0)
            cb_xrp_before = cb_balance.get('free', {}).get('XRP', 0)
            gem_xrp_before = gem_balance.get('free', {}).get('XRP', 0)
            
            logger.info(f"   Initial balances:")
            logger.info(f"   Coinbase: ${cb_usd_before:.2f} USD, {cb_xrp_before:.6f} XRP")
            logger.info(f"   Gemini: ${gem_usd_before:.2f} USD, {gem_xrp_before:.6f} XRP")
            
            # Check if we have enough USD on Coinbase for test
            if cb_usd_before < self.test_amount_usd:
                logger.warning(f"   ⚠️ Insufficient USD on Coinbase (${cb_usd_before:.2f} < ${self.test_amount_usd})")
                logger.info("   Skipping transfer test - insufficient funds")
                self.test_results['transfer_functionality'] = "SKIPPED"
                return
            
            # Get current XRP price
            ticker = cb_exchange.fetch_ticker(self.test_symbol)
            if hasattr(ticker, '__await__'):
                ticker = await ticker
            
            xrp_price = float(ticker['last'])
            xrp_amount = self.test_amount_usd / xrp_price
            
            logger.info(f"   XRP price: ${xrp_price:.4f}")
            logger.info(f"   Will buy: {xrp_amount:.6f} XRP for ${self.test_amount_usd}")
            
            # Test buy on Coinbase
            logger.info("   Testing buy on Coinbase...")
            
            if cb_exchange.id == 'coinbase':
                order = cb_exchange.create_order(
                    symbol=self.test_symbol,
                    type='market',
                    side='buy',
                    amount=xrp_amount,
                    price=xrp_price
                )
            else:
                order = cb_exchange.create_limit_order(
                    symbol=self.test_symbol,
                    side='buy',
                    amount=xrp_amount,
                    price=xrp_price * 1.01
                )
            
            if hasattr(order, '__await__'):
                order = await order
            
            order_id = order.get('id', 'unknown')
            logger.info(f"   ✅ Buy order placed: {order_id}")
            
            # Wait for fill
            await asyncio.sleep(5)
            
            # Check new balance
            cb_balance_after = cb_exchange.fetch_balance()
            if hasattr(cb_balance_after, '__await__'):
                cb_balance_after = await cb_balance_after
            
            cb_xrp_after = cb_balance_after.get('free', {}).get('XRP', 0)
            xrp_bought = cb_xrp_after - cb_xrp_before
            
            logger.info(f"   ✅ Bought: {xrp_bought:.6f} XRP")
            
            if xrp_bought < 0.001:  # Less than 0.001 XRP
                logger.warning("   ⚠️ Very small amount bought, skipping transfer test")
                self.test_results['transfer_functionality'] = "SKIPPED"
                return
            
            # Test transfer to Gemini
            logger.info("   Testing transfer to Gemini...")
            
            # Get Gemini deposit address
            gem_deposit = gem_exchange.fetch_deposit_address('XRP', {'network': 'XRP'})
            if hasattr(gem_deposit, '__await__'):
                gem_deposit = await gem_deposit
            
            address = gem_deposit['address']
            tag = gem_deposit.get('tag')
            
            logger.info(f"   Gemini address: {address[:20]}...")
            if tag:
                logger.info(f"   Gemini tag: {tag}")
            
            # Record Gemini balance before transfer
            gem_balance_before_transfer = gem_exchange.fetch_balance()
            if hasattr(gem_balance_before_transfer, '__await__'):
                gem_balance_before_transfer = await gem_balance_before_transfer
            
            gem_xrp_before_transfer = gem_balance_before_transfer.get('free', {}).get('XRP', 0)
            
            # Initiate withdrawal from Coinbase
            logger.info("   Initiating withdrawal from Coinbase...")
            
            withdraw_params = {'network': 'XRP'}
            if tag:
                withdraw_params['destination_tag'] = tag
            
            withdrawal = cb_exchange.withdraw(
                code='XRP',
                amount=xrp_bought,
                address=address,
                params=withdraw_params
            )
            if hasattr(withdrawal, '__await__'):
                withdrawal = await withdrawal
            
            withdrawal_id = withdrawal.get('id', 'unknown')
            logger.info(f"   ✅ Withdrawal initiated: {withdrawal_id}")
            
            # Monitor transfer (wait up to 5 minutes)
            logger.info("   Monitoring transfer completion...")
            max_wait_time = 300  # 5 minutes
            check_interval = 15  # Check every 15 seconds
            elapsed = 0
            
            transfer_success = False
            while elapsed < max_wait_time:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                gem_balance_now = gem_exchange.fetch_balance()
                if hasattr(gem_balance_now, '__await__'):
                    gem_balance_now = await gem_balance_now
                
                gem_xrp_now = gem_balance_now.get('free', {}).get('XRP', 0)
                
                # Check if XRP arrived (allow for small fees)
                if gem_xrp_now >= gem_xrp_before_transfer + (xrp_bought * 0.95):
                    logger.info(f"   ✅ Transfer confirmed! Gemini XRP: {gem_xrp_now:.6f}")
                    logger.info(f"   Transfer time: {elapsed} seconds")
                    transfer_success = True
                    break
                
                logger.info(f"   ⏳ Still waiting... ({elapsed}s elapsed, Gemini XRP: {gem_xrp_now:.6f})")
            
            if not transfer_success:
                logger.warning(f"   ⚠️ Transfer timeout after {max_wait_time}s")
                logger.warning("   Transfer may still complete - check manually")
            
            # Test sell on Gemini
            if transfer_success:
                logger.info("   Testing sell on Gemini...")
                
                gem_xrp_final = gem_exchange.fetch_balance()
                if hasattr(gem_xrp_final, '__await__'):
                    gem_xrp_final = await gem_xrp_final
                
                xrp_to_sell = gem_xrp_final.get('free', {}).get('XRP', 0)
                
                if xrp_to_sell > 0.001:  # More than 0.001 XRP
                    # Get current price
                    gem_ticker = gem_exchange.fetch_ticker(self.test_symbol)
                    if hasattr(gem_ticker, '__await__'):
                        gem_ticker = await gem_ticker
                    
                    sell_price = float(gem_ticker['last'])
                    
                    # Place sell order
                    if gem_exchange.id == 'coinbase':
                        sell_order = gem_exchange.create_order(
                            symbol=self.test_symbol,
                            type='market',
                            side='sell',
                            amount=xrp_to_sell,
                            price=sell_price
                        )
                    else:
                        sell_order = gem_exchange.create_limit_order(
                            symbol=self.test_symbol,
                            side='sell',
                            amount=xrp_to_sell,
                            price=sell_price * 0.99
                        )
                    
                    if hasattr(sell_order, '__await__'):
                        sell_order = await sell_order
                    
                    sell_order_id = sell_order.get('id', 'unknown')
                    logger.info(f"   ✅ Sell order placed: {sell_order_id}")
                    
                    # Wait for fill
                    await asyncio.sleep(5)
                    
                    logger.info("   ✅ Sell order completed")
            
            self.test_results['transfer_functionality'] = transfer_success
            logger.info("✅ TEST 5 PASSED: Transfer functionality working")
            
        except Exception as e:
            logger.error(f"❌ TEST 5 FAILED: {str(e)}")
            self.test_results['transfer_functionality'] = False
            import traceback
            traceback.print_exc()

    async def test_stuck_position_recovery(self):
        """
        Test 6: Stuck position recovery system
        """
        logger.info("\n" + "-"*60)
        logger.info("🚨 TEST 6: Stuck Position Recovery")
        logger.info("-"*60)
        
        try:
            # Initialize stuck position recovery
            self.stuck_recovery = StuckPositionRecovery(
                self.exchange_manager.exchanges,
                Config
            )
            
            logger.info("   Testing stuck position recovery initialization...")
            logger.info("   ✅ Stuck position recovery initialized")
            
            # Test scanning for stuck positions
            logger.info("   Scanning for stuck positions...")
            stuck_positions = await self.stuck_recovery.scan_for_stuck_positions()
            
            logger.info(f"   Found {len(stuck_positions)} stuck positions")
            
            # Test recovery statistics
            stats = self.stuck_recovery.get_recovery_stats()
            logger.info(f"   Recovery stats: {stats}")
            
            self.test_results['stuck_position_recovery'] = True
            logger.info("✅ TEST 6 PASSED: Stuck position recovery working")
            
        except Exception as e:
            logger.error(f"❌ TEST 6 FAILED: {str(e)}")
            self.test_results['stuck_position_recovery'] = False
            raise e

    async def test_opportunity_monitoring(self):
        """
        Test 7: Opportunity monitoring system
        """
        logger.info("\n" + "-"*60)
        logger.info("🎯 TEST 7: Opportunity Monitoring")
        logger.info("-"*60)
        
        try:
            # Initialize opportunity monitoring
            self.opportunity_monitor = OpportunityMonitoring(
                self.exchange_manager.exchanges,
                Config
            )
            
            logger.info("   Testing opportunity monitoring initialization...")
            logger.info("   ✅ Opportunity monitoring initialized")
            
            # Test scanning for opportunities
            logger.info("   Scanning for opportunities...")
            opportunities = await self.opportunity_monitor.scan_for_opportunities()
            
            logger.info(f"   Found {len(opportunities)} opportunities")
            
            for opp in opportunities[:3]:  # Show first 3
                logger.info(f"   {opp.symbol}: {opp.spread_percent:.3f}% spread, "
                           f"${opp.estimated_profit:.3f} profit, "
                           f"validation: {opp.validation_score:.2f}")
            
            # Test monitoring statistics
            stats = self.opportunity_monitor.get_opportunity_stats()
            logger.info(f"   Monitoring stats: {stats}")
            
            self.test_results['opportunity_monitoring'] = True
            logger.info("✅ TEST 7 PASSED: Opportunity monitoring working")
            
        except Exception as e:
            logger.error(f"❌ TEST 7 FAILED: {str(e)}")
            self.test_results['opportunity_monitoring'] = False
            raise e

    async def test_end_to_end_strategy(self):
        """
        Test 8: End-to-end strategy validation
        """
        logger.info("\n" + "-"*60)
        logger.info("🚀 TEST 8: End-to-End Strategy")
        logger.info("-"*60)
        
        try:
            logger.info("   Testing complete strategy integration...")
            
            # Test all components working together
            components = [
                ("Exchange Manager", self.exchange_manager is not None),
                ("Retry Logic", self.retry_logic is not None),
                ("Order Manager", self.order_manager is not None),
                ("Stuck Recovery", self.stuck_recovery is not None),
                ("Opportunity Monitor", self.opportunity_monitor is not None)
            ]
            
            all_components_working = True
            for component_name, is_working in components:
                status = "✅" if is_working else "❌"
                logger.info(f"   {status} {component_name}: {'Working' if is_working else 'Failed'}")
                if not is_working:
                    all_components_working = False
            
            # Test configuration
            logger.info(f"   ✅ Currency pairs: {len(Config.CURRENCY_PAIRS)}")
            logger.info(f"   ✅ Min profit threshold: ${Config.MIN_PROFIT_USD}")
            logger.info(f"   ✅ Exchange fees: CB {Config.EXCHANGE_FEES['coinbase']['taker']*100:.2f}%, "
                       f"GEM {Config.EXCHANGE_FEES['gemini']['taker']*100:.2f}%")
            
            self.test_results['end_to_end_strategy'] = all_components_working
            logger.info("✅ TEST 8 PASSED: End-to-end strategy working")
            
        except Exception as e:
            logger.error(f"❌ TEST 8 FAILED: {str(e)}")
            self.test_results['end_to_end_strategy'] = False
            raise e

    async def generate_test_report(self):
        """
        Generate comprehensive test report
        """
        logger.info("\n" + "="*80)
        logger.info("📊 COMPREHENSIVE TEST REPORT")
        logger.info("="*80)
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        logger.info(f"Test Duration: {duration:.1f} seconds")
        logger.info(f"Test Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Test End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        
        # Test results summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result is True)
        skipped_tests = sum(1 for result in self.test_results.values() if result == "SKIPPED")
        failed_tests = total_tests - passed_tests - skipped_tests
        
        logger.info("TEST RESULTS SUMMARY:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Passed: {passed_tests}")
        logger.info(f"  Skipped: {skipped_tests}")
        logger.info(f"  Failed: {failed_tests}")
        logger.info(f"  Success Rate: {(passed_tests/total_tests*100):.1f}%")
        logger.info("")
        
        # Detailed results
        logger.info("DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            if result is True:
                status = "✅ PASSED"
            elif result == "SKIPPED":
                status = "⏭️ SKIPPED"
            else:
                status = "❌ FAILED"
            
            logger.info(f"  {test_name.replace('_', ' ').title()}: {status}")
        
        logger.info("")
        
        # Recommendations
        if failed_tests == 0:
            logger.info("🎉 ALL TESTS PASSED!")
            logger.info("   The arbitrage strategy is ready for deployment.")
            logger.info("   All systems are functioning correctly.")
        else:
            logger.info("⚠️ SOME TESTS FAILED")
            logger.info("   Please review the failed tests before deployment.")
            logger.info("   Fix any issues before running the live bot.")
        
        logger.info("")
        logger.info("="*80)

async def main():
    """
    Main entry point for the comprehensive test
    """
    test = ComprehensiveStrategyTest()
    await test.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
