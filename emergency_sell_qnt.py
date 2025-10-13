#!/usr/bin/env python3
"""
Emergency script to sell stuck QNT on Gemini
"""

import ccxt
from coinbase_gemini_config import Config

print("="*80)
print("🚨 EMERGENCY: Selling stuck QNT on Gemini")
print("="*80)

# Initialize Gemini
gem = ccxt.gemini({
    'apiKey': Config.GEMINI_API_KEY,
    'secret': Config.GEMINI_SECRET_KEY,
    'enableRateLimit': True
})

gem.load_markets()

# Get QNT balance
balance = gem.fetch_balance()
qnt_amount = balance['free'].get('QNT', 0)

print(f"\nQNT on Gemini: {qnt_amount:.6f}")

if qnt_amount > 0:
    # Get current price
    ticker = gem.fetch_ticker('QNT/USD')
    current_price = ticker['bid']  # Use bid for selling
    
    print(f"Current QNT price: ${current_price:.2f}")
    print(f"Value: ${qnt_amount * current_price:.2f}")
    
    # Place limit sell order (maker fees)
    print(f"\nPlacing limit sell order...")
    print(f"  Amount: {qnt_amount:.6f} QNT")
    print(f"  Price: ${current_price:.2f}")
    
    try:
        order = gem.create_limit_sell_order('QNT/USD', qnt_amount, current_price)
        print(f"\n✅ Order placed successfully!")
        print(f"Order ID: {order['id']}")
        print(f"Status: {order['status']}")
        print(f"\n💰 Will receive ~${qnt_amount * current_price:.2f} USD")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"\nTrying market order...")
        # Gemini only allows limit orders, so this will fail
        print("❌ Gemini only supports limit orders")
else:
    print("\n✅ No QNT found on Gemini")

print("="*80)
