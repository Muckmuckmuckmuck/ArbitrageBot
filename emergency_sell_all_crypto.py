#!/usr/bin/env python3
"""
Emergency script to sell ALL stuck crypto on Gemini
"""

import ccxt
from coinbase_gemini_config import Config

print("="*80)
print("🚨 EMERGENCY: Selling ALL stuck crypto on Gemini")
print("="*80)

# Initialize Gemini
gem = ccxt.gemini({
    'apiKey': Config.GEMINI_API_KEY,
    'secret': Config.GEMINI_SECRET_KEY,
    'enableRateLimit': True
})

gem.load_markets()

# Get balance
balance = gem.fetch_balance()

# Find all crypto holdings (excluding USD, USDT, USDC)
crypto_holdings = {}
for currency, amount in balance['free'].items():
    if amount > 0 and currency not in ['USD', 'USDT', 'USDC']:
        crypto_holdings[currency] = amount

print(f"\n📊 Found {len(crypto_holdings)} crypto holdings on Gemini:")
print("-"*80)

total_value_usd = 0

for currency, amount in crypto_holdings.items():
    # Try both USD and USDC pairs
    symbol = None
    ticker = None
    
    for quote in ['USD', 'USDC']:
        try:
            test_symbol = f"{currency}/{quote}"
            if test_symbol in gem.markets:
                ticker = gem.fetch_ticker(test_symbol)
                symbol = test_symbol
                break
        except:
            continue
    
    if ticker and symbol:
        current_price = ticker['bid']
        value_usd = amount * current_price
        total_value_usd += value_usd
        
        print(f"  {currency:8s} | Amount: {amount:12.6f} | Price: ${current_price:10.2f} | Value: ${value_usd:10.2f}")
        
        # Ask user if they want to sell
        print(f"\n  🔴 Sell {amount:.6f} {currency} @ ${current_price:.2f}?")
        response = input("     Type 'yes' to sell, anything else to skip: ").strip().lower()
        
        if response == 'yes':
            try:
                print(f"     Placing limit sell order...")
                order = gem.create_limit_sell_order(symbol, amount, current_price)
                print(f"     ✅ Order placed! ID: {order['id']}")
                print(f"     💰 Will receive ~${value_usd:.2f} USD")
            except Exception as e:
                print(f"     ❌ Error: {str(e)}")
        else:
            print(f"     ⏭️  Skipped")
        
        print("-"*80)
    else:
        print(f"  {currency:8s} | Amount: {amount:12.6f} | ❌ No market found")
        print("-"*80)

print(f"\n💰 Total value of crypto on Gemini: ${total_value_usd:.2f}")
print("="*80)

