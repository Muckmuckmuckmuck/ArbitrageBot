#!/usr/bin/env python3
"""
Sell BTC to USDC on Coinbase
Simple script to convert BTC back to USDC
"""

import asyncio
import os
from dotenv import load_dotenv
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager

# Load environment variables
load_dotenv()

async def sell_btc():
    """Sell all BTC to USDC"""
    
    # Initialize exchange manager
    exchange_manager = CoinbaseGeminiExchangeManager()
    await exchange_manager.initialize()
    
    # Get balance
    balance = await exchange_manager.fetch_balance('coinbase')
    free_balance = balance.get('free', {})
    btc_balance = free_balance.get('BTC', 0)
    usdc_balance = free_balance.get('USDC', 0)
    
    print(f"Current balances:")
    print(f"   BTC: {btc_balance:.8f} BTC")
    print(f"   USDC: ${usdc_balance:.2f}")
    
    if btc_balance <= 0:
        print("\n✅ No BTC to sell")
        return
    
    # Get current price
    ticker = await exchange_manager.fetch_ticker('coinbase', 'BTC/USDC')
    current_price = ticker.get('bid') or ticker.get('last', 0)
    
    print(f"\nCurrent BTC/USDC price: ${current_price:.2f}")
    print(f"Estimated USDC received: ${btc_balance * current_price:.2f}")
    
    # Sell BTC for USDC (use 95% to leave buffer)
    sell_amount = btc_balance * 0.95
    
    print(f"\nSelling {sell_amount:.8f} BTC for USDC...")
    
    # Calculate limit price (slightly below bid to ensure fill)
    limit_price = current_price * 0.995
    
    print(f"Limit price: ${limit_price:.2f}")
    
    try:
        order = await exchange_manager.create_order(
            exchange_id='coinbase',
            symbol='BTC/USDC',
            order_type='limit',
            side='sell',
            amount=sell_amount,
            price=limit_price
        )
        
        order_id = order.get('id')
        print(f"\n✅ Order placed: {order_id}")
        print(f"   Selling {sell_amount:.8f} BTC @ ${limit_price:.2f}")
        
        # Wait for fill
        print("\nWaiting for order to fill...")
        max_wait = 30
        for i in range(max_wait):
            await asyncio.sleep(1)
            try:
                order_status = await exchange_manager.fetch_order('coinbase', order_id, 'BTC/USDC')
                status = order_status.get('status', 'unknown')
                
                if status in ['closed', 'filled']:
                    filled = order_status.get('filled', 0)
                    cost = order_status.get('cost', 0)
                    print(f"\n✅ Order filled!")
                    print(f"   Sold: {filled:.8f} BTC")
                    print(f"   Received: ${cost:.2f} USDC")
                    
                    # Verify balance
                    balance = await exchange_manager.fetch_balance('coinbase')
                    usdc_balance = balance.get('free', {}).get('USDC', 0)
                    btc_remaining = balance.get('free', {}).get('BTC', 0)
                    
                    print(f"\n✅ Updated balances:")
                    print(f"   USDC: ${usdc_balance:.2f}")
                    print(f"   BTC: {btc_remaining:.8f} BTC")
                    return
                elif status == 'canceled':
                    print("\n⚠️ Order was canceled")
                    return
                elif i % 5 == 0:
                    print(f"   Still waiting... ({i}s elapsed)")
            except Exception as e:
                print(f"   Error checking order: {e}")
        
        print("\n⚠️ Order didn't fill within timeout")
        print("   You may need to cancel it manually or wait longer")
        
    except Exception as e:
        print(f"\n❌ Error placing order: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(sell_btc())

