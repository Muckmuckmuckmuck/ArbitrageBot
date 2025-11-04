# 📋 Coinbase Support - Error Details Template

Use this template to provide Coinbase support with all required information.

---

## **Correlation ID:**
[Will be captured from error response - check logs for "Correlation ID:" field]

**Note:** If correlation ID is not in the error response, it may be in response headers as `x-correlation-id`

---

## **Timestamp of the error:**
[Will be captured from error logs - check for "Timestamp:" field]

**Format:** ISO 8601 (e.g., `2025-11-04T20:27:59.961572`)

---

## **Request Details:**

### **API Endpoint:**
`POST /withdrawals/crypto` (via CCXT library)

### **Currency:**
`API3` (ERC-20 token on Ethereum network)

### **Amount:**
[Amount attempted - will be in logs]

### **Network Parameter:**
`ETH` (Ethereum mainnet)

### **Destination Address:**
[Address from logs]

### **API Key Permissions:**
- `wallet:transactions:send` ✅ (Enabled)
- `wallet:withdrawals:create` ✅ (Should be enabled if available for account type)

### **Address Book Status:**
- Address is allowlisted in Coinbase Address Book ✅
- Address Book allowlisting is [ENABLED/DISABLED] (check your settings)

### **Full Request Parameters:**
```json
{
  "currency": "API3",
  "amount": "[amount]",
  "crypto_address": "[destination_address]",
  "network": "ETH"
}
```

---

## **Error Response:**
```
{"errors":[{"id":"internal_server_error","message":"An internal error has occurred."}]}
```

---

## **Additional Information:**
- **Account Type:** [Personal/Institutional]
- **API Key Type:** [Exchange API Key]
- **Account Status:** [Fully verified/Partially verified]
- **Recent Deposits:** [Yes/No - if yes, may have withdrawal restrictions]
- **Withdrawal History:** [First withdrawal/Previous withdrawals successful]

---

## **Troubleshooting Steps Already Taken:**
1. ✅ Verified API key has withdrawal permissions
2. ✅ Verified destination address is in Address Book (allowlisted)
3. ✅ Ensured network parameter is correctly set to 'ETH' for ERC-20 token
4. ✅ Verified sufficient balance for withdrawal
5. ✅ Implemented retry logic (all attempts fail with same error)
6. ✅ Tested with different amounts (error persists)

---

## **Expected Behavior:**
Withdrawal should succeed with:
- Valid ERC-20 address
- Correct network parameter (ETH)
- Allowlisted address
- Sufficient balance

## **Actual Behavior:**
Consistent `internal_server_error` on all withdrawal attempts for API3 (ERC-20 token).

---

**Next Steps:**
Run `coinbase_withdrawal_error_test.py` to capture all details automatically.

