#!/usr/bin/env python3
"""
Emergency script to sell ALL crypto on both exchanges and convert to USD
Run this LOCALLY (not on Railway) to immediately free up cash
"""

import ccxt
import asyncio
from coinbase_gemini_config import Config

async def sell_all_crypto():
    print("="*80)
    print("🚨 EMERGENCY: Selling ALL crypto to USD")
    print("="*80)
    
    # Initialize exchanges
    cb = ccxt.coinbase({
        'apiKey': Config.COINBASE_API_KEY,
        'secret': Config.COINBASE_SECRET_KEY,
        'enableRateLimit': True
    })
    
    gem = ccxt.gemini({
        'apiKey': Config.GEMINI_API_KEY,
        'secret': Config.GEMINI_SECRET_KEY,
        'enableRateLimit': True
    })
    
    cb.load_markets()
    gem.load_markets()
    
    total_value = 0
    orders_placed = []
    
    # COINBASE
    print("\n" + "="*80)
    print("📊 COINBASE")
    print("="*80)
    
    cb_balance = cb.fetch_balance()
    for currency, amount in cb_balance['free'].items():
        if amount > 0 and currency not in ['USD', 'USDT', 'USDC']:
            # Try both USD and USDC pairs
            for quote in ['USD', 'USDC']:
                try:
                    symbol = f"{currency}/{quote}"
                    if symbol in cb.markets:
                        ticker = cb.fetch_ticker(symbol)
                        current_price = ticker['bid']
                        value_usd = amount * current_price
                        total_value += value_usd
                        
                        print(f"\n🔴 {currency}: {amount:.6f} @ ${current_price:.2f} = ${value_usd:.2f}")
                        print(f"   Placing LIMIT SELL order...")
                        
                        try:
                            order = cb.create_limit_sell_order(symbol, amount, current_price)
                            print(f"   ✅ Order placed! ID: {order['id']}")
                            orders_placed.append({
                                'exchange': 'coinbase',
                                'symbol': symbol,
                                'amount': amount,
                                'price': current_price,
                                'value': value_usd,
                                'order_id': order['id']
                            })
                            break  # Successfully placed order
                        except Exception as e:
                            print(f"   ❌ Error placing order: {str(e)[:100]}")
                except Exception as e:
                    continue
    
    # GEMINI
    print("\n" + "="*80)
    print("📊 GEMINI")
    print("="*80)
    
    try:
        gem_balance = gem.fetch_balance()
        for currency, amount in gem_balance['free'].items():
            if amount > 0 and currency not in ['USD', 'USDT', 'USDC']:
                # Try both USD and USDC pairs
                for quote in ['USD', 'USDC']:
                    try:
                        symbol = f"{currency}/{quote}"
                        if symbol in gem.markets:
                            ticker = gem.fetch_ticker(symbol)
                            current_price = ticker['bid']
                            value_usd = amount * current_price
                            total_value += value_usd
                            
                            print(f"\n🔴 {currency}: {amount:.6f} @ ${current_price:.2f} = ${value_usd:.2f}")
                            print(f"   Placing LIMIT SELL order...")
                            
                            try:
                                order = gem.create_limit_sell_order(symbol, amount, current_price)
                                print(f"   ✅ Order placed! ID: {order['id']}")
                                orders_placed.append({
                                    'exchange': 'gemini',
                                    'symbol': symbol,
                                    'amount': amount,
                                    'price': current_price,
                                    'value': value_usd,
                                    'order_id': order['id']
                                })
                                break  # Successfully placed order
                            except Exception as e:
                                print(f"   ❌ Error placing order: {str(e)[:100]}")
                    except Exception as e:
                        continue
    except Exception as e:
        if 'master-keys are not-supported' in str(e):
            print(f"\n⚠️  Gemini API key is a 'Master' key - need 'Primary' key to trade!")
            print(f"   Go to Gemini → Settings → API → Create new 'Primary' API key")
        else:
            print(f"❌ Error fetching Gemini balance: {str(e)}")
    
    # Summary
    print("\n" + "="*80)
    print("📋 SUMMARY")
    print("="*80)
    print(f"Total value to be converted to USD: ${total_value:.2f}")
    print(f"Orders placed: {len(orders_placed)}")
    
    if orders_placed:
        print("\n📝 Orders:")
        for order in orders_placed:
            print(f"  [{order['exchange']}] {order['symbol']}: {order['amount']:.6f} @ ${order['price']:.2f} = ${order['value']:.2f}")
        print(f"\n💰 Once all orders fill, you'll have ~${total_value:.2f} USD to trade!")
    else:
        print("\n⚠️  No orders placed. Check if you have a valid API key.")
    
    print("="*80)

if __name__ == "__main__":
    asyncio.run(sell_all_crypto())

