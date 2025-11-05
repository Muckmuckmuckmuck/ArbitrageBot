#!/usr/bin/env python3
"""
Simple script to buy $2 of BTC with USDC on Coinbase
"""

import ccxt
import os
import logging
from dotenv import load_dotenv

# Suppress all logging except critical errors
logging.getLogger('ccxt').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

# Load credentials
load_dotenv()
load_dotenv('.env.railway')

# Get credentials
api_key = os.getenv('COINBASE_API_KEY')
secret_key = os.getenv('COINBASE_SECRET_KEY')
passphrase = os.getenv('COINBASE_PASSPHRASE', '')

# Initialize Coinbase
coinbase = ccxt.coinbase({
    'apiKey': api_key,
    'secret': secret_key,
    'password': passphrase,
    'options': {
        'advanced': True  # Advanced Trade API
    },
    'enableRateLimit': True,
})

# Load markets
coinbase.load_markets()

# Get BTC/USDC price
symbol = 'BTC/USDC'
ticker = coinbase.fetch_ticker(symbol)
btc_price = ticker['ask']

# Calculate amount for $2
usd_amount = 2.0
btc_amount = usd_amount / btc_price

# Set limit price (1% above ask to ensure fill)
buy_price = btc_price * 1.01

print(f"Buying {btc_amount:.8f} BTC for ${usd_amount:.2f} USDC")
print(f"Price: ${buy_price:.2f} per BTC")

# Place order
order = coinbase.create_order(
    symbol=symbol,
    type='limit',
    side='buy',
    amount=btc_amount,
    price=buy_price
)

print(f"\n✅ Order placed!")
print(f"Order ID: {order['id']}")
print(f"Status: {order['status']}")
print(f"Amount: {order['amount']} BTC")
print(f"Price: ${order['price']}")

