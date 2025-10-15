#!/usr/bin/env python3
"""
Quick script to sell XRP on Coinbase from the test
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager


async def main():
    print("\n🔄 Selling XRP on Coinbase...")
    
    mgr = CoinbaseGeminiExchangeManager()
    
    try:
        await mgr.initialize()
        cb = mgr.exchanges['coinbase']
        
        # Get XRP balance
        bal = cb.fetch_balance()
        if hasattr(bal, '__await__'):
            bal = await bal
        
        xrp_balance = float(bal['free'].get('XRP', 0))
        print(f"XRP balance: {xrp_balance:.6f}")
        
        if xrp_balance < 0.01:
            print("No XRP to sell")
            return
        
        # Get price
        ticker = cb.fetch_ticker('XRP/USD')
        if hasattr(ticker, '__await__'):
            ticker = await ticker
        
        price = float(ticker['last'])
        print(f"XRP price: ${price:.4f}")
        print(f"Will sell: {xrp_balance:.6f} XRP for ~${xrp_balance * price:.2f}")
        
        # Sell
        order = cb.create_market_sell_order('XRP/USD', xrp_balance)
        if hasattr(order, '__await__'):
            order = await order
        
        print(f"✅ Sell order placed: {order.get('id', 'unknown')}")
        
        await asyncio.sleep(3)
        
        # Check balance
        bal = cb.fetch_balance()
        if hasattr(bal, '__await__'):
            bal = await bal
        
        usd_balance = float(bal['free'].get('USD', 0))
        xrp_balance = float(bal['free'].get('XRP', 0))
        
        print(f"\n✅ Done!")
        print(f"USD balance: ${usd_balance:.2f}")
        print(f"XRP balance: {xrp_balance:.6f}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        await mgr.close()


if __name__ == "__main__":
    asyncio.run(main())

