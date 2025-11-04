#!/usr/bin/env python3
"""
Test Exchange API authentication to see what works
"""

import asyncio
import aiohttp
import hmac
import hashlib
import base64
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_exchange_auth():
    """Test different authentication formats"""
    
    api_key = os.getenv('COINBASE_API_KEY', '')
    secret_key = os.getenv('COINBASE_SECRET_KEY', '')
    passphrase = os.getenv('COINBASE_PASSPHRASE', '')
    
    if not all([api_key, secret_key, passphrase]):
        print("❌ Missing credentials")
        return
    
    print("=" * 80)
    print("TESTING EXCHANGE API AUTHENTICATION")
    print("=" * 80)
    print()
    
    # Test 1: Simple GET to /accounts (should work if auth is correct)
    print("TEST 1: GET /accounts (Simple authenticated request)")
    print("-" * 80)
    
    timestamp = str(int(time.time()))
    method = 'GET'
    path = '/accounts'
    message = timestamp + method + path
    
    secret = base64.b64decode(secret_key)
    signature = hmac.new(secret, message.encode('utf-8'), hashlib.sha256)
    signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')
    
    headers = {
        'CB-ACCESS-KEY': api_key,
        'CB-ACCESS-SIGN': signature_b64,
        'CB-ACCESS-TIMESTAMP': timestamp,
        'CB-ACCESS-PASSPHRASE': passphrase,  # Plain text
        'Content-Type': 'application/json'
    }
    
    print(f"Timestamp: {timestamp}")
    print(f"Method: {method}")
    print(f"Path: {path}")
    print(f"Message: {message}")
    print(f"Signature (first 20 chars): {signature_b64[:20]}...")
    print()
    
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.exchange.coinbase.com/accounts', headers=headers) as response:
            text = await response.text()
            print(f"Status: {response.status}")
            print(f"Response: {text[:300]}")
            
            if response.status == 200:
                print("✅ SUCCESS! Authentication works!")
            elif response.status == 401:
                print("❌ Authentication failed")
                print()
                print("Trying alternative: base64 encoded passphrase...")
                
                # Try with base64 encoded passphrase
                passphrase_b64 = base64.b64encode(passphrase.encode('utf-8')).decode('utf-8')
                headers2 = headers.copy()
                headers2['CB-ACCESS-PASSPHRASE'] = passphrase_b64
                
                async with session.get('https://api.exchange.coinbase.com/accounts', headers=headers2) as response2:
                    text2 = await response2.text()
                    print(f"Status with base64 passphrase: {response2.status}")
                    print(f"Response: {text2[:300]}")
            else:
                print(f"Unexpected status: {response.status}")

if __name__ == "__main__":
    asyncio.run(test_exchange_auth())

