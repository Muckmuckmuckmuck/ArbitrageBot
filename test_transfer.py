#!/usr/bin/env python3
"""
Quick Transfer Test Script
Tests if crypto transfers work between Coinbase and Gemini
Uses $0.50 of XRP for a cheap, fast test
"""

import os
import sys
import time
import asyncio
from datetime import datetime
import ccxt

# ============================================================================
# CONFIGURATION
# ============================================================================

TEST_CRYPTO = "XRP"
TEST_AMOUNT_USD = 0.50  # Test with $0.50 of XRP
TRANSFER_TIMEOUT = 300  # 5 minutes max
CHECK_INTERVAL = 5  # Check every 5 seconds

# ============================================================================
# SETUP
# ============================================================================

def log(message, level="INFO"):
    """Formatted logging"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level:5} | {message}")

def separator(title=""):
    """Visual separator"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}")

# ============================================================================
# INITIALIZE EXCHANGES
# ============================================================================

separator("INITIALIZING EXCHANGES")

# Coinbase
coinbase = ccxt.coinbase({
    'apiKey': os.getenv('COINBASE_API_KEY'),
    'secret': os.getenv('COINBASE_SECRET_KEY'),
    'enableRateLimit': True,
})

# Gemini
gemini = ccxt.gemini({
    'apiKey': os.getenv('GEMINI_API_KEY'),
    'secret': os.getenv('GEMINI_SECRET_KEY'),
    'enableRateLimit': True,
})

log("✅ Coinbase initialized")
log("✅ Gemini initialized")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_balance(exchange, currency):
    """Get free balance for a currency"""
    balance = exchange.fetch_balance()
    return balance.get('free', {}).get(currency, 0)

def get_xrp_price(exchange):
    """Get current XRP price"""
    ticker = exchange.fetch_ticker(f'{TEST_CRYPTO}/USD')
    return ticker['last']

def buy_xrp(exchange, exchange_name, usd_amount):
    """Buy XRP with USD"""
    log(f"Buying ${usd_amount:.2f} of {TEST_CRYPTO} on {exchange_name}...")
    
    price = get_xrp_price(exchange)
    amount = usd_amount / price
    
    log(f"   Price: ${price:.4f}")
    log(f"   Amount: {amount:.4f} {TEST_CRYPTO}")
    
    # Place market buy order
    # For Coinbase, we need to pass the price parameter
    if exchange_name.lower() == 'coinbase':
        order = exchange.create_order(
            symbol=f'{TEST_CRYPTO}/USD',
            type='market',
            side='buy',
            amount=amount,
            price=price  # Required for Coinbase
        )
    else:
        order = exchange.create_order(
            symbol=f'{TEST_CRYPTO}/USD',
            type='market',
            side='buy',
            amount=amount
        )
    
    log(f"✅ Buy order placed: {order['id']}")
    time.sleep(2)  # Wait for order to settle
    
    actual_amount = get_balance(exchange, TEST_CRYPTO)
    log(f"✅ Balance after buy: {actual_amount:.4f} {TEST_CRYPTO}")
    
    return actual_amount

def transfer_xrp(from_exchange, from_name, to_exchange, to_name, amount):
    """Transfer XRP from one exchange to another"""
    log(f"Transferring {amount:.4f} {TEST_CRYPTO} from {from_name} to {to_name}...")
    
    # Get deposit address on destination exchange
    log(f"   Getting {TEST_CRYPTO} deposit address on {to_name}...")
    deposit_info = to_exchange.fetch_deposit_address(TEST_CRYPTO)
    
    address = deposit_info['address']
    tag = deposit_info.get('tag', None)
    
    log(f"   Deposit address: {address}")
    if tag:
        log(f"   Destination tag: {tag}")
    
    # Get initial balance on destination
    initial_balance = get_balance(to_exchange, TEST_CRYPTO)
    log(f"   Initial {to_name} balance: {initial_balance:.4f} {TEST_CRYPTO}")
    
    # Initiate withdrawal from source exchange
    log(f"   Initiating withdrawal from {from_name}...")
    
    withdrawal_params = {}
    if tag:
        withdrawal_params['tag'] = tag
    
    withdrawal = from_exchange.withdraw(
        code=TEST_CRYPTO,
        amount=amount,
        address=address,
        tag=tag,
        params=withdrawal_params
    )
    
    log(f"✅ Withdrawal initiated: {withdrawal.get('id', 'N/A')}")
    log(f"   Txn ID: {withdrawal.get('txid', 'Pending...')}")
    
    # Monitor destination balance
    log(f"   Monitoring {to_name} balance (timeout: {TRANSFER_TIMEOUT}s)...")
    
    start_time = time.time()
    checks = 0
    
    while time.time() - start_time < TRANSFER_TIMEOUT:
        checks += 1
        current_balance = get_balance(to_exchange, TEST_CRYPTO)
        
        if current_balance > initial_balance:
            arrived_amount = current_balance - initial_balance
            elapsed = time.time() - start_time
            log(f"✅ TRANSFER COMPLETE!")
            log(f"   Sent: {amount:.4f} {TEST_CRYPTO}")
            log(f"   Received: {arrived_amount:.4f} {TEST_CRYPTO}")
            log(f"   Time: {elapsed:.0f}s ({checks} checks)")
            return arrived_amount
        
        if checks % 6 == 0:  # Every 30 seconds
            elapsed = time.time() - start_time
            log(f"   [{elapsed:.0f}s] Still waiting... (balance: {current_balance:.4f})")
        
        time.sleep(CHECK_INTERVAL)
    
    log(f"❌ TIMEOUT: Transfer not confirmed after {TRANSFER_TIMEOUT}s", "ERROR")
    return 0

