# 📋 PIONEX.US ACCOUNT GUIDE

## Which Account Should You Choose?

---

## 🎯 QUICK ANSWER

**For your arbitrage bot**: **STANDARD ACCOUNT**

You don't need an institutional account unless you're managing $100k+ or need special features.

---

## 📊 COMPARISON

### **Standard Account** ✅ (Recommended)

**Best for**:
- Individual traders
- Personal accounts
- Starting capital: $100 - $100,000
- Automated trading bots
- **Your arbitrage bot** ✅

**Benefits**:
- ✅ Quick signup (5-10 minutes)
- ✅ Lower fees (0.05% maker, 0.05% taker)
- ✅ Full API access
- ✅ Automated trading allowed
- ✅ No minimum balance
- ✅ Fast verification

**Limitations**:
- Lower daily withdrawal limits (~$50k/day)
- Standard support response time

**Fees**:
- Trading: 0.05% maker / 0.05% taker (0.1% total)
- Withdrawals: Varies by coin (free for some)
- No monthly fees

**API Access**: ✅ Full access (what you need!)

---

### **Institutional Account**

**Best for**:
- Hedge funds
- Trading firms
- Crypto businesses
- Managing client funds
- High-volume traders (>$1M/month)

**Benefits**:
- Lower fees for very high volume
- Dedicated account manager
- Higher withdrawal limits
- Priority support
- Custom solutions

**Requirements**:
- Business registration
- Company documents
- Tax ID / EIN
- Proof of funds
- Compliance documentation
- Minimum balance requirements

**Fees**:
- Negotiated based on volume
- Generally better for >$1M trading volume/month
- May have monthly account fees

**API Access**: ✅ Full access (same as standard)

---

## 🎯 DECISION MATRIX

| Factor | Standard | Institutional |
|--------|----------|---------------|
| **Setup Time** | 5-10 min ✅ | Days to weeks |
| **Documentation** | Minimal ✅ | Extensive |
| **Min Balance** | None ✅ | $50k-100k+ |
| **Trading Fees** | 0.1% total ✅ | Lower (if high volume) |
| **API Access** | Full ✅ | Full ✅ |
| **Automated Trading** | Yes ✅ | Yes ✅ |
| **For Your Bot** | Perfect ✅ | Overkill ❌ |

---

## 💡 WHY STANDARD IS RIGHT FOR YOU

### 1. **Your Bot Doesn't Need Institutional Features**
- Your bot just needs API access ✅
- Standard account has full API access ✅
- You're trading your own money, not clients' ✅

### 2. **Faster Setup**
- Standard: 5-10 minutes ✅
- Institutional: Could take weeks ❌
- You want to start testing ASAP ✅

### 3. **No Minimum Requirements**
- Standard: Start with $100 ✅
- Institutional: Usually requires $50k-100k+ ❌
- You're starting small ✅

### 4. **Lower Fees (For Your Volume)**
Standard account fees: 0.1% total
- $1,000 trade = $1 fee
- $10,000 trade = $10 fee
- $100,000 trade = $100 fee

Institutional fees are only better if you're trading $1M+ per month.

### 5. **Simpler Compliance**
- Standard: Basic KYC (ID verification) ✅
- Institutional: Business docs, tax forms, legal agreements ❌

---

## 📝 HOW TO SIGN UP (STANDARD ACCOUNT)

### Step 1: Go to Pionex.US
```
https://www.pionex.us
```

### Step 2: Click "Sign Up"
- Choose **"Individual Account"** or **"Standard Account"**
- Do NOT choose "Institutional" or "Business"

### Step 3: Provide Information
- Email address
- Password
- Phone number (for 2FA)

### Step 4: Verify Identity (KYC)
- Upload government ID (Driver's license or passport)
- Take selfie for verification
- Wait 5-30 minutes for approval

### Step 5: Enable 2FA
- Download Google Authenticator or Authy
- Enable 2-factor authentication
- **IMPORTANT**: Save backup codes!

### Step 6: Create API Keys
1. Go to Account → API Management
2. Click "Create New API Key"
3. Enable permissions:
   - ✅ Read
   - ✅ Trade
   - ❌ Withdraw (not needed, safer to leave off)
4. Save API key and secret securely
5. Add to your `.env` file

---

## 🚀 FOR COINBASE PRO

Same recommendation: **STANDARD/INDIVIDUAL ACCOUNT**

### Coinbase Pro Account Types:
1. **Individual** ✅ (Recommended for you)
2. **Institution** (Only if you're a business)

### How to Sign Up:
1. Go to https://pro.coinbase.com
2. Sign up with email
3. Verify identity (KYC)
4. Enable 2FA
5. Create API keys:
   - Go to Profile → API
   - Create new API key
   - Enable: View, Trade
   - Save key, secret, and passphrase
   - Add to `.env` file

---

## 💰 WHEN TO UPGRADE TO INSTITUTIONAL

Consider institutional accounts when:
- [ ] Trading volume > $1 million/month
- [ ] Managing other people's money
- [ ] Operating as a business/hedge fund
- [ ] Need dedicated support
- [ ] Want negotiated fee tiers
- [ ] Have compliance team to handle paperwork

For most individual bot traders: **Never needed**

---

## ⚠️  IMPORTANT NOTES

### API Access is the Same
- Standard account API = Institutional API
- Same endpoints, same functionality
- No difference for your bot

### You Can Always Upgrade Later
- Start with standard
- If you grow to $1M+ volume, contact Pionex
- They'll help you upgrade if it makes sense
- No penalty for starting standard

### Institutional Account is NOT Worth It Unless:
- You're trading $1M+ per month
- You're a registered business
- You need compliance features
- You want dedicated support

For a bot starting with $100-$10,000, institutional is:
- ❌ Slower to set up
- ❌ More paperwork
- ❌ Same or higher fees (at your volume)
- ❌ Unnecessary complexity

---

## ✅ FINAL RECOMMENDATION

### **Sign up for STANDARD ACCOUNT on both exchanges**

**Pionex.US**: Individual/Standard Account  
**Coinbase Pro**: Individual Account

This gives you:
- ✅ Fast setup (30 minutes total)
- ✅ Full API access
- ✅ Low fees
- ✅ No minimum balance
- ✅ Everything your bot needs
- ✅ Can start trading today

You can always upgrade later if needed (you won't need to).

---

## 🎯 NEXT STEPS

1. **Sign up for standard accounts** on both exchanges
2. **Complete KYC verification** (usually 5-30 minutes)
3. **Enable 2FA** (security is critical!)
4. **Create API keys** (Read + Trade permissions)
5. **Add keys to .env file**
6. **Run test_imports.py** to verify setup
7. **Start bot in sandbox mode** for testing

---

## 📞 STILL UNSURE?

**Ask yourself**:
- Am I trading my own money? → **Standard** ✅
- Am I starting with < $100k? → **Standard** ✅
- Do I just need API access for my bot? → **Standard** ✅
- Am I an individual, not a business? → **Standard** ✅

If you answered YES to any of these → **Go with Standard Account**

---

**TL;DR**: Use **Standard/Individual accounts**. Institutional is overkill and slower. You can always upgrade later if you scale to $1M+ trading volume (which would be a nice problem to have! 🚀)
