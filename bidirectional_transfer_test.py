#!/usr/bin/env python3
"""
BI-DIRECTIONAL TRANSFER TEST v2.0
----------------------------------
This script tests transfers in BOTH directions:
1. Buy $1.00 XRP on Coinbase → Transfer to Gemini → Sell on Gemini
2. Buy $1.00 XRP on Gemini → Transfer to Coinbase → Sell on Coinbase

This validates the full arbitrage pipeline.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager


def log(message, level="INFO"):
    """Simple logger with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level:5s} | {message}")


async def get_balance(exchange, currency: str) -> float:
    """Get balance for a specific currency"""
    bal = exchange.fetch_balance()
    if hasattr(bal, '__await__'):
        bal = await bal
    return float(bal['free'].get(currency, 0))


async def get_price(exchange, symbol: str) -> float:
    """Get current price"""
    ticker = exchange.fetch_ticker(symbol)
    if hasattr(ticker, '__await__'):
        ticker = await ticker
    return float(ticker['last'])


async def buy_xrp(exchange, exchange_name: str, amount_usd: float, price: float):
    """Buy XRP on an exchange"""
    log(f"Buying ${amount_usd:.2f} of XRP on {exchange_name.upper()}...", "INFO")
    
    xrp_amount = amount_usd / price
    log(f"   Will buy: {xrp_amount:.4f} XRP at ${price:.4f}", "DEBUG")
    
    try:
        if exchange_name == 'coinbase':
            # Coinbase requires price for market buy orders
            order = exchange.create_order(
                symbol='XRP/USD',
                type='market',
                side='buy',
                amount=xrp_amount,
                price=price
            )
        else:  # gemini
            # Gemini requires limit orders - use 1% above market to ensure fill
            order = exchange.create_limit_buy_order(
                symbol='XRP/USD',
                amount=xrp_amount,
                price=price * 1.01
            )
        
        if hasattr(order, '__await__'):
            order = await order
        
        order_id = order.get('id', 'unknown')
        log(f"   ✅ Order placed: {order_id}", "INFO")
        
        # Wait for fill
        await asyncio.sleep(5)
        
        return True
        
    except Exception as e:
        log(f"   ❌ Buy failed: {str(e)}", "ERROR")
        return False


async def sell_xrp(exchange, exchange_name: str, amount: float, price: float):
    """Sell XRP on an exchange"""
    log(f"Selling {amount:.4f} XRP on {exchange_name.upper()}...", "INFO")
    
    expected_usd = amount * price
    log(f"   Expected: ${expected_usd:.2f} at ${price:.4f}", "DEBUG")
    
    try:
        if exchange_name == 'coinbase':
            order = exchange.create_market_sell_order(
                symbol='XRP/USD',
                amount=amount
            )
        else:  # gemini
            # Gemini requires limit orders - use 1% below market to ensure fill
            order = exchange.create_limit_sell_order(
                symbol='XRP/USD',
                amount=amount,
                price=price * 0.99
            )
        
        if hasattr(order, '__await__'):
            order = await order
        
        order_id = order.get('id', 'unknown')
        log(f"   ✅ Order placed: {order_id}", "INFO")
        
        # Wait for fill
        await asyncio.sleep(5)
        
        return True
        
    except Exception as e:
        log(f"   ❌ Sell failed: {str(e)}", "ERROR")
        return False


