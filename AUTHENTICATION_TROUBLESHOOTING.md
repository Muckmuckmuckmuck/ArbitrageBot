# 🔧 Coinbase API Authentication Troubleshooting

## Current Status

- **Error:** 401 "Invalid API Key"
- **API Endpoint:** `api.exchange.coinbase.com/withdrawals/crypto`
- **Authentication:** CB-ACCESS headers with HMAC-SHA256 signature

## Possible Causes

### 1. **IP Whitelisting** (Most Likely)
Your API key might have IP restrictions that don't include Railway's IP.

**Fix:**
1. Go to Coinbase → Settings → API
2. Find your API key
3. Check "IP Whitelist" settings
4. Either:
   - Add Railway's IP address (if you know it)
   - Or disable IP whitelist (allow all IPs)

### 2. **API Key Permissions**
Make sure "Transfer" permission is enabled, not just "Trade" and "View".

**Check:**
1. Go to Coinbase → Settings → API
2. Find your API key
3. Verify permissions: ✅ View, ✅ Trade, ✅ **Transfer**

### 3. **API Key Status**
- Is the key active? (not revoked/disabled)
- Was it just created? (may need 48 hours to activate)
- Has it expired?

### 4. **Authentication Format**
Current implementation:
- ✅ Passphrase: Plain text (not base64 encoded)
- ✅ Signature: HMAC-SHA256 with timestamp + method + path + body
- ✅ Headers: CB-ACCESS-KEY, CB-ACCESS-SIGN, CB-ACCESS-TIMESTAMP, CB-ACCESS-PASSPHRASE

## Testing

Run the diagnostic script:
```bash
python3 CHECK_API_KEY_TYPE.py
```

This will test:
- ✅ If your keys work with Main Coinbase API (`api.coinbase.com`)
- ✅ If your keys work with Exchange API (`api.exchange.coinbase.com`)
- ❌ Which API is failing and why

## Next Steps

1. **Run diagnostic script** to see which API works
2. **Check IP whitelisting** in Coinbase settings
3. **Verify Transfer permission** is enabled
4. **Test again** after fixing IP whitelist

## If Still Failing

If both APIs fail or Exchange API fails:
- May need to contact Coinbase support
- Or may need Exchange-specific API keys (if they're different)
- Or may need to use a different withdrawal method

