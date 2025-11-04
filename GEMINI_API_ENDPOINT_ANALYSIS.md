# 🔍 Gemini API Endpoint Analysis

## Which Endpoint Are We Using?

### **We're Using CCXT → Calls Gemini's `/v1/withdraw/{currency}` Endpoint**

CCXT's `exchange.withdraw()` method maps to Gemini's **external withdrawal endpoint**:
- **Endpoint:** `POST /v1/withdraw/{currency}`
- **Purpose:** Withdraw crypto to **external addresses** (e.g., Coinbase)
- **This is correct for our use case!** ✅

### **NOT Using `/v1/account/transfer/{currency}`**

This endpoint is for **internal transfers** between Gemini accounts:
- **Endpoint:** `POST /v1/account/transfer/{currency}`
- **Purpose:** Transfer between Gemini accounts (e.g., "Primary" to "Trading")
- **Requires:** Master level key + Fund Manager role
- **This is NOT what we need** ❌

---

## Requirements for `/v1/withdraw/{currency}` (Our Endpoint)

### **1. API Key Requirements**
- ✅ **Fund Manager role** - REQUIRED
- ❓ **Master vs Account level key** - Documentation is unclear
  - Transfer endpoint explicitly requires "Master level key"
  - Withdraw endpoint doesn't specify, but typically works with Account level keys

### **2. Address Whitelisting**
- ✅ **Approved address list must exist** on your account
- ✅ **Destination address must be on approved list** before withdrawal
- ⚠️ **"Cryptocurrency withdrawal address whitelists are not enabled"** - This means the whitelist feature itself is disabled

### **3. OAuth Scope**
- ✅ **`crypto:send`** scope required (for OAuth keys)

### **4. Required Parameters**
- `address` - Destination address (must be approved)
- `amount` - Amount to withdraw
- `account` - Required for Master API keys (account name like "primary")

---

## Critical Issues Identified

### **Issue 1: Whitelist Feature Not Enabled**
**Error:** `"Cryptocurrency withdrawal address whitelists are not enabled for account primary"`

**What This Means:**
- The whitelist **feature itself** is disabled on your account
- Even if addresses are added, they won't be recognized
- You need to **enable the whitelist feature** in Gemini settings

**Solution:**
1. Go to Gemini → Settings → Security
2. Find "Approved Addresses" or "Withdrawal Whitelist"
3. **Enable the whitelist feature**
4. Then add addresses to the whitelist

### **Issue 2: API Key Type Confusion**
**Documentation says:**
- `/v1/account/transfer/{currency}` requires **Master level key**
- `/v1/withdraw/{currency}` doesn't specify, but typically works with Account level keys

**Our Setup:**
- We're using `/v1/withdraw/{currency}` (external withdrawal)
- Should work with Account level key + Fund Manager role
- But if you're using a Master key, that's also fine

### **Issue 3: Account Parameter**
**For Master API keys:**
- Must specify `account` parameter (e.g., "primary")
- CCXT may not be passing this automatically

**For Account level keys:**
- `account` parameter not needed
- Key is already scoped to specific account

---

## What We Need to Verify

### ✅ **Check Your Gemini API Key:**
1. **Key Type:** Master or Account level?
2. **Role:** Fund Manager role assigned?
3. **OAuth Scope:** `crypto:send` (if using OAuth)

### ✅ **Check Gemini Account Settings:**
1. **Whitelist Feature:** Is it enabled?
   - Go to Settings → Security → Approved Addresses
   - Enable if disabled
2. **Approved Addresses:** Are Coinbase addresses added?
   - Add Coinbase deposit addresses for each crypto
   - Confirm via email if required

### ✅ **Check CCXT Implementation:**
1. **Is CCXT passing `account` parameter?**
   - If using Master key, CCXT may need to pass `account="primary"`
   - Check if we need to add this to params

---

## Next Steps

1. **Enable Gemini whitelist feature** (if disabled)
2. **Verify API key has Fund Manager role**
3. **Add Coinbase addresses to Gemini whitelist**
4. **Test withdrawal again**

---

## Summary

**We're using the CORRECT endpoint** (`/v1/withdraw/{currency}`) for external withdrawals.

**The issue is:**
- Whitelist feature is disabled on your Gemini account
- You need to enable it first, then add addresses

**The endpoint itself is correct - the problem is account configuration!**

