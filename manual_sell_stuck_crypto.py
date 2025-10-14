#!/usr/bin/env python3
"""
Manual script to sell ALL stuck crypto on Coinbase
Run this to immediately free up your stuck funds
"""

import ccxt
import asyncio
from coinbase_gemini_config import Config

async def sell_all_crypto_on_coinbase():
    print("="*80)
    print("🧹 MANUAL CLEANUP: Selling ALL crypto on Coinbase")
    print("="*80)
    
    # Initialize Coinbase
    cb = ccxt.coinbase({
        'apiKey': Config.COINBASE_API_KEY,
        'secret': Config.COINBASE_SECRET_KEY,
        'enableRateLimit': True
    })
    
    cb.load_markets()
    
    # Get balance
    balance = cb.fetch_balance()
    
    # Find all crypto holdings
    total_freed = 0
    orders_placed = []
    
    print("\n📊 Checking Coinbase balances...")
    
    for currency, amount in balance['free'].items():
        if currency in ['USD', 'USDT', 'USDC'] or amount <= 0:
            continue
        
        print(f"\n💰 Found: {amount:.6f} {currency}")
        
        # Try to sell for USD, USDC, or USDT
        sold = False
        for quote in ['USD', 'USDC', 'USDT']:
            try:
                symbol = f"{currency}/{quote}"
                
                if symbol not in cb.markets:
                    continue
                
                # Get current price
                ticker = cb.fetch_ticker(symbol)
                bid_price = ticker.get('bid') or ticker.get('last')
                
                if not bid_price:
                    continue
                
                value_usd = amount * bid_price
                print(f"   Price: ${bid_price:.6f}")
                print(f"   Value: ${value_usd:.2f}")
                
                if value_usd < 0.50:
                    print(f"   ⏭️  Skipping (too small)")
                    sold = True
                    break
                
                # Place limit sell order (maker fees)
                print(f"   🔄 Placing limit sell order...")
                order = cb.create_limit_sell_order(symbol, amount, bid_price)
                
                print(f"   ✅ Order placed!")
                print(f"   Order ID: {order['id']}")
                
                orders_placed.append({
                    'currency': currency,
                    'amount': amount,
                    'price': bid_price,
                    'value': value_usd,
                    'order_id': order['id']
                })
                
                total_freed += value_usd
                sold = True
                break
                
            except Exception as e:
                print(f"   ⚠️  Error with {symbol}: {str(e)[:50]}")
                continue
        
        if not sold:
            print(f"   ❌ Could not sell {currency} (no valid market found)")
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Orders placed: {len(orders_placed)}")
    print(f"Total value: ${total_freed:.2f}")
    print("\nOrders:")
    for order in orders_placed:
        print(f"   • Sell {order['amount']:.6f} {order['currency']} @ ${order['price']:.6f} = ${order['value']:.2f}")
    print("="*80)
    print("\n✅ All orders placed! They will fill soon and free up USD for trading.")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(sell_all_crypto_on_coinbase())

