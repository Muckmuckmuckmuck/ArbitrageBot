# 🔍 Coinbase Withdrawal - Final Analysis

## Current Situation

### ✅ What Works
- **Trading**: Purchases work perfectly on `api.coinbase.com` (Main API)
- **Authentication**: Our API keys authenticate successfully for trading
- **Balance Fetching**: Can read balances from Coinbase

### ❌ What Doesn't Work
- **External Withdrawals**: Both Main API and Exchange API return 401 errors
- **Main API** (`/v2/accounts/{account_id}/transactions`): Returns 401 Unauthorized
- **Exchange API** (`/withdrawals/crypto`): Returns 401 "Invalid API Key"

## Root Cause Analysis

### The Problem
Coinbase has **TWO separate APIs**:

1. **Main Coinbase API** (`api.coinbase.com`)
   - Used for: Trading, balance checking, Coinbase-to-Coinbase transfers
   - Your keys work here ✅
   - Endpoint: `/v2/accounts/{account_id}/transactions`
   - Purpose: "Send Money" API (primarily for Coinbase accounts)

2. **Coinbase Exchange API** (`api.exchange.coinbase.com`)
   - Used for: External crypto withdrawals, advanced trading
   - Your keys DON'T work here ❌
   - Endpoint: `/withdrawals/crypto`
   - Purpose: External crypto withdrawals

### Why 401 Errors Occur

1. **Main API** (`/v2/accounts/{account_id}/transactions`):
   - Returns 401 even with valid keys
   - Likely because this endpoint is **restricted** to Coinbase-to-Coinbase transfers only
   - External addresses may not be supported by this endpoint

2. **Exchange API** (`/withdrawals/crypto`):
   - Returns 401 "Invalid API Key"
   - **Requires separate Exchange API keys** (different from Main API keys)
   - Your Main API keys won't work here

## Solution

### Option 1: Create Exchange API Keys (RECOMMENDED)

You need to create **separate API keys** specifically for the Coinbase Exchange:

1. **Go to**: https://exchange.coinbase.com/settings/api
2. **Create new API key** with:
   - **View** permission
   - **Trade** permission
   - **Transfer** permission (CRITICAL for withdrawals)
3. **IP Whitelisting**: Add Railway's IP or disable whitelist
4. **Update Environment Variables**:
   ```
   COINBASE_EXCHANGE_API_KEY=your_exchange_api_key
   COINBASE_EXCHANGE_SECRET_KEY=your_exchange_secret_key
   COINBASE_EXCHANGE_PASSPHRASE=your_exchange_passphrase
   ```

### Option 2: Use Coinbase Advanced Trade API

Coinbase may have a newer API that supports both trading and withdrawals:

1. **Check**: https://www.coinbase.com/advanced-trade
2. **Create API keys** with withdrawal permissions
3. **Update code** to use Advanced Trade API endpoints

### Option 3: Contact Coinbase Support

If your API keys should work but don't:

1. **Ask**: "Do my Main API keys support external crypto withdrawals?"
2. **Provide**: 
   - API key permissions (wallet:transactions:send)
   - Error details (401 Unauthorized)
   - Endpoints tried (/v2/accounts/{account_id}/transactions, /withdrawals/crypto)
3. **Request**: Clarification on which API keys are needed for external withdrawals

## Implementation Steps

### If Using Exchange API Keys:

1. **Update Config**: Add Exchange API keys to `coinbase_gemini_config.py`
2. **Update Exchange Manager**: Use Exchange API keys for withdrawal calls
3. **Keep Main API Keys**: Continue using Main API keys for trading

### Code Changes Needed:

```python
# In coinbase_gemini_exchanges.py
# Use Exchange API keys for withdrawals
EXCHANGE_API_KEY = Config.COINBASE_EXCHANGE_API_KEY
EXCHANGE_SECRET_KEY = Config.COINBASE_EXCHANGE_SECRET_KEY
EXCHANGE_PASSPHRASE = Config.COINBASE_EXCHANGE_PASSPHRASE

# Use Main API keys for trading (already working)
MAIN_API_KEY = Config.COINBASE_API_KEY  # Keep for trading
```

## Verification

After implementing Exchange API keys:

1. **Test Authentication**: Verify Exchange API keys work with `/accounts` endpoint
2. **Test Withdrawal**: Try withdrawing 0.01 API3 to Gemini
3. **Monitor Logs**: Check for any remaining errors

## Conclusion

**Your current API keys work for trading but NOT for external withdrawals.**

**You need separate Exchange API keys** created from:
- https://exchange.coinbase.com/settings/api

These keys are **different** from your Main API keys and are required for:
- External crypto withdrawals
- Advanced trading features
- Exchange-specific operations

The 401 errors are **expected** - they indicate that external withdrawals require Exchange API keys, not Main API keys.

