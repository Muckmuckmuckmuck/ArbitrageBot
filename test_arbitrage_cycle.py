#!/usr/bin/env python3
"""
Cross-Exchange Arbitrage Test Script
Tests the complete arbitrage cycle with $0.50 of XRP:
1. Buy XRP on Coinbase
2. Transfer to Gemini
3. Sell on Gemini
4. Buy XRP on Gemini
5. Transfer to Coinbase
6. Sell on Coinbase

This validates all critical functions before running the full bot.
"""

import os
import sys
import time
import asyncio
from datetime import datetime
from decimal import Decimal
import ccxt

# ============================================================================
# CONFIGURATION
# ============================================================================

TEST_AMOUNT_USD = 0.50  # Test with $0.50 of XRP
TEST_CRYPTO = "XRP"
TRANSFER_TIMEOUT = 300  # 5 minutes max wait for transfers
BALANCE_CHECK_INTERVAL = 5  # Check every 5 seconds

# ============================================================================
# LOGGING SETUP
# ============================================================================

class TestLogger:
    """Enhanced logger with timestamps and visual separators"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.step_count = 0
        self.errors = []
        self.warnings = []
    
    def header(self, message):
        """Print a major section header"""
        print("\n" + "=" * 80)
        print(f"  {message}")
        print("=" * 80)
    
    def step(self, message):
        """Print a test step"""
        self.step_count += 1
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"\n[STEP {self.step_count}] [{elapsed:.1f}s] {message}")
        print("-" * 80)
    
    def info(self, message, indent=0):
        """Print an info message"""
        prefix = "  " * indent
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{prefix}[{timestamp}] ℹ️  {message}")
    
    def success(self, message, indent=0):
        """Print a success message"""
        prefix = "  " * indent
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{prefix}[{timestamp}] ✅ {message}")
    
    def warning(self, message, indent=0):
        """Print a warning message"""
        prefix = "  " * indent
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{prefix}[{timestamp}] ⚠️  {message}")
        self.warnings.append(message)
    
    def error(self, message, indent=0):
        """Print an error message"""
        prefix = "  " * indent
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{prefix}[{timestamp}] ❌ {message}")
        self.errors.append(message)
    
    def data(self, key, value, indent=0):
        """Print a key-value pair"""
        prefix = "  " * indent
        print(f"{prefix}   {key}: {value}")
    
    def summary(self):
        """Print final summary"""
        self.header("TEST SUMMARY")
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        print(f"Steps completed: {self.step_count}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Errors: {len(self.errors)}")
        
        if self.errors:
            print("\n❌ ERRORS ENCOUNTERED:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.errors:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n💥 {len(self.errors)} TEST(S) FAILED")
        
        print("=" * 80)

logger = TestLogger()

# ============================================================================
# EXCHANGE INITIALIZATION
# ============================================================================

def init_exchanges():
    """Initialize Coinbase and Gemini exchanges"""
    logger.step("Initializing exchanges")
    
    # Get API credentials
    coinbase_key = os.getenv('COINBASE_API_KEY')
    coinbase_secret = os.getenv('COINBASE_API_SECRET')
    gemini_key = os.getenv('GEMINI_API_KEY')
    gemini_secret = os.getenv('GEMINI_API_SECRET')
    
    if not all([coinbase_key, coinbase_secret, gemini_key, gemini_secret]):
        logger.error("Missing API credentials in environment variables")
        sys.exit(1)
    
    logger.info("API credentials found")
    
    # Initialize Coinbase
    try:
        coinbase = ccxt.coinbase({
            'apiKey': coinbase_key,
            'secret': coinbase_secret,
            'enableRateLimit': True,
        })
        coinbase.load_markets()
        logger.success(f"Coinbase initialized: {len(coinbase.markets)} markets")
    except Exception as e:
        logger.error(f"Failed to initialize Coinbase: {e}")
        sys.exit(1)
    
    # Initialize Gemini
    try:
        gemini = ccxt.gemini({
            'apiKey': gemini_key,
            'secret': gemini_secret,
            'enableRateLimit': True,
        })
        gemini.load_markets()
        logger.success(f"Gemini initialized: {len(gemini.markets)} markets")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        sys.exit(1)
    
    return coinbase, gemini

# ============================================================================
# BALANCE FUNCTIONS
# ============================================================================

def get_balance(exchange, currency):
    """Get balance for a specific currency"""
    try:
        balance = exchange.fetch_balance()
        free = balance.get('free', {}).get(currency, 0)
        total = balance.get('total', {}).get(currency, 0)
        return {'free': free, 'total': total}
    except Exception as e:
        logger.error(f"Error fetching {currency} balance: {e}")
        return {'free': 0, 'total': 0}

def log_balances(coinbase, gemini):
    """Log current balances on both exchanges"""
    logger.info("Current balances:")
    
    # Coinbase
    cb_usd = get_balance(coinbase, 'USD')
    cb_xrp = get_balance(coinbase, TEST_CRYPTO)
    logger.data(f"Coinbase USD", f"${cb_usd['free']:.2f} free, ${cb_usd['total']:.2f} total", indent=1)
    logger.data(f"Coinbase {TEST_CRYPTO}", f"{cb_xrp['free']:.4f} free, {cb_xrp['total']:.4f} total", indent=1)
    
    # Gemini
    gem_usd = get_balance(gemini, 'USD')
    gem_xrp = get_balance(gemini, TEST_CRYPTO)
    logger.data(f"Gemini USD", f"${gem_usd['free']:.2f} free, ${gem_usd['total']:.2f} total", indent=1)
    logger.data(f"Gemini {TEST_CRYPTO}", f"{gem_xrp['free']:.4f} free, {gem_xrp['total']:.4f} total", indent=1)
    
    return {
        'coinbase': {'usd': cb_usd, 'xrp': cb_xrp},
        'gemini': {'usd': gem_usd, 'xrp': gem_xrp}
    }

# ============================================================================
# TRADING FUNCTIONS
# ============================================================================

def buy_crypto(exchange, exchange_name, symbol, amount_usd):
    """Buy crypto with USD"""
    logger.info(f"Buying ${amount_usd:.2f} of {symbol} on {exchange_name}")
    
    try:
        # Get current price
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        logger.data("Current price", f"${price:.4f}", indent=1)
        
        # Calculate amount to buy
        amount = amount_usd / price
        logger.data("Amount to buy", f"{amount:.4f} {symbol.split('/')[0]}", indent=1)
        
        # Place market buy order
        logger.info(f"Placing market buy order...", indent=1)
        order = exchange.create_market_buy_order(symbol, amount)
        
        # Log order details
        logger.success(f"Order placed: {order['id']}", indent=1)
        logger.data("Status", order['status'], indent=2)
        logger.data("Filled", f"{order.get('filled', 0):.4f}", indent=2)
        logger.data("Cost", f"${order.get('cost', 0):.2f}", indent=2)
        
        # Wait a moment for order to settle
        time.sleep(2)
        
        # Fetch order status
        order_status = exchange.fetch_order(order['id'], symbol)
        logger.data("Final status", order_status['status'], indent=2)
        
        if order_status['status'] == 'closed':
            actual_amount = float(order_status.get('filled', 0))
            actual_cost = float(order_status.get('cost', 0))
            logger.success(f"Buy complete: {actual_amount:.4f} {symbol.split('/')[0]} for ${actual_cost:.2f}", indent=1)
            return actual_amount
        else:
            logger.error(f"Order not filled: {order_status['status']}", indent=1)
            return 0
        
    except Exception as e:
        logger.error(f"Buy failed: {e}", indent=1)
        return 0

def sell_crypto(exchange, exchange_name, symbol, amount):
    """Sell crypto for USD"""
    logger.info(f"Selling {amount:.4f} {symbol.split('/')[0]} on {exchange_name}")
    
    try:
        # Get current price
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        logger.data("Current price", f"${price:.4f}", indent=1)
        logger.data("Expected revenue", f"${amount * price:.2f}", indent=1)
        
        # Place market sell order (or limit for Gemini)
        logger.info(f"Placing sell order...", indent=1)
        
        if exchange_name.lower() == 'gemini':
            # Gemini requires limit orders
            order = exchange.create_limit_sell_order(symbol, amount, price)
        else:
            order = exchange.create_market_sell_order(symbol, amount)
        
        # Log order details
        logger.success(f"Order placed: {order['id']}", indent=1)
        logger.data("Status", order['status'], indent=2)
        
        # Wait for order to settle
        time.sleep(2)
        
        # Fetch order status
        order_status = exchange.fetch_order(order['id'], symbol)
        logger.data("Final status", order_status['status'], indent=2)
        
        if order_status['status'] == 'closed':
            actual_revenue = float(order_status.get('cost', 0))
            logger.success(f"Sell complete: ${actual_revenue:.2f} received", indent=1)
            return actual_revenue
        else:
            logger.warning(f"Order status: {order_status['status']}", indent=1)
            return 0
        
    except Exception as e:
        logger.error(f"Sell failed: {e}", indent=1)
        return 0

# ============================================================================
# TRANSFER FUNCTIONS
# ============================================================================

def get_deposit_address(exchange, exchange_name, currency):
    """Get deposit address for a currency"""
    logger.info(f"Getting {currency} deposit address for {exchange_name}", indent=1)
    
    try:
        address_info = exchange.fetch_deposit_address(currency)
        address = address_info['address']
        tag = address_info.get('tag', None)
        
        logger.success(f"Deposit address: {address}", indent=2)
        if tag:
            logger.data("Destination tag", tag, indent=2)
        
        return address, tag
        
    except Exception as e:
        logger.error(f"Failed to get deposit address: {e}", indent=2)
        return None, None

def transfer_crypto(from_exchange, from_name, to_exchange, to_name, currency, amount):
    """Transfer crypto from one exchange to another"""
    logger.info(f"Transferring {amount:.4f} {currency} from {from_name} to {to_name}")
    
    # Get destination address
    to_address, to_tag = get_deposit_address(to_exchange, to_name, currency)
    if not to_address:
        logger.error("Cannot transfer without destination address", indent=1)
        return False
    
    # Get initial balance on destination
    initial_balance = get_balance(to_exchange, currency)['free']
    logger.data("Initial balance on destination", f"{initial_balance:.4f} {currency}", indent=1)
    
    try:
        # Initiate withdrawal
        logger.info(f"Initiating withdrawal from {from_name}...", indent=1)
        
        withdrawal_params = {}
        if to_tag:
            withdrawal_params['tag'] = to_tag
        
        withdrawal = from_exchange.withdraw(currency, amount, to_address, withdrawal_params)
        
        logger.success(f"Withdrawal initiated: {withdrawal.get('id', 'N/A')}", indent=2)
        logger.data("Status", withdrawal.get('status', 'unknown'), indent=2)
        
        # Monitor destination balance
        logger.info(f"Monitoring {to_name} for incoming {currency}...", indent=1)
        logger.info(f"Will check every {BALANCE_CHECK_INTERVAL}s for up to {TRANSFER_TIMEOUT}s", indent=2)
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < TRANSFER_TIMEOUT:
            check_count += 1
            time.sleep(BALANCE_CHECK_INTERVAL)
            
            current_balance = get_balance(to_exchange, currency)['free']
            elapsed = time.time() - start_time
            
            logger.info(f"Check #{check_count} ({elapsed:.0f}s): {current_balance:.4f} {currency}", indent=2)
            
            if current_balance > initial_balance:
                received = current_balance - initial_balance
                logger.success(f"Transfer complete! Received {received:.4f} {currency} in {elapsed:.0f}s", indent=2)
                return True
        
        # Timeout
        logger.error(f"Transfer timeout after {TRANSFER_TIMEOUT}s", indent=1)
        logger.warning(f"Check {to_name} manually - transfer may still arrive", indent=1)
        return False
        
    except Exception as e:
        logger.error(f"Transfer failed: {e}", indent=1)
        return False

# ============================================================================
# TEST CYCLES
# ============================================================================

def test_coinbase_to_gemini(coinbase, gemini):
    """Test: Buy on Coinbase → Transfer to Gemini → Sell on Gemini"""
    logger.header("TEST 1: COINBASE → GEMINI ARBITRAGE CYCLE")
    
    symbol = f"{TEST_CRYPTO}/USD"
    
    # Step 1: Buy on Coinbase
    logger.step(f"Buy ${TEST_AMOUNT_USD:.2f} of {TEST_CRYPTO} on Coinbase")
    amount_bought = buy_crypto(coinbase, "Coinbase", symbol, TEST_AMOUNT_USD)
    
    if amount_bought == 0:
        logger.error("Cannot proceed - buy failed")
        return False
    
    # Step 2: Transfer to Gemini
    logger.step(f"Transfer {amount_bought:.4f} {TEST_CRYPTO} to Gemini")
    transfer_success = transfer_crypto(
        coinbase, "Coinbase",
        gemini, "Gemini",
        TEST_CRYPTO, amount_bought
    )
    
    if not transfer_success:
        logger.error("Cannot proceed - transfer failed or timed out")
        logger.warning(f"You may have {amount_bought:.4f} {TEST_CRYPTO} stuck on Coinbase")
        return False
    
    # Step 3: Sell on Gemini
    logger.step(f"Sell {amount_bought:.4f} {TEST_CRYPTO} on Gemini")
    revenue = sell_crypto(gemini, "Gemini", symbol, amount_bought)
    
    if revenue == 0:
        logger.error("Sell failed")
        return False
    
    # Calculate net result
    logger.step("Calculate net result")
    net = revenue - TEST_AMOUNT_USD
    logger.data("Initial investment", f"${TEST_AMOUNT_USD:.2f}", indent=1)
    logger.data("Final revenue", f"${revenue:.2f}", indent=1)
    logger.data("Net result", f"${net:.2f} ({(net/TEST_AMOUNT_USD)*100:.2f}%)", indent=1)
    
    if net >= 0:
        logger.success("Test 1 PASSED: Coinbase → Gemini cycle complete")
    else:
        logger.warning(f"Test 1 completed with loss: ${abs(net):.2f}")
    
    return True

def test_gemini_to_coinbase(coinbase, gemini):
    """Test: Buy on Gemini → Transfer to Coinbase → Sell on Coinbase"""
    logger.header("TEST 2: GEMINI → COINBASE ARBITRAGE CYCLE")
    
    symbol = f"{TEST_CRYPTO}/USD"
    
    # Step 1: Buy on Gemini
    logger.step(f"Buy ${TEST_AMOUNT_USD:.2f} of {TEST_CRYPTO} on Gemini")
    amount_bought = buy_crypto(gemini, "Gemini", symbol, TEST_AMOUNT_USD)
    
    if amount_bought == 0:
        logger.error("Cannot proceed - buy failed")
        return False
    
    # Step 2: Transfer to Coinbase
    logger.step(f"Transfer {amount_bought:.4f} {TEST_CRYPTO} to Coinbase")
    transfer_success = transfer_crypto(
        gemini, "Gemini",
        coinbase, "Coinbase",
        TEST_CRYPTO, amount_bought
    )
    
    if not transfer_success:
        logger.error("Cannot proceed - transfer failed or timed out")
        logger.warning(f"You may have {amount_bought:.4f} {TEST_CRYPTO} stuck on Gemini")
        return False
    
    # Step 3: Sell on Coinbase
    logger.step(f"Sell {amount_bought:.4f} {TEST_CRYPTO} on Coinbase")
    revenue = sell_crypto(coinbase, "Coinbase", symbol, amount_bought)
    
    if revenue == 0:
        logger.error("Sell failed")
        return False
    
    # Calculate net result
    logger.step("Calculate net result")
    net = revenue - TEST_AMOUNT_USD
    logger.data("Initial investment", f"${TEST_AMOUNT_USD:.2f}", indent=1)
    logger.data("Final revenue", f"${revenue:.2f}", indent=1)
    logger.data("Net result", f"${net:.2f} ({(net/TEST_AMOUNT_USD)*100:.2f}%)", indent=1)
    
    if net >= 0:
        logger.success("Test 2 PASSED: Gemini → Coinbase cycle complete")
    else:
        logger.warning(f"Test 2 completed with loss: ${abs(net):.2f}")
    
    return True

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run all tests"""
    logger.header("CROSS-EXCHANGE ARBITRAGE TEST SUITE")
    logger.info(f"Testing with ${TEST_AMOUNT_USD:.2f} of {TEST_CRYPTO}")
    logger.info(f"Transfer timeout: {TRANSFER_TIMEOUT}s")
    
    # Initialize exchanges
    coinbase, gemini = init_exchanges()
    
    # Log initial balances
    logger.step("Check initial balances")
    initial_balances = log_balances(coinbase, gemini)
    
    # Verify sufficient funds
    cb_usd = initial_balances['coinbase']['usd']['free']
    gem_usd = initial_balances['gemini']['usd']['free']
    
    if cb_usd < TEST_AMOUNT_USD:
        logger.error(f"Insufficient USD on Coinbase: ${cb_usd:.2f} < ${TEST_AMOUNT_USD:.2f}")
        logger.info("Please add funds to Coinbase to run Test 1")
    
    if gem_usd < TEST_AMOUNT_USD:
        logger.error(f"Insufficient USD on Gemini: ${gem_usd:.2f} < ${TEST_AMOUNT_USD:.2f}")
        logger.info("Please add funds to Gemini to run Test 2")
    
    if cb_usd < TEST_AMOUNT_USD and gem_usd < TEST_AMOUNT_USD:
        logger.error("Insufficient funds on both exchanges")
        sys.exit(1)
    
    # Run tests
    test1_passed = False
    test2_passed = False
    
    if cb_usd >= TEST_AMOUNT_USD:
        test1_passed = test_coinbase_to_gemini(coinbase, gemini)
        
        # Wait between tests
        if test1_passed and gem_usd >= TEST_AMOUNT_USD:
            logger.info("\nWaiting 10 seconds before Test 2...")
            time.sleep(10)
    
    if gem_usd >= TEST_AMOUNT_USD:
        test2_passed = test_gemini_to_coinbase(coinbase, gemini)
    
    # Log final balances
    logger.step("Check final balances")
    final_balances = log_balances(coinbase, gemini)
    
    # Summary
    logger.summary()
    
    # Exit code
    if logger.errors:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.error("\n\nTest interrupted by user")
        logger.summary()
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        logger.summary()
        sys.exit(1)

