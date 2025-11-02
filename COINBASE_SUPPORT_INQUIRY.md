# 📧 Coinbase Support Inquiry - Withdrawal Issues

## Subject Line:
**API Withdrawal Issues - Internal Server Errors & Address Book Requirements**

---

## Message to Coinbase Support:

Dear Coinbase Support Team,

I am experiencing issues with cryptocurrency withdrawals via the Coinbase API and would appreciate your assistance.

### Account Information:
- **Account Type:** [Your Account Type]
- **API Access:** Coinbase Advanced Trade API / Coinbase Prime API
- **API Permissions:** Currently have wallet permissions enabled

### Issue 1: Internal Server Errors on Withdrawals

**Problem:**
When attempting to withdraw cryptocurrency (specifically ERC-20 tokens like API3) via the API, I am receiving `internal_server_error` responses:

```
{
  "errors": [
    {
      "id": "internal_server_error",
      "message": "An internal error has occurred."
    }
  ]
}
```

**Details:**
- **Currency:** API3 (ERC-20 token on Ethereum network)
- **Network:** Ethereum (ETH)
- **API Endpoint:** `/v2/withdrawals/crypto` or equivalent withdrawal endpoint
- **Status:** Withdrawal request is being rejected immediately with server error
- **Frequency:** Consistent across multiple attempts with retry logic
- **Timing:** Occurs regardless of time of day or withdrawal amount

**What I've verified:**
- ✅ Account has sufficient balance
- ✅ API key has withdrawal permissions
- ✅ Withdrawal addresses are properly allowlisted in Address Book
- ✅ Network parameters are correct (Ethereum for ERC-20 tokens)
- ✅ API credentials are valid and authenticated

### Issue 2: Address Book / Allowlist Requirements

**Question:**
I have addresses allowlisted in my Coinbase Address Book (including the API3 Ethereum address `0xa13EdA5E3bD538499C1C1e0a8bc8e3eB8161a40E`), but I want to confirm:

1. **Is Address Book allowlisting required for API withdrawals?**
   - If yes, are there any additional steps needed beyond adding addresses to the Address Book?
   - Do addresses need to be "approved" or "activated" in a specific way?

2. **Address Book vs. API Deposit Addresses:**
   - My Address Book shows API3 address: `0xf417Dfe4f978d8DbcBD511B8a6F90e2140B65E40`
   - API `fetch_deposit_address` returns: `0xa13EdA5E3bD538499C1C1e0a8bc8e3eB8161a40E`
   - These are different addresses. Which one should I use for withdrawals?
   - Are deposit addresses and withdrawal addresses different in Coinbase?

3. **Account Restrictions:**
   - Are there any account-level restrictions that might prevent API withdrawals?
   - Do I need to enable a specific setting for API-based withdrawals?

### Technical Details:

**API Integration:**
- Using CCXT library for API access
- Following Coinbase API v2/v3 documentation
- Properly handling authentication and rate limits

**Withdrawal Request Format:**
```json
{
  "currency": "API3",
  "amount": "<amount>",
  "crypto_address": "<destination_address>",
  "network": "ETH"
}
```

**Error Response:**
```json
{
  "errors": [
    {
      "id": "internal_server_error",
      "message": "An internal error has occurred."
    }
  ]
}
```

### What I Need:

1. **Clarification on the internal server error:**
   - Is this a known issue?
   - Are there account restrictions preventing withdrawals?
   - Is there a different endpoint or method I should use?

2. **Address Book / Allowlist guidance:**
   - Which address should I use for withdrawals?
   - Do I need to take any action beyond adding to Address Book?
   - Are there any approval workflows required?

3. **Account Settings:**
   - Are there any account settings I need to enable for API withdrawals?
   - Do I need special permissions or account verification?

### Additional Context:

I am building an automated trading system that requires reliable bidirectional cryptocurrency transfers between exchanges. The ability to withdraw via API is critical for this functionality.

### Contact Information:
- **Email:** [Your Email]
- **Account:** [Your Account Email/ID]
- **Phone:** [Your Phone if preferred]

Thank you for your time and assistance. I am available to provide any additional information or perform tests as needed.

Best regards,
[Your Name]

---

## Alternative Shorter Version:

**Subject:** API Withdrawal Internal Server Error - ERC-20 Tokens

Dear Coinbase Support,

I'm experiencing `internal_server_error` responses when attempting to withdraw ERC-20 tokens (specifically API3) via the Coinbase API.

**Issue:** Withdrawal requests return `{"errors": [{"id": "internal_server_error", "message": "An internal error has occurred."}]}`

**What I've verified:**
- ✅ Sufficient balance
- ✅ API withdrawal permissions enabled
- ✅ Addresses allowlisted in Address Book
- ✅ Correct network parameters (Ethereum)

**Questions:**
1. Is this a known issue or account restriction?
2. Which address should I use: the one from Address Book or the one returned by `fetch_deposit_address` API call? (They differ)
3. Are there additional account settings needed for API withdrawals?

I can provide transaction IDs, API request details, or perform additional tests if needed.

Thank you,
[Your Name]

