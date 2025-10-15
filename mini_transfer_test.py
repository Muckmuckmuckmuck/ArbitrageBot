#!/usr/bin/env python3
"""
MINI TRANSFER TEST - Coinbase to Gemini
----------------------------------------
This is a simple test to verify crypto transfers work.

Test: Buy $0.50 of XRP on Coinbase → Transfer to Gemini

This script has detailed logging at every step.
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


async def main():
    log("="*80, "")
    log("🧪 MINI TRANSFER TEST: COINBASE → GEMINI", "")
    log("="*80, "")
    log("Test: Buy $0.50 XRP on Coinbase, transfer to Gemini", "")
    log("", "")
    
    mgr = CoinbaseGeminiExchangeManager()
    
    try:
        # Step 1: Initialize
        log("STEP 1/6: Initializing exchanges...", "INFO")
        await mgr.initialize()
        log("✅ Exchanges initialized successfully", "INFO")
        
        cb = mgr.exchanges['coinbase']
        gem = mgr.exchanges['gemini']
        
        # Step 2: Check initial balances
        log("", "")
        log("STEP 2/6: Checking initial balances...", "INFO")
        
        cb_bal = cb.fetch_balance()
        if hasattr(cb_bal, '__await__'):
            cb_bal = await cb_bal
        
        gem_bal = gem.fetch_balance()
        if hasattr(gem_bal, '__await__'):
            gem_bal = await gem_bal
        
        cb_usd = float(cb_bal['free'].get('USD', 0))
        cb_xrp = float(cb_bal['free'].get('XRP', 0))
        gem_usd = float(gem_bal['free'].get('USD', 0))
        gem_xrp = float(gem_bal['free'].get('XRP', 0))
        
        log(f"Coinbase: ${cb_usd:.2f} USD, {cb_xrp:.6f} XRP", "INFO")
        log(f"Gemini:   ${gem_usd:.2f} USD, {gem_xrp:.6f} XRP", "INFO")
        
        if cb_usd < 1.0:
            log(f"❌ ERROR: Coinbase has insufficient USD (${cb_usd:.2f})", "ERROR")
            log("Need at least $1.00 to buy $0.50 of XRP", "ERROR")
            return
        
        log("✅ Sufficient balance on Coinbase", "INFO")
        
        # Step 3: Get XRP price and calculate amount
        log("", "")
        log("STEP 3/6: Getting XRP price...", "INFO")
        
        ticker = cb.fetch_ticker('XRP/USD')
        if hasattr(ticker, '__await__'):
            ticker = await ticker
        
        price = float(ticker['last'])
        log(f"Current XRP price: ${price:.4f}", "INFO")
        
        buy_amount_usd = 0.50  # $0.50 test
        xrp_amount = buy_amount_usd / price
        log(f"Will buy: {xrp_amount:.4f} XRP for ${buy_amount_usd:.2f}", "INFO")
        
        # Step 4: Buy XRP on Coinbase
        log("", "")
        log("STEP 4/6: Buying XRP on Coinbase...", "INFO")
        
        try:
            log(f"Placing market buy order for {xrp_amount:.4f} XRP...", "DEBUG")
            
            # Coinbase requires price for market buy orders
            order = cb.create_order(
                symbol='XRP/USD',
                type='market',
                side='buy',
                amount=xrp_amount,
                price=price  # Required by Coinbase
            )
            if hasattr(order, '__await__'):
                order = await order
            
            order_id = order.get('id', 'unknown')
            order_status = order.get('status', 'unknown')
            
            log(f"✅ Order placed successfully", "INFO")
            log(f"   Order ID: {order_id}", "DEBUG")
            log(f"   Status: {order_status}", "DEBUG")
            
            # Wait for order to fill
            log("Waiting 5 seconds for order to fill...", "DEBUG")
            await asyncio.sleep(5)
            
            # Check new balance
            cb_bal = cb.fetch_balance()
            if hasattr(cb_bal, '__await__'):
                cb_bal = await cb_bal
            
            cb_xrp_now = float(cb_bal['free'].get('XRP', 0))
            xrp_bought = cb_xrp_now - cb_xrp
            
            log(f"✅ Purchase confirmed!", "INFO")
            log(f"   XRP bought: {xrp_bought:.6f}", "INFO")
            log(f"   Coinbase XRP balance: {cb_xrp_now:.6f}", "INFO")
            
            if xrp_bought < 0.1:
                log(f"⚠️  WARNING: Very small amount bought ({xrp_bought:.6f} XRP)", "WARN")
                log("This might not be enough to transfer (min transfer limits)", "WARN")
                return
            
        except Exception as e:
            log(f"❌ Buy failed: {str(e)}", "ERROR")
            import traceback
            log("Full traceback:", "ERROR")
            traceback.print_exc()
            return
        
        # Step 5: Get Gemini deposit address
        log("", "")
        log("STEP 5/6: Getting Gemini XRP deposit address...", "INFO")
        
        try:
            log("Fetching deposit address from Gemini...", "DEBUG")
            
            deposit_info = gem.fetch_deposit_address('XRP')
            if hasattr(deposit_info, '__await__'):
                deposit_info = await deposit_info
            
            address = deposit_info['address']
            tag = deposit_info.get('tag')
            
            log(f"✅ Deposit address retrieved", "INFO")
            log(f"   Address: {address}", "DEBUG")
            if tag:
                log(f"   Tag: {tag}", "DEBUG")
            else:
                log(f"   Tag: None", "DEBUG")
            
        except Exception as e:
            log(f"❌ Failed to get deposit address: {str(e)}", "ERROR")
            import traceback
            log("Full traceback:", "ERROR")
            traceback.print_exc()
            return
        
        # Step 6: Transfer XRP from Coinbase to Gemini
        log("", "")
        log("STEP 6/6: Transferring XRP from Coinbase to Gemini...", "INFO")
        
        try:
            log(f"Initiating withdrawal of {xrp_bought:.6f} XRP...", "DEBUG")
            log(f"   From: Coinbase", "DEBUG")
            log(f"   To: {address}", "DEBUG")
            if tag:
                log(f"   Tag: {tag}", "DEBUG")
            
            withdraw_params = {'network': 'XRP'}
            if tag:
                withdraw_params['tag'] = tag
            
            log(f"Withdrawal params: {withdraw_params}", "DEBUG")
            
            withdrawal = cb.withdraw(
                code='XRP',
                amount=xrp_bought,
                address=address,
                params=withdraw_params
            )
            if hasattr(withdrawal, '__await__'):
                withdrawal = await withdrawal
            
            withdrawal_id = withdrawal.get('id', 'unknown')
            withdrawal_status = withdrawal.get('status', 'unknown')
            
            log(f"✅ Withdrawal initiated successfully!", "INFO")
            log(f"   Withdrawal ID: {withdrawal_id}", "INFO")
            log(f"   Status: {withdrawal_status}", "INFO")
            log(f"   Amount: {xrp_bought:.6f} XRP", "INFO")
            
            # Monitor Gemini balance
            log("", "")
            log("⏳ Monitoring Gemini balance for incoming XRP...", "INFO")
            log("   (XRP transfers typically take 30-120 seconds)", "INFO")
            
            max_wait = 300  # 5 minutes
            check_interval = 15  # Check every 15 seconds
            elapsed = 0
            
            while elapsed < max_wait:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                gem_bal = gem.fetch_balance()
                if hasattr(gem_bal, '__await__'):
                    gem_bal = await gem_bal
                
                gem_xrp_now = float(gem_bal['free'].get('XRP', 0))
                
                log(f"   [{elapsed}s] Gemini XRP balance: {gem_xrp_now:.6f} (was {gem_xrp:.6f})", "DEBUG")
                
                # Check if transfer completed (95% of amount to account for fees)
                if gem_xrp_now > gem_xrp + (xrp_bought * 0.95):
                    received = gem_xrp_now - gem_xrp
                    log("", "")
                    log(f"✅ TRANSFER CONFIRMED!", "INFO")
                    log(f"   Sent: {xrp_bought:.6f} XRP", "INFO")
                    log(f"   Received: {received:.6f} XRP", "INFO")
                    log(f"   Time taken: {elapsed} seconds", "INFO")
                    log(f"   Gemini balance: {gem_xrp_now:.6f} XRP", "INFO")
                    
                    # Calculate any transfer fee
                    if received < xrp_bought:
                        fee = xrp_bought - received
                        fee_pct = (fee / xrp_bought) * 100
                        log(f"   Transfer fee: {fee:.6f} XRP ({fee_pct:.2f}%)", "INFO")
                    
                    break
            else:
                log("", "")
                log(f"⚠️  Transfer not confirmed after {max_wait}s", "WARN")
                log("   This doesn't mean it failed - XRP transfers can take longer", "WARN")
                log("   Check Gemini manually in a few minutes", "WARN")
                log(f"   Withdrawal ID: {withdrawal_id}", "INFO")
                return
            
        except Exception as e:
            log(f"❌ Transfer failed: {str(e)}", "ERROR")
            import traceback
            log("Full traceback:", "ERROR")
            traceback.print_exc()
            return
        
        # Success summary
        log("", "")
        log("="*80, "")
        log("🎉 TEST COMPLETE - SUCCESS!", "")
        log("="*80, "")
        log("Summary:", "INFO")
        log(f"  1. Bought {xrp_bought:.6f} XRP on Coinbase for ${buy_amount_usd:.2f}", "INFO")
        log(f"  2. Transferred to Gemini (took {elapsed}s)", "INFO")
        log(f"  3. Gemini received {gem_xrp_now - gem_xrp:.6f} XRP", "INFO")
        log("", "")
        log("✅ TRANSFER MECHANISM IS WORKING!", "")
        log("="*80, "")
        
    except Exception as e:
        log("", "")
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        import traceback
        log("Full traceback:", "ERROR")
        traceback.print_exc()
        
    finally:
        log("", "")
        log("Closing exchange connections...", "DEBUG")
        await mgr.close()
        log("✅ Connections closed", "DEBUG")


if __name__ == "__main__":
    asyncio.run(main())

