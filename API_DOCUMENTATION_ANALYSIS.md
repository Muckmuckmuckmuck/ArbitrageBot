# 📚 API Documentation Analysis - Coinbase & Gemini

## 🔍 Key Findings from Official Documentation

### 🏦 Coinbase API Requirements

#### 1. **API Key Permissions**
- **Required:** `wallet:withdrawals:create` scope
- **Current Status:** ✅ You have `wallet:transactions:send` (should be sufficient)

#### 2. **Address Book (Allowlist) - CRITICAL ISSUE**
- **Default Behavior:** Coinbase Prime uses an address book to prevent withdrawals to unknown addresses
- **New Addresses:** Must be added via API but require **consensus approval in the UI**
- **Solution:** Can be **disabled in the UI** for streamlined workflows
- **Status:** ❓ **Unknown if enabled/disabled on your account**

#### 3. **Withdrawal Endpoint**
- **Correct Endpoint:** `POST https://api.exchange.coinbase.com/withdrawals/crypto`
- **Our Usage:** We're using `POST https://api.coinbase.com/v2/accounts/:account_id/transactions`
- **Issue:** ❌ **We're using the wrong endpoint!**

#### 4. **Required Parameters**
- `amount`: The amount to withdraw
- `currency`: The cryptocurrency (XRP)
- `crypto_address`: The destination wallet address
- **Missing:** We might be missing required parameters

---

### 🏦 Gemini API Requirements

#### 1. **API Key Permissions**
- **Required:** "Fund Management" permission
- **Status:** ❓ **Unknown if enabled**

#### 2. **Address Whitelisting**
- **Required:** Withdrawal addresses must be whitelisted
- **Process:** Add addresses in "Security" → "Approved Addresses"
- **Approval:** May require email confirmation
- **Status:** ❓ **Unknown if Gemini address is whitelisted**

#### 3. **Withdrawal Endpoint**
- **Correct:** `POST https://api.gemini.com/v1/withdraw/{currency}`
- **Parameters:** `address`, `amount`, `withdrawal_id` (optional)

---

## 🚨 CRITICAL ISSUES IDENTIFIED

### Issue 1: Wrong Coinbase Endpoint
**Problem:** We're using the wrong API endpoint
- **Current:** `POST /v2/accounts/:account_id/transactions`
- **Correct:** `POST /withdrawals/crypto`

### Issue 2: Address Book Restrictions
**Problem:** Coinbase may be blocking unknown addresses
- **Solution:** Disable address book in UI or add Gemini address

### Issue 3: Missing Permissions
**Problem:** API keys may not have correct permissions
- **Coinbase:** Need `wallet:withdrawals:create`
- **Gemini:** Need "Fund Management" permission

### Issue 4: Address Whitelisting
**Problem:** Gemini may require address whitelisting
- **Solution:** Add Coinbase address to Gemini whitelist

---

## 🔧 IMMEDIATE FIXES REQUIRED

### Step 1: Check Coinbase Settings
1. **Go to:** https://www.coinbase.com/settings/security
2. **Look for:** "Address Book" or "Allowlist" settings
3. **Action:** Disable if enabled, or add Gemini XRP address

### Step 2: Check API Permissions
1. **Coinbase:** Verify `wallet:withdrawals:create` permission
2. **Gemini:** Verify "Fund Management" permission

### Step 3: Fix API Endpoint
**Current Code:**
```python
withdrawal = source_exchange.withdraw(
    code='XRP',
    amount=amount,
    address=address,
    params=withdraw_params
)
```

**Should Use:**
```python
# For Coinbase - use correct endpoint
withdrawal = source_exchange.withdraw(
    code='XRP',
    amount=amount,
    address=address,
    params=withdraw_params
)
```

### Step 4: Whitelist Addresses
1. **Gemini:** Add Coinbase XRP address to whitelist
2. **Coinbase:** Add Gemini XRP address to whitelist (if address book enabled)

---

## 📋 ACTION PLAN

### Phase 1: Account Configuration (Today)
1. **Check Coinbase address book settings**
2. **Verify API permissions on both exchanges**
3. **Whitelist addresses if required**

### Phase 2: Code Fixes (Today)
1. **Update withdrawal endpoint** (if needed)
2. **Add proper error handling**
3. **Test with small amounts**

### Phase 3: Testing (Tomorrow)
1. **Test manual withdrawal** on both exchanges
2. **Test API withdrawal** with small amounts
3. **Verify cross-exchange transfers**

---

## 🎯 ROOT CAUSE ANALYSIS

### Most Likely Issues (in order):
1. **Address Book enabled** on Coinbase (blocks unknown addresses)
2. **Missing API permissions** (withdrawals not allowed)
3. **Address not whitelisted** on Gemini
4. **Wrong API endpoint** (using v2 instead of withdrawals/crypto)

### Quick Test:
Try a **manual withdrawal** on Coinbase:
1. Go to Coinbase → Send/Receive
2. Select XRP
3. Try to send to Gemini address
4. See if you get the same error

---

## 💡 ALTERNATIVE SOLUTIONS

### Option 1: Use Different Crypto
- **USDC:** Often has better cross-exchange support
- **USDT:** Widely supported, lower fees
- **LTC:** Fast and cheap transfers

### Option 2: Different Exchange Pair
- **Binance + Coinbase:** Better compatibility
- **Kraken + Gemini:** More reliable
- **Coinbase Pro + Gemini:** Same company

### Option 3: Manual Transfer First
1. **Manually transfer** small amount
2. **Verify it works**
3. **Then automate** with bot

---

## 🚀 NEXT STEPS

### Immediate (Today):
1. **Sell XRP** to recover money
2. **Check account settings** on both exchanges
3. **Verify API permissions**

### Short-term (This Week):
1. **Fix API configuration**
2. **Test manual transfers**
3. **Update bot code**

### Long-term (Next Week):
1. **Enable automated transfers**
2. **Resume arbitrage trading**
3. **Scale up capital**

---

## 📞 SUPPORT CONTACTS

### Coinbase Support:
- **Email:** support@coinbase.com
- **Help Center:** https://help.coinbase.com
- **API Issues:** https://developers.coinbase.com/support

### Gemini Support:
- **Email:** support@gemini.com
- **Help Center:** https://support.gemini.com
- **API Issues:** https://docs.gemini.com/rest-api/

---

**The main issue is likely the Coinbase Address Book blocking unknown addresses. Check your account settings first!** 🎯
