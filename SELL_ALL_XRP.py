#!/usr/bin/env python3
"""
SELL ALL XRP ON COINBASE
------------------------
Sell all accumulated XRP from the tests to recover money
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager


async def main():
    print("\n💰 SELLING ALL XRP ON COINBASE...")
    print("="*60)
    
    mgr = CoinbaseGeminiExchangeManager()
    
    try:
        await mgr.initialize()
        cb = mgr.exchanges['coinbase']
        
        # Get XRP balance
        bal = cb.fetch_balance()
        if hasattr(bal, '__await__'):
            bal = await bal
        
        xrp_balance = float(bal['free'].get('XRP', 0))
        usd_balance = float(bal['free'].get('USD', 0))
        
        print(f"Current balances:")
        print(f"  USD: ${usd_balance:.2f}")
        print(f"  XRP: {xrp_balance:.6f}")
        
        if xrp_balance < 0.01:
            print("\n✅ No XRP to sell")
            return
        
        # Get current XRP price
        ticker = cb.fetch_ticker('XRP/USD')
        if hasattr(ticker, '__await__'):
            ticker = await ticker
        
        price = float(ticker['last'])
        total_value = xrp_balance * price
        
        print(f"\nXRP Details:")
        print(f"  Current price: ${price:.4f}")
        print(f"  Total value: ${total_value:.2f}")
        print(f"  Amount to sell: {xrp_balance:.6f} XRP")
        
        # Confirm
        print(f"\n⚠️  About to sell {xrp_balance:.6f} XRP for ~${total_value:.2f}")
        print("This will convert all XRP back to USD")
        
        # Sell all XRP
        print(f"\n💸 Placing sell order...")
        
        order = cb.create_market_sell_order('XRP/USD', xrp_balance)
        if hasattr(order, '__await__'):
            order = await order
        
        order_id = order.get('id', 'unknown')
        print(f"✅ Sell order placed: {order_id}")
        print(f"   Status: {order.get('status', 'unknown')}")
        
        # Wait for order to fill
        print(f"\n⏳ Waiting for order to fill...")
        await asyncio.sleep(5)
        
        # Check final balances
        bal = cb.fetch_balance()
        if hasattr(bal, '__await__'):
            bal = await bal
        
        final_usd = float(bal['free'].get('USD', 0))
        final_xrp = float(bal['free'].get('XRP', 0))
        usd_gained = final_usd - usd_balance
        
        print(f"\n✅ SELL COMPLETE!")
        print(f"="*60)
        print(f"Final balances:")
        print(f"  USD: ${final_usd:.2f} (gained ${usd_gained:.2f})")
        print(f"  XRP: {final_xrp:.6f}")
        print(f"\n💰 Recovered ${usd_gained:.2f} from XRP sale")
        
        if final_xrp > 0.001:
            print(f"\n⚠️  Warning: {final_xrp:.6f} XRP remaining (dust amount)")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        await mgr.close()


if __name__ == "__main__":
    asyncio.run(main())
