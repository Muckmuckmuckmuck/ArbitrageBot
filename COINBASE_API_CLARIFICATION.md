# 🔍 Coinbase API Clarification - Which API Are We Using?

## ⚠️ CRITICAL QUESTION: Advanced Trade API vs Exchange API

### **Coinbase Has TWO Different APIs:**

#### **1. Coinbase Advanced Trade API** (Newer)
- **Base URL:** `https://api.coinbase.com/api/v3/brokerage`
- **Endpoint Example:** `/api/v3/brokerage/orders`
- **Purpose:** Newer API for trading
- **Status:** May not support withdrawals directly

#### **2. Coinbase Exchange API** (Formerly Coinbase Pro)
- **Base URL:** `https://api.exchange.coinbase.com` or `https://api.coinbase.com/v2/`
- **Endpoint Example:** `/withdrawals/crypto`
- **Purpose:** Trading + Withdrawals
- **Status:** This is where `/withdrawals/crypto` endpoint exists

---

## What Does CCXT Use?

### **CCXT's `coinbase` Exchange:**
- **Exchange ID:** `coinbase`
- **May use:** Exchange API (older Coinbase Pro API)
- **OR:** Advanced Trade API (newer API)

### **The Problem:**
The `/withdrawals/crypto` endpoint we found in the documentation is from the **Exchange API**, not Advanced Trade API.

If CCXT's `coinbase` exchange is using **Advanced Trade API**, then:
- ❌ It might not have access to `/withdrawals/crypto` endpoint
- ❌ We might need to use a different CCXT exchange (like `coinbasepro`)
- ❌ Or we need to use the Exchange API directly

---

## ✅ VERIFIED: CCXT's coinbase Exchange

### **CCXT Uses:**
- **Base URL:** `https://api.coinbase.com`
- **Documentation References:**
  - `https://developers.coinbase.com/api/v2` (v2 API)
  - `https://docs.cloud.coinbase.com/advanced-trade/docs/welcome` (Advanced Trade API)

### **This Means:**
CCXT's `coinbase` exchange uses the **main Coinbase API** (`api.coinbase.com`), which may support both:
- Coinbase v2 API endpoints
- Advanced Trade API endpoints

**However**, the `/withdrawals/crypto` endpoint you found is from the **Exchange API** (`api.exchange.coinbase.com`), not the main Coinbase API!

### **2. Check Which Withdrawal Endpoint CCXT Calls:**
- Does CCXT's `coinbase` exchange call `/withdrawals/crypto`?
- Or does it use a different endpoint?

### **3. Verify API Key Type:**
- **Exchange API keys:** Have passphrase (older format)
- **Advanced Trade API keys:** May not have passphrase (newer format)
- **Your keys:** Have passphrase? → Likely Exchange API keys

---

## Possible Solutions

### **Option 1: Use `coinbasepro` Exchange in CCXT**
```python
# Instead of:
ccxt.coinbase()

# Use:
ccxt.coinbasepro()  # But this might be deprecated
```

### **Option 2: Use Exchange API Directly**
If CCXT doesn't support withdrawals properly, we might need to:
- Use CCXT for trading
- Use Exchange API directly for withdrawals (via HTTP requests)

### **Option 3: Verify CCXT Version**
- Newer CCXT versions might have better support
- Check if there's a `coinbaseadvanced` exchange

---

## Current Status

### **What We Know:**
- ✅ We're using `ccxt.coinbase()`
- ✅ We have passphrase (suggests Exchange API keys)
- ✅ Comments say "Coinbase Advanced Trade"
- ❌ Withdrawals failing with `internal_server_error`
- ❓ Not sure which API CCXT is actually using

### **What We Need:**
1. **Verify CCXT's base URL** for coinbase exchange
2. **Check if `/withdrawals/crypto` endpoint is accessible**
3. **Determine if we need to switch APIs or use direct HTTP calls**

---

## Next Steps

1. **Check CCXT source code** or documentation for coinbase exchange
2. **Test withdrawal endpoint** directly with Exchange API
3. **Verify API key permissions** match the API being used
4. **Consider switching** to Exchange API directly if CCXT doesn't support it

---

## Important Note

The `/withdrawals/crypto` endpoint documentation you shared is from **Coinbase Exchange API**, not Advanced Trade API. This suggests we should be using the Exchange API, not Advanced Trade API.

**If CCXT's `coinbase` exchange is using Advanced Trade API, that could explain why withdrawals are failing!**

