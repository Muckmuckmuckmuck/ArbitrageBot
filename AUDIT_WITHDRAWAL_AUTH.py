#!/usr/bin/env python3
"""
Audit script to compare working CCXT authentication vs our withdrawal implementation
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

async def test_authentication():
    """Test different authentication methods"""
    
    api_key = os.getenv('COINBASE_API_KEY', '')
    secret_key = os.getenv('COINBASE_SECRET_KEY', '')
    passphrase = os.getenv('COINBASE_PASSPHRASE', '')
    
    if not all([api_key, secret_key, passphrase]):
        print("❌ Missing API credentials")
        return
    
    print("=" * 80)
    print("AUDIT: Coinbase Authentication Comparison")
    print("=" * 80)
    print()
    
    # Test 1: Simple GET to verify keys work with main API
    print("TEST 1: Main Coinbase API (api.coinbase.com) - GET /v2/user")
    print("-" * 80)
    try:
        timestamp = str(int(time.time()))
        method = 'GET'
        path = '/v2/user'
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
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.coinbase.com/v2/user', headers=headers) as response:
                if response.status == 200:
                    print("✅ SUCCESS: Keys work with main API")
                    data = await response.json()
                    print(f"   User: {data.get('data', {}).get('name', 'Unknown')}")
                else:
                    print(f"❌ FAILED: Status {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print()
    
    # Test 2: Exchange API with same authentication
    print("TEST 2: Exchange API (api.exchange.coinbase.com) - GET /accounts")
    print("-" * 80)
    try:
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
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.exchange.coinbase.com/accounts', headers=headers) as response:
                if response.status == 200:
                    print("✅ SUCCESS: Same keys work with Exchange API!")
                    data = await response.json()
                    print(f"   Accounts: {len(data) if isinstance(data, list) else 'N/A'}")
                else:
                    print(f"❌ FAILED: Status {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
                    if response.status == 401:
                        print()
                        print("   🔍 DIAGNOSIS:")
                        print("   - Keys work with main API but NOT Exchange API")
                        print("   - This means keys are for main API only")
                        print("   - Need Exchange API keys OR different endpoint")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print()
    
    # Test 3: Withdrawal endpoint (POST)
    print("TEST 3: Exchange API Withdrawal Endpoint (POST /withdrawals/crypto)")
    print("-" * 80)
    print("   (This will fail with 400/401 but shows if auth works)")
    try:
        timestamp = str(int(time.time()))
        method = 'POST'
        path = '/withdrawals/crypto'
        
        # Minimal test body (will fail validation but shows auth)
        body = {
            'amount': '0.001',
            'currency': 'BTC',
            'crypto_address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'  # Genesis block address (safe to test)
        }
        body_json = json.dumps(body)
        
        message = timestamp + method + path + body_json
        secret = base64.b64decode(secret_key)
        signature = hmac.new(secret, message.encode('utf-8'), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')
        
        headers = {
            'CB-ACCESS-KEY': api_key,
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.exchange.coinbase.com/withdrawals/crypto', 
                                  headers=headers, data=body_json) as response:
                text = await response.text()
                if response.status == 401:
                    print(f"❌ AUTH FAILED: Status {response.status}")
                    print(f"   Response: {text[:200]}")
                    print()
                    print("   🔍 ISSUE: Authentication is failing")
                    print("   - Check signature generation")
                    print("   - Check passphrase format")
                    print("   - Check if keys have Exchange API access")
                elif response.status == 400:
                    print(f"⚠️  AUTH WORKS but validation failed: Status {response.status}")
                    print(f"   Response: {text[:200]}")
                    print()
                    print("   ✅ GOOD: Authentication passed!")
                    print("   ❌ Issue is with request body/parameters")
                else:
                    print(f"Status {response.status}: {text[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print("If Test 1 passes but Test 2 fails:")
    print("  → Keys are for main API only, not Exchange API")
    print()
    print("If Test 2 passes but Test 3 fails with 401:")
    print("  → Authentication format issue (signature/body)")
    print()
    print("If Test 3 fails with 400:")
    print("  → Authentication works! Issue is with request parameters")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_authentication())