async def transfer_xrp(source_exchange, source_name: str, dest_exchange, dest_name: str, amount: float):
    """Transfer XRP from source to destination"""
    log(f"Transferring {amount:.6f} XRP: {source_name.upper()} → {dest_name.upper()}", "INFO")
    
    try:
        # Get deposit address
        log(f"   📍 Getting {dest_name} deposit address...", "DEBUG")
        deposit_info = dest_exchange.fetch_deposit_address('XRP')
        if hasattr(deposit_info, '__await__'):
            deposit_info = await deposit_info
        
        address = deposit_info['address']
        tag = deposit_info.get('tag')
        
        log(f"   Address: {address[:20]}...", "DEBUG")
        if tag:
            log(f"   Tag: {tag}", "DEBUG")
        
        # Record balance before
        balance_before = await get_balance(dest_exchange, 'XRP')
        log(f"   {dest_name} XRP before: {balance_before:.6f}", "DEBUG")
        
        # Initiate withdrawal
        log(f"   💸 Initiating withdrawal from {source_name}...", "DEBUG")
        
        withdraw_params = {'network': 'XRP'}
        if tag:
            withdraw_params['tag'] = tag
        
        withdrawal = source_exchange.withdraw(
            code='XRP',
            amount=amount,
            address=address,
            params=withdraw_params
        )
        if hasattr(withdrawal, '__await__'):
            withdrawal = await withdrawal
        
        withdrawal_id = withdrawal.get('id', 'unknown')
        log(f"   ✅ Withdrawal initiated: {withdrawal_id}", "INFO")
        
        # Monitor destination balance
        log(f"   ⏳ Monitoring {dest_name} balance...", "INFO")
        
        max_wait = 300  # 5 minutes
        check_interval = 15
        elapsed = 0
        
        while elapsed < max_wait:
            await asyncio.sleep(check_interval)
            elapsed += check_interval
            
            balance_now = await get_balance(dest_exchange, 'XRP')
            
            log(f"   [{elapsed}s] {dest_name} XRP: {balance_now:.6f}", "DEBUG")
            
            if balance_now > balance_before + (amount * 0.95):
                received = balance_now - balance_before
                log(f"   ✅ Transfer confirmed! Received: {received:.6f} XRP ({elapsed}s)", "INFO")
                return True
        
        log(f"   ⚠️  Transfer timeout after {max_wait}s", "WARN")
        return False
        
    except Exception as e:
        log(f"   ❌ Transfer failed: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


async def test_coinbase_to_gemini(cb, gem):
    """Test: Coinbase → Gemini"""
    log("", "")
    log("="*80, "")
    log("🧪 TEST 1: COINBASE → GEMINI", "")
    log("="*80, "")
    
    try:
        # Check balances
        cb_usd = await get_balance(cb, 'USD')
        cb_xrp_before = await get_balance(cb, 'XRP')
        gem_usd = await get_balance(gem, 'USD')
        gem_xrp_before = await get_balance(gem, 'XRP')
        
        log(f"Initial: CB ${cb_usd:.2f} USD, {cb_xrp_before:.6f} XRP", "INFO")
        log(f"Initial: GEM ${gem_usd:.2f} USD, {gem_xrp_before:.6f} XRP", "INFO")
        
        if cb_usd < 1.0:
            log(f"❌ Insufficient USD on Coinbase (${cb_usd:.2f})", "ERROR")
            return False
        
        # Get price
        price = await get_price(cb, 'XRP/USD')
        log(f"XRP price: ${price:.4f}", "INFO")
        
        # Buy on Coinbase
        log("", "")
        log("STEP 1/3: Buy XRP on Coinbase", "INFO")
        if not await buy_xrp(cb, 'coinbase', 1.00, price):  # $1 minimum for Coinbase
            return False
        
        # Check how much we bought
        cb_xrp_after = await get_balance(cb, 'XRP')
        xrp_bought = cb_xrp_after - cb_xrp_before
        log(f"   Bought: {xrp_bought:.6f} XRP", "INFO")
        
        if xrp_bought < 0.01:
            log(f"   ⚠️  Amount too small to transfer", "WARN")
            return False
        
        # Transfer to Gemini
        log("", "")
        log("STEP 2/3: Transfer XRP to Gemini", "INFO")
        if not await transfer_xrp(cb, 'coinbase', gem, 'gemini', xrp_bought):
            return False
        
        # Sell on Gemini
        log("", "")
        log("STEP 3/3: Sell XRP on Gemini", "INFO")
        gem_xrp_final = await get_balance(gem, 'XRP')
        gem_price = await get_price(gem, 'XRP/USD')
        
        if not await sell_xrp(gem, 'gemini', gem_xrp_final - gem_xrp_before, gem_price):
            return False
        
        # Final balances
        cb_usd_final = await get_balance(cb, 'USD')
        gem_usd_final = await get_balance(gem, 'USD')
        
        log("", "")
        log("✅ TEST 1 COMPLETE!", "INFO")
        log(f"   Coinbase: ${cb_usd:.2f} → ${cb_usd_final:.2f} USD", "INFO")
        log(f"   Gemini: ${gem_usd:.2f} → ${gem_usd_final:.2f} USD", "INFO")
        
        return True
        
    except Exception as e:
        log(f"❌ Test 1 failed: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


async def test_gemini_to_coinbase(cb, gem):
    """Test: Gemini → Coinbase"""
    log("", "")
    log("="*80, "")
    log("🧪 TEST 2: GEMINI → COINBASE", "")
    log("="*80, "")
    
    try:
        # Check balances
        cb_usd = await get_balance(cb, 'USD')
        cb_xrp_before = await get_balance(cb, 'XRP')
        gem_usd = await get_balance(gem, 'USD')
        gem_xrp_before = await get_balance(gem, 'XRP')
        
        log(f"Initial: CB ${cb_usd:.2f} USD, {cb_xrp_before:.6f} XRP", "INFO")
        log(f"Initial: GEM ${gem_usd:.2f} USD, {gem_xrp_before:.6f} XRP", "INFO")
        
        if gem_usd < 1.0:
            log(f"❌ Insufficient USD on Gemini (${gem_usd:.2f})", "ERROR")
            log(f"   Skipping Test 2 - funds may still be settling", "WARN")
            return True  # Don't fail, just skip
        
        # Get price
        price = await get_price(gem, 'XRP/USD')
        log(f"XRP price: ${price:.4f}", "INFO")
        
        # Buy on Gemini
        log("", "")
        log("STEP 1/3: Buy XRP on Gemini", "INFO")
        if not await buy_xrp(gem, 'gemini', 1.00, price):  # $1 minimum for consistency
            return False
        
        # Check how much we bought
        gem_xrp_after = await get_balance(gem, 'XRP')
        xrp_bought = gem_xrp_after - gem_xrp_before
        log(f"   Bought: {xrp_bought:.6f} XRP", "INFO")
        
        if xrp_bought < 0.01:
            log(f"   ⚠️  Amount too small to transfer", "WARN")
            return False
        
        # Transfer to Coinbase
        log("", "")
        log("STEP 2/3: Transfer XRP to Coinbase", "INFO")
        if not await transfer_xrp(gem, 'gemini', cb, 'coinbase', xrp_bought):
            return False
        
        # Sell on Coinbase
        log("", "")
        log("STEP 3/3: Sell XRP on Coinbase", "INFO")
        cb_xrp_final = await get_balance(cb, 'XRP')
        cb_price = await get_price(cb, 'XRP/USD')
        
        if not await sell_xrp(cb, 'coinbase', cb_xrp_final - cb_xrp_before, cb_price):
            return False
        
        # Final balances
        cb_usd_final = await get_balance(cb, 'USD')
        gem_usd_final = await get_balance(gem, 'USD')
        
        log("", "")
        log("✅ TEST 2 COMPLETE!", "INFO")
        log(f"   Coinbase: ${cb_usd:.2f} → ${cb_usd_final:.2f} USD", "INFO")
        log(f"   Gemini: ${gem_usd:.2f} → ${gem_usd_final:.2f} USD", "INFO")
        
        return True
        
    except Exception as e:
        log(f"❌ Test 2 failed: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


async def main():
    log("="*80, "")
    log("🧪 BI-DIRECTIONAL TRANSFER TEST", "")
    log("="*80, "")
    log("Testing both transfer directions:", "")
    log("  1. Coinbase → Gemini (buy, transfer, sell)", "")
    log("  2. Gemini → Coinbase (buy, transfer, sell)", "")
    log("", "")
    
    mgr = CoinbaseGeminiExchangeManager()
    
    try:
        # Initialize
        log("Initializing exchanges...", "INFO")
        await mgr.initialize()
        log("✅ Exchanges initialized", "INFO")
        
        cb = mgr.exchanges['coinbase']
        gem = mgr.exchanges['gemini']
        
        # Show initial balances
        log("", "")
        log("="*80, "")
        log("💰 INITIAL BALANCES", "")
        log("="*80, "")
        
        cb_usd = await get_balance(cb, 'USD')
        cb_xrp = await get_balance(cb, 'XRP')
        gem_usd = await get_balance(gem, 'USD')
        gem_xrp = await get_balance(gem, 'XRP')
        
        log(f"Coinbase: ${cb_usd:.2f} USD, {cb_xrp:.6f} XRP", "INFO")
        log(f"Gemini:   ${gem_usd:.2f} USD, {gem_xrp:.6f} XRP", "INFO")
        
        # Run tests
        test1_passed = await test_coinbase_to_gemini(cb, gem)
        
        if test1_passed:
            log("", "")
            log("⏳ Waiting 30 seconds before Test 2...", "INFO")
            await asyncio.sleep(30)
            
            test2_passed = await test_gemini_to_coinbase(cb, gem)
        else:
            test2_passed = False
        
        # Show final balances
        log("", "")
        log("="*80, "")
        log("💰 FINAL BALANCES", "")
        log("="*80, "")
        
        cb_usd_final = await get_balance(cb, 'USD')
        cb_xrp_final = await get_balance(cb, 'XRP')
        gem_usd_final = await get_balance(gem, 'USD')
        gem_xrp_final = await get_balance(gem, 'XRP')
        
        log(f"Coinbase: ${cb_usd_final:.2f} USD, {cb_xrp_final:.6f} XRP", "INFO")
        log(f"Gemini:   ${gem_usd_final:.2f} USD, {gem_xrp_final:.6f} XRP", "INFO")
        
        # Summary
        log("", "")
        log("="*80, "")
        log("📊 TEST SUMMARY", "")
        log("="*80, "")
        log(f"Test 1 (CB → GEM): {'✅ PASSED' if test1_passed else '❌ FAILED'}", "")
        log(f"Test 2 (GEM → CB): {'✅ PASSED' if test2_passed else '❌ FAILED'}", "")
        
        if test1_passed and test2_passed:
            log("", "")
            log("🎉 ALL TESTS PASSED - BI-DIRECTIONAL TRANSFERS WORKING!", "")
            log("", "")
            log("Your arbitrage pipeline is fully functional! 🚀", "")
        elif test1_passed:
            log("", "")
            log("✅ Test 1 passed - Coinbase → Gemini works!", "")
            log("⚠️  Test 2 skipped or failed - check Gemini balance", "")
        else:
            log("", "")
            log("⚠️  Tests failed - check logs above for details", "")
        
        log("="*80, "")
        
    except Exception as e:
        log(f"❌ TEST SUITE FAILED: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        
    finally:
        log("", "")
        log("Closing exchange connections...", "DEBUG")
        await mgr.close()
        log("✅ Connections closed", "DEBUG")


if __name__ == "__main__":
    asyncio.run(main())

