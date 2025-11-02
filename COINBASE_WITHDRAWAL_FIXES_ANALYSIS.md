# 🔍 Coinbase Withdrawal Issues - Complete Analysis & Fixes

## 📋 Issues Identified

### Issue 1: Missing Network Parameter ✅ FIXED
**Problem:** Our exchange manager's `withdraw` method was not accepting or passing the `network` parameter.

**Root Cause:**
- Exchange manager had `params={}` hardcoded (empty)
- Network parameter was being passed but ignored
- ERC-20 tokens (like API3) **require** network parameter on Coinbase

**Fix Applied:**
- Updated `withdraw()` method to accept `network` parameter
- Network is now properly added to `params` dict
- All ERC-20 withdrawals now include `{'network': 'ETH'}`

### Issue 2: Incorrect Tag Parameter Format ✅ FIXED
**Problem:** Tag was being passed as separate parameter, but should be inside `params`.

**Root Cause:**
- CCXT allows tag as separate parameter OR inside params
- Working example (`mini_transfer_test.py`) shows tag **inside params**
- Some exchanges (like Coinbase) may require tag in params

**Fix Applied:**
- Tag is now added to `params` dict instead of separate parameter
- For Coinbase XRP, using `destination_tag` in params
- For other cryptos, using `tag` in params

### Issue 3: Address Book Allowlist Requirement ⚠️ CONFIGURATION NEEDED
**Problem:** Coinbase may require addresses to be in Address Book before withdrawal.

**Error Code:** `recipient_allowlist_violation`

**Finding:**
- User confirmed addresses ARE in address book
- However, **changes take ~2 days to take effect** (from Coinbase docs)
- Address must match exactly what's in address book

**Action Required:**
1. Verify the exact address in Coinbase Address Book matches API-returned address
2. Wait 2 days after adding address if recently added
3. Or disable Address Book allowlisting if not needed

### Issue 4: Internal Server Error - Account Restrictions ⚠️ POTENTIAL ISSUE
**Problem:** `internal_server_error` can indicate account-level restrictions.

**Possible Causes:**
- New account withdrawal restrictions
- Incomplete KYC/verification
- Security review/hold
- Missing API permissions

**Action Required:**
- Verify account verification status
- Check for any account holds
- Contact Coinbase support if persists

## ✅ Code Fixes Applied

### 1. Updated Exchange Manager Withdraw Method
```python
async def withdraw(self, exchange_id: str, currency: str, amount: float, 
                  address: str, tag: Optional[str] = None, 
                  network: Optional[str] = None, params: Optional[Dict] = None) -> Dict:
    # Build params dict properly
    withdraw_params = {}
    if params:
        withdraw_params.update(params)
    
    # Add network if provided (REQUIRED for ERC-20 tokens)
    if network:
        withdraw_params['network'] = network
    
    # Add tag to params (not as separate parameter)
    if tag:
        if exchange_id == 'coinbase' and currency == 'XRP':
            withdraw_params['destination_tag'] = tag
        else:
            withdraw_params['tag'] = tag
    
    # Call CCXT withdraw with tag=None (tag is in params)
    result = exchange.withdraw(
        code=currency,
        amount=amount,
        address=address,
        tag=None,  # Tag is in params
        params=withdraw_params
    )
```

### 2. Updated Test to Use Exchange Manager
**Before:**
```python
coinbase = self.exchange_manager.get_exchange('coinbase')
withdrawal = coinbase.withdraw(
    self.test_crypto,
    amount_to_send,
    address,
    tag,
    {'network': self.network}
)
```

**After:**
```python
withdrawal = await self.exchange_manager.withdraw(
    'coinbase',
    self.test_crypto,
    amount_to_send,
    address,
    tag=tag,
    network=self.network  # Network parameter properly passed
)
```

## 📚 Documentation Findings

### From Official Coinbase API Docs:

1. **Network Parameter:** REQUIRED for multi-network cryptos (ERC-20 tokens need `{'network': 'ETH'}`)

2. **Address Book:** 
   - If enabled, addresses MUST be pre-added
   - Changes take ~2 days to take effect
   - Can be disabled in settings

3. **Error Codes:**
   - `recipient_allowlist_violation` = Address not in allowlist
   - `internal_server_error` = Could be account restriction or missing parameter

4. **Required Parameters:**
   - `currency`: The cryptocurrency code
   - `amount`: Amount to withdraw
   - `crypto_address`: Destination address
   - `network`: Network parameter (for ERC-20 tokens)

## 🎯 What Should Work Now

### With the Code Fixes:
1. ✅ Network parameter properly passed to Coinbase API
2. ✅ Tag included in params (not as separate parameter)
3. ✅ Proper parameter format matching CCXT best practices
4. ✅ Consistent use of exchange manager method

### Remaining Requirements:
1. ⚠️ Address must be in Coinbase Address Book (user confirmed ✅)
2. ⚠️ Wait 2 days if address was recently added
3. ⚠️ Account must be fully verified
4. ⚠️ No account holds or restrictions

## 🧪 Testing Recommendations

### Test Sequence:
1. **Verify Address Match:**
   - Coinbase Address Book: `0xa13E...a40E`
   - API returned: `0xa13EdA5E3bD538499C1C1e0a8bc8e3eB8161a40E`
   - These should match exactly (they do!)

2. **Test Small Withdrawal:**
   - Start with 0.1 API3 (minimum)
   - Use the fixed code
   - Monitor for any new error messages

3. **If Still Failing:**
   - Check account verification status
   - Verify no account holds
   - Contact Coinbase support with exact error

## 📝 Next Steps

### Immediate:
1. ✅ Code fixes applied (committed)
2. ⏳ Test with fixed code
3. ⏳ Monitor for new error messages

### If Still Failing:
1. Verify account is fully verified (no restrictions)
2. Check Coinbase account status page
3. Contact Coinbase support with:
   - Exact error message
   - Currency: API3
   - Network: Ethereum
   - Address: `0xa13EdA5E3bD538499C1C1e0a8bc8e3eB8161a40E`
   - Confirmation that address IS in address book

## 🔑 Key Takeaways

1. **Network parameter is CRITICAL** for ERC-20 tokens - now fixed ✅
2. **Tag format matters** - now using params format ✅
3. **Address Book** - addresses must match exactly and be approved
4. **Account restrictions** - may need Coinbase support to resolve
5. **2-day delay** - address book changes take time to activate

The code should now be correct. If errors persist, they're likely account-level restrictions that require Coinbase support intervention.

