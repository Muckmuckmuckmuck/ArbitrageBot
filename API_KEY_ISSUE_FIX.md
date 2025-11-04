# 🔧 Coinbase Exchange API Key Issue - "Invalid API Key"

## Problem

Getting **401 "Invalid API Key"** error when trying to use Exchange API.

## Possible Causes

### 1. **Wrong API Key Type** (Most Likely)
Your API keys might be for **Main Coinbase API**, not **Exchange API**.

**Main Coinbase API:**
- Created at: `https://www.coinbase.com/settings/api`
- Works with: `api.coinbase.com`
- Does NOT work with: `api.exchange.coinbase.com`

**Exchange API:**
- Created at: `https://exchange.coinbase.com/settings/api`
- Works with: `api.exchange.coinbase.com`
- Different API keys!

### 2. **Passphrase Encoding** (Fixed)
I've updated the code to base64 encode the passphrase, which Exchange API requires.

### 3. **IP Whitelisting**
If your API key has IP restrictions, Railway's IP might not be whitelisted.

### 4. **API Key Permissions**
Even with "transfer" permission, if it's a Main API key, it won't work with Exchange API.

---

## Solution

### Option 1: Create Exchange API Keys (Recommended)

1. **Go to Exchange API Settings:**
   ```
   https://exchange.coinbase.com/settings/api
   ```

2. **Create New API Key:**
   - Click "New API Key"
   - Set permissions: **View**, **Trade**, **Transfer**
   - Set IP whitelist (optional, or leave blank for Railway)
   - Click "Create"

3. **Update Environment Variables:**
   - Replace `COINBASE_API_KEY` with Exchange API key
   - Replace `COINBASE_SECRET_KEY` with Exchange API secret
   - Replace `COINBASE_PASSPHRASE` with Exchange API passphrase

4. **Redeploy on Railway:**
   - Update environment variables
   - Bot will automatically redeploy

### Option 2: Test Which API Your Keys Work With

Run the diagnostic script:
```bash
python3 CHECK_API_KEY_TYPE.py
```

This will tell you:
- ✅ If your keys work with Main Coinbase API
- ✅ If your keys work with Exchange API
- ❌ Which API your keys are for

---

## How to Tell Which API Your Keys Are For

### Main Coinbase API Keys:
- Created at: `coinbase.com/settings/api`
- Used for: Main Coinbase platform
- Works with: `api.coinbase.com`
- Does NOT work with: Exchange API

### Exchange API Keys:
- Created at: `exchange.coinbase.com/settings/api`
- Used for: Coinbase Exchange (formerly Pro)
- Works with: `api.exchange.coinbase.com`
- Does NOT work with: Main Coinbase API

---

## Code Fix Applied

I've updated the code to:
1. ✅ Base64 encode the passphrase (required by Exchange API)
2. ✅ Better error logging
3. ✅ Diagnostic script to test API key type

---

## Next Steps

1. **Run diagnostic:** `python3 CHECK_API_KEY_TYPE.py`
2. **If Exchange API fails:** Create new Exchange API keys
3. **Update environment variables** with Exchange API keys
4. **Test withdrawal again**

---

## Important Note

**Main Coinbase API keys and Exchange API keys are DIFFERENT!**

Even if your main API keys have "transfer" permission, they won't work with Exchange API endpoints. You need separate Exchange API keys.