def sell_xrp(exchange, exchange_name, amount):
    """Sell XRP for USD"""
    log(f"Selling {amount:.4f} {TEST_CRYPTO} on {exchange_name}...")
    
    price = get_xrp_price(exchange)
    expected_usd = amount * price
    
    log(f"   Price: ${price:.4f}")
    log(f"   Expected: ${expected_usd:.2f}")
    
    # Place market sell order
    order = exchange.create_order(
        symbol=f'{TEST_CRYPTO}/USD',
        type='market',
        side='sell',
        amount=amount
    )
    
    log(f"✅ Sell order placed: {order['id']}")
    time.sleep(2)  # Wait for order to settle
    
    usd_balance = get_balance(exchange, 'USD')
    log(f"✅ USD balance after sell: ${usd_balance:.2f}")
    
    return usd_balance

# ============================================================================
# TEST 1: COINBASE → GEMINI
# ============================================================================

separator("TEST 1: COINBASE → GEMINI TRANSFER")

log("Step 1: Check initial balances")
cb_usd_initial = get_balance(coinbase, 'USD')
cb_xrp_initial = get_balance(coinbase, TEST_CRYPTO)
gem_usd_initial = get_balance(gemini, 'USD')
gem_xrp_initial = get_balance(gemini, TEST_CRYPTO)

log(f"   Coinbase: ${cb_usd_initial:.2f} USD, {cb_xrp_initial:.4f} {TEST_CRYPTO}")
log(f"   Gemini:   ${gem_usd_initial:.2f} USD, {gem_xrp_initial:.4f} {TEST_CRYPTO}")

if cb_usd_initial < TEST_AMOUNT_USD:
    log(f"❌ ERROR: Insufficient USD on Coinbase (need ${TEST_AMOUNT_USD:.2f}, have ${cb_usd_initial:.2f})", "ERROR")
    sys.exit(1)

separator()

log("Step 2: Buy XRP on Coinbase")
try:
    xrp_amount = buy_xrp(coinbase, "Coinbase", TEST_AMOUNT_USD)
except Exception as e:
    log(f"❌ ERROR buying XRP: {e}", "ERROR")
    sys.exit(1)

separator()

log("Step 3: Transfer XRP from Coinbase to Gemini")
try:
    arrived_amount = transfer_xrp(coinbase, "Coinbase", gemini, "Gemini", xrp_amount)
    
    if arrived_amount == 0:
        log("❌ Transfer failed or timed out", "ERROR")
        log("⚠️  XRP may still arrive later - check manually", "WARN")
        sys.exit(1)
        
except Exception as e:
    log(f"❌ ERROR during transfer: {e}", "ERROR")
    log(f"   Details: {str(e)}", "ERROR")
    sys.exit(1)

separator()

log("Step 4: Sell XRP on Gemini")
try:
    final_usd = sell_xrp(gemini, "Gemini", arrived_amount)
except Exception as e:
    log(f"❌ ERROR selling XRP: {e}", "ERROR")
    sys.exit(1)

# ============================================================================
# TEST 1 RESULTS
# ============================================================================

separator("TEST 1 RESULTS: COINBASE → GEMINI")

usd_spent = cb_usd_initial - get_balance(coinbase, 'USD')
usd_gained = get_balance(gemini, 'USD') - gem_usd_initial
net_change = usd_gained - usd_spent

