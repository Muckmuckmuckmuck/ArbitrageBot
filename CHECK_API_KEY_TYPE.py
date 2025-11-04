#!/usr/bin/env python3
"""
Diagnostic script to check Coinbase API key type and test authentication
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

async def test_api_key():
    """Test Coinbase API key and determine which API it works with"""
    
    api_key = os.getenv('COINBASE_API_KEY', '')
    secret_key = os.getenv('COINBASE_SECRET_KEY', '')
    passphrase = os.getenv('COINBASE_PASSPHRASE', '')
    
    if not api_key or not secret_key:
        print("❌ API keys not configured")
        return
    
    print("=" * 80)
    print("COINBASE API KEY DIAGNOSTIC")
    print("=" * 80)
    print(f"API Key: {api_key[:10]}...{api_key[-6:]}")
    print(f"Has Passphrase: {'Yes' if passphrase else 'No'}")
    print()
    
    # Test 1: Main Coinbase API (api.coinbase.com)
    print("TEST 1: Main Coinbase API (api.coinbase.com)")
    print("-" * 80)
    try:
        timestamp = str(int(time.time()))
        message = timestamp + 'GET' + '/v2/user'
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
            async with session.get('https://api.coinbase.com/v2/user', headers=headers) as response:
                if response.status == 200:
                    print("✅ SUCCESS: API key works with Main Coinbase API")
                    data = await response.json()
                    print(f"   User: {data.get('data', {}).get('name', 'Unknown')}")
                else:
                    print(f"❌ FAILED: Status {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print()
    
    # Test 2: Exchange API (api.exchange.coinbase.com)
    print("TEST 2: Exchange API (api.exchange.coinbase.com)")
    print("-" * 80)
    try:
        timestamp = str(int(time.time()))
        endpoint = '/accounts'
        message = timestamp + 'GET' + endpoint
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
            async with session.get('https://api.exchange.coinbase.com/accounts', headers=headers) as response:
                if response.status == 200:
                    print("✅ SUCCESS: API key works with Exchange API")
                    data = await response.json()
                    print(f"   Accounts found: {len(data) if isinstance(data, list) else 'N/A'}")
                else:
                    print(f"❌ FAILED: Status {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
                    if response.status == 401:
                        print("   ⚠️  This API key is NOT valid for Exchange API")
                        print("   💡 You need to create Exchange API keys from:")
                        print("      https://exchange.coinbase.com/settings/api")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print()
    print("=" * 80)
    print("TROUBLESHOOTING:")
    print("=" * 80)
    print("If Exchange API test failed with 401, check:")
    print("1. IP Whitelisting:")
    print("   - Go to Coinbase API settings")
    print("   - Check if IP whitelist is enabled")
    print("   - Add Railway's IP or disable whitelist")
    print()
    print("2. API Permissions:")
    print("   - Make sure 'Transfer' permission is enabled")
    print("   - Not just 'Trade' and 'View'")
    print()
    print("3. API Key Status:")
    print("   - Check if API key is active (not revoked)")
    print("   - Wait 48 hours if just created")
    print()
    print("4. If keys work with Main API but not Exchange API:")
    print("   - May need Exchange-specific keys")
    print("   - Or may need to use different endpoint")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_api_key())

