#!/usr/bin/env python3
"""
Simple script to buy $2 of BTC with USDC on Coinbase
ONLY shows BTC purchase logging - nothing else
"""

import ccxt
import os
import sys
import logging
from dotenv import load_dotenv

# Completely suppress ALL logging
logging.disable(logging.CRITICAL)
for logger_name in ['ccxt', 'urllib3', 'requests']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    logging.getLogger(logger_name).disabled = True

# Suppress stdout/stderr from ccxt
class NullWriter:
    def write(self, s): pass
    def flush(self): pass

# Load credentials
load_dotenv()
load_dotenv('.env.railway')

# Get credentials
api_key = os.getenv('COINBASE_API_KEY')
secret_key = os.getenv('COINBASE_SECRET_KEY')
passphrase = os.getenv('COINBASE_PASSPHRASE', '')

# Initialize Coinbase - suppress verbose output
coinbase = ccxt.coinbase({
    'apiKey': api_key,
    'secret': secret_key,
    'password': passphrase,
    'options': {
        'advanced': True
    },
    'enableRateLimit': True,
    'verbose': False,
})

# Load markets silently
coinbase.load_markets()

# Get BTC/USDC price
symbol = 'BTC/USDC'
ticker = coinbase.fetch_ticker(symbol)
btc_price = ticker['ask']

# Calculate amount for $2
usd_amount = 2.0
btc_amount = usd_amount / btc_price
buy_price = btc_price * 1.01

# BTC PURCHASE LOGGING ONLY
print(f"BTC Purchase: Buying {btc_amount:.8f} BTC for ${usd_amount:.2f} USDC")
print(f"BTC Purchase: Price ${buy_price:.2f} per BTC")

# Place order
order = coinbase.create_order(
    symbol=symbol,
    type='limit',
    side='buy',
    amount=btc_amount,
    price=buy_price
)

# BTC PURCHASE RESULT ONLY
print(f"BTC Purchase: Order placed - ID: {order['id']}")
print(f"BTC Purchase: Status: {order['status']}")
print(f"BTC Purchase: Amount: {order['amount']} BTC")
print(f"BTC Purchase: Price: ${order['price']}")