log(f"💰 USD spent on Coinbase: ${usd_spent:.2f}")
log(f"💰 USD gained on Gemini:  ${usd_gained:.2f}")
log(f"📊 Net change: ${net_change:.2f}")

if net_change > -0.10:  # Allow up to 20% loss for fees
    log(f"✅ TEST 1 PASSED: Transfer works!", "SUCCESS")
else:
    log(f"⚠️  TEST 1 WARNING: High loss ({abs(net_change)/usd_spent*100:.1f}%)", "WARN")

# ============================================================================
# TEST 2: GEMINI → COINBASE
# ============================================================================

separator("TEST 2: GEMINI → COINBASE TRANSFER")

log("Waiting 10 seconds before Test 2...")
time.sleep(10)

log("Step 1: Check balances")
gem_usd_test2 = get_balance(gemini, 'USD')
log(f"   Gemini USD: ${gem_usd_test2:.2f}")

if gem_usd_test2 < TEST_AMOUNT_USD:
    log(f"❌ ERROR: Insufficient USD on Gemini (need ${TEST_AMOUNT_USD:.2f}, have ${gem_usd_test2:.2f})", "ERROR")
    log(f"⚠️  Skipping Test 2", "WARN")
    separator("FINAL SUMMARY")
    log("✅ Test 1: PASSED (Coinbase → Gemini works)")
    log("⚠️  Test 2: SKIPPED (Insufficient funds)")
    sys.exit(0)

separator()

log("Step 2: Buy XRP on Gemini")
try:
    xrp_amount = buy_xrp(gemini, "Gemini", TEST_AMOUNT_USD)
except Exception as e:
    log(f"❌ ERROR buying XRP: {e}", "ERROR")
    sys.exit(1)

separator()

log("Step 3: Transfer XRP from Gemini to Coinbase")
try:
    arrived_amount = transfer_xrp(gemini, "Gemini", coinbase, "Coinbase", xrp_amount)
    
    if arrived_amount == 0:
        log("❌ Transfer failed or timed out", "ERROR")
        log("⚠️  XRP may still arrive later - check manually", "WARN")
        sys.exit(1)
        
except Exception as e:
    log(f"❌ ERROR during transfer: {e}", "ERROR")
    log(f"   Details: {str(e)}", "ERROR")
    sys.exit(1)

separator()

log("Step 4: Sell XRP on Coinbase")
try:
    final_usd = sell_xrp(coinbase, "Coinbase", arrived_amount)
except Exception as e:
    log(f"❌ ERROR selling XRP: {e}", "ERROR")
    sys.exit(1)

# ============================================================================
# TEST 2 RESULTS
# ============================================================================

separator("TEST 2 RESULTS: GEMINI → COINBASE")

cb_usd_test2 = get_balance(coinbase, 'USD')
gem_usd_after = get_balance(gemini, 'USD')

usd_spent_test2 = gem_usd_test2 - gem_usd_after
usd_gained_test2 = cb_usd_test2 - (cb_usd_initial - usd_spent)  # Account for Test 1
net_change_test2 = usd_gained_test2 - usd_spent_test2

log(f"💰 USD spent on Gemini:   ${usd_spent_test2:.2f}")
log(f"💰 USD gained on Coinbase: ${usd_gained_test2:.2f}")
log(f"📊 Net change: ${net_change_test2:.2f}")

if net_change_test2 > -0.10:
    log(f"✅ TEST 2 PASSED: Transfer works!", "SUCCESS")
else:
    log(f"⚠️  TEST 2 WARNING: High loss ({abs(net_change_test2)/usd_spent_test2*100:.1f}%)", "WARN")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

separator("FINAL SUMMARY")

log("Test 1 (Coinbase → Gemini):")
log(f"   Net change: ${net_change:.2f}")
log(f"   Status: {'✅ PASS' if net_change > -0.10 else '⚠️  WARNING'}")

log("Test 2 (Gemini → Coinbase):")
log(f"   Net change: ${net_change_test2:.2f}")
log(f"   Status: {'✅ PASS' if net_change_test2 > -0.10 else '⚠️  WARNING'}")

separator()

if net_change > -0.10 and net_change_test2 > -0.10:
    log("🎉 ALL TESTS PASSED!", "SUCCESS")
    log("   Transfers work in both directions!")
    log("   Bot is ready for live trading!")
else:
    log("⚠️  SOME TESTS FAILED", "WARN")
    log("   Review errors above")
    log("   Check API key permissions")
    log("   Verify address whitelisting")

separator()

log(f"Total cost: ${abs(net_change) + abs(net_change_test2):.2f}")
log("(This is the cost of testing - fees + slippage)")

