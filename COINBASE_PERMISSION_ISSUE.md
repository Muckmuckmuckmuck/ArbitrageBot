# 🚨 CRITICAL: Coinbase API Permission Issue

## Problem Identified

Based on Coinbase's official documentation for `/withdrawals/crypto` endpoint:

### Required Permission
- **Documentation says:** `"transfer"` permission
- **We currently have:** `wallet:transactions:send` permission

### The Issue
The `/withdrawals/crypto` endpoint specifically requires:
- ✅ **"transfer" permission** (not "wallet:transactions:send")
- ✅ **API key must belong to default profile**

## What This Means

Even though `wallet:transactions:send` might work for other endpoints, the `/withdrawals/crypto` endpoint explicitly requires the "transfer" permission.

## Solution

### Step 1: Check Current API Key Permissions
1. Go to Coinbase → Settings → API
2. Find your API key
3. Check what permissions are enabled

### Step 2: Update API Key Permissions
If "transfer" is not enabled:
1. **Option A:** Edit existing key and enable "transfer" permission
2. **Option B:** Create new API key with "transfer" permission

### Step 3: Verify API Key Profile
- Ensure the API key belongs to your **default profile**
- If you have multiple profiles, the key must be associated with the default one

## Testing

After updating permissions:
1. Run the withdrawal test again
2. The `internal_server_error` should be resolved if this was the issue

## Additional Notes

- CCXT should be using the correct endpoint (`/withdrawals/crypto`)
- The endpoint is correct, but the permission might be wrong
- This could explain why we get `internal_server_error` instead of a clear permission error

