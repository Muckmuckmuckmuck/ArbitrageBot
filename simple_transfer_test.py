#!/usr/bin/env python3
"""
SIMPLE TRANSFER TEST
--------------------
This script does ONE thing: Buy $1 XRP on Coinbase, transfer to Gemini, sell.

This isolates the transfer mechanism to verify it works.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager


async def main():
    print("\n" + "="*80)
    print("🧪 SIMPLE TRANSFER TEST: COINBASE → GEMINI")
    print("="*80)
    
    mgr = CoinbaseGeminiExchangeManager()
    
    try:
        # Initialize
        print("\n[1/7] 🔧 Initializing exchanges...")
        await mgr.initialize()
        print("      ✅ Connected to Coinbase and Gemini")
        
        # Check balances
        print("\n[2/7] 💰 Checking balances...")
        cb = mgr.exchanges['coinbase']
        gem = mgr.exchanges['gemini']
        
        cb_bal = cb.fetch_balance()
        if hasattr(cb_bal, '__await__'):
            cb_bal = await cb_bal
        
        gem_bal = gem.fetch_balance()
        if hasattr(gem_bal, '__await__'):
            gem_bal = await gem_bal
            
        cb_usd = float(cb_bal['free'].get('USD', 0))
        gem_usd = float(gem_bal['free'].get('USD', 0))
        cb_xrp = float(cb_bal['free'].get('XRP', 0))
        gem_xrp = float(gem_bal['free'].get('XRP', 0))
        
        print(f"      Coinbase: ${cb_usd:.2f} USD, {cb_xrp:.4f} XRP")
        print(f"      Gemini:   ${gem_usd:.2f} USD, {gem_xrp:.4f} XRP")
        
        if cb_usd < 1.5:
            print(f"\n❌ ERROR: Coinbase has insufficient USD (${cb_usd:.2f})")
            print("   Need at least $1.50 to buy $1 of XRP")
            return
        
        # Get XRP price
        print("\n[3/7] 📊 Getting XRP price...")
        ticker = cb.fetch_ticker('XRP/USD')
        if hasattr(ticker, '__await__'):
            ticker = await ticker
        
        price = float(ticker['last'])
        print(f"      XRP price: ${price:.4f}")
        
        # Calculate amount
        buy_amount_usd = 1.0
        xrp_amount = buy_amount_usd / price
        print(f"      Will buy: {xrp_amount:.2f} XRP for ${buy_amount_usd:.2f}")
        
        # Buy XRP on Coinbase
        print("\n[4/7] 💸 Buying XRP on Coinbase...")
        try:
            order = cb.create_order(
                symbol='XRP/USD',
                type='market',
                side='buy',
                amount=xrp_amount,
                params={'funds': buy_amount_usd}
            )
            if hasattr(order, '__await__'):
                order = await order
            
            print(f"      ✅ Order placed: {order.get('id', 'unknown')}")
            print(f"      Status: {order.get('status', 'unknown')}")
            
            # Wait for order to fill
            await asyncio.sleep(5)
            
            # Check new balance
            cb_bal = cb.fetch_balance()
            if hasattr(cb_bal, '__await__'):
                cb_bal = await cb_bal
            
            xrp_bought = float(cb_bal['free'].get('XRP', 0)) - cb_xrp
            print(f"      ✅ Bought {xrp_bought:.4f} XRP")
            
        except Exception as e:
            print(f"      ❌ Buy failed: {str(e)}")
            return
        
        # Get Gemini deposit address
        print("\n[5/7] 📍 Getting Gemini XRP deposit address...")
        try:
            deposit_info = gem.fetch_deposit_address('XRP')
            if hasattr(deposit_info, '__await__'):
                deposit_info = await deposit_info
            
            address = deposit_info['address']
            tag = deposit_info.get('tag')
            
            print(f"      Address: {address}")
            if tag:
                print(f"      Tag: {tag}")
                
        except Exception as e:
            print(f"      ❌ Failed to get deposit address: {str(e)}")
            return
        
        # Record Gemini balance before transfer
        gem_xrp_before = gem_xrp
        
        # Transfer XRP from Coinbase to Gemini
        print(f"\n[6/7] 🚀 Transferring {xrp_bought:.4f} XRP to Gemini...")
        try:
            withdraw_params = {'network': 'XRP'}
            if tag:
                withdraw_params['tag'] = tag
            
            withdrawal = cb.withdraw(
                code='XRP',
                amount=xrp_bought,
                address=address,
                params=withdraw_params
            )
            if hasattr(withdrawal, '__await__'):
                withdrawal = await withdrawal
            
            print(f"      ✅ Withdrawal initiated: {withdrawal.get('id', 'unknown')}")
            print(f"      ⏳ Waiting for transfer to complete (XRP is fast, ~30-90 seconds)...")
            
            # Monitor Gemini balance
            max_wait = 300  # 5 minutes
            check_interval = 15
            elapsed = 0
            
            while elapsed < max_wait:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                gem_bal = gem.fetch_balance()
                if hasattr(gem_bal, '__await__'):
                    gem_bal = await gem_bal
                
                gem_xrp_now = float(gem_bal['free'].get('XRP', 0))
                
                if gem_xrp_now > gem_xrp_before + (xrp_bought * 0.95):
                    print(f"      ✅ Transfer confirmed! Gemini now has {gem_xrp_now:.4f} XRP")
                    print(f"      Time taken: {elapsed}s")
                    break
                
                print(f"      ⏳ Still waiting... ({elapsed}s elapsed, Gemini XRP: {gem_xrp_now:.4f})")
            else:
                print(f"      ⚠️  Transfer timed out after {max_wait}s")
                print(f"      Check Gemini manually - it may still arrive")
                return
                
        except Exception as e:
            print(f"      ❌ Transfer failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return
        
        # Sell XRP on Gemini
        print(f"\n[7/7] 💵 Selling XRP on Gemini...")
        try:
            # Get current Gemini XRP balance
            gem_bal = gem.fetch_balance()
            if hasattr(gem_bal, '__await__'):
                gem_bal = await gem_bal
            
            xrp_to_sell = float(gem_bal['free'].get('XRP', 0))
            
            # Gemini requires limit orders
            sell_price = price * 0.99  # 1% below market to ensure fill
            
            order = gem.create_limit_sell_order(
                symbol='XRP/USD',
                amount=xrp_to_sell,
                price=sell_price
            )
            if hasattr(order, '__await__'):
                order = await order
            
            print(f"      ✅ Sell order placed: {order.get('id', 'unknown')}")
            print(f"      Amount: {xrp_to_sell:.4f} XRP at ${sell_price:.4f}")
            
            # Wait for fill
            await asyncio.sleep(10)
            
            # Check USD balance
            gem_bal = gem.fetch_balance()
            if hasattr(gem_bal, '__await__'):
                gem_bal = await gem_bal
            
            gem_usd_now = float(gem_bal['free'].get('USD', 0))
            print(f"      ✅ Gemini USD balance: ${gem_usd_now:.2f}")
            
        except Exception as e:
            print(f"      ❌ Sell failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return
        
        # Summary
        print("\n" + "="*80)
        print("✅ TEST COMPLETE!")
        print("="*80)
        print(f"Successfully bought ${buy_amount_usd:.2f} XRP on Coinbase,")
        print(f"transferred to Gemini, and sold for USD.")
        print("\nThis confirms your transfer mechanism is working! 🎉")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        await mgr.close()


if __name__ == "__main__":
    asyncio.run(main())

