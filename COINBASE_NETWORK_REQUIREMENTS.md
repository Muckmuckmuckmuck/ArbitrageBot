# 🌐 Coinbase Network Requirements for Bot Cryptos

## 🎯 **CRITICAL: Network Information for Each Crypto**

### **BRIDGE CRYPTO (For Transfers)**

#### 0. **XRP (Ripple)**
- **Network:** `XRP Ledger`
- **Coinbase Parameter:** `{'network': 'XRP'}`
- **Transfer Time:** ~3-5 minutes
- **Fee:** FREE on Coinbase
- **Notes:** XRP Ledger network, requires destination_tag for some exchanges

### **PRIMARY TIER (70% capital)**

#### 1. **ZEC (Zcash)**
- **Network:** `Zcash Network` (Native blockchain)
- **Coinbase Parameter:** `{'network': 'ZEC'}` or `{'network': 'Zcash'}`
- **Transfer Time:** ~10 minutes
- **Fee:** FREE on Coinbase
- **Notes:** Native Zcash blockchain, not ERC-20

#### 2. **BAT (Basic Attention Token)**
- **Network:** `Ethereum (ERC-20)`
- **Coinbase Parameter:** `{'network': 'ETH'}` or `{'network': 'Ethereum'}`
- **Transfer Time:** ~3-15 minutes (depends on gas)
- **Fee:** FREE on Coinbase
- **Notes:** ERC-20 token on Ethereum

#### 3. **COMP (Compound)**
- **Network:** `Ethereum (ERC-20)`
- **Coinbase Parameter:** `{'network': 'ETH'}` or `{'network': 'Ethereum'}`
- **Transfer Time:** ~3-15 minutes (depends on gas)
- **Fee:** FREE on Coinbase
- **Notes:** ERC-20 token on Ethereum

#### 4. **QNT (Quant)**
- **Network:** `Ethereum (ERC-20)`
- **Coinbase Parameter:** `{'network': 'ETH'}` or `{'network': 'Ethereum'}`
- **Transfer Time:** ~3-15 minutes (depends on gas)
- **Fee:** FREE on Coinbase
- **Notes:** ERC-20 token on Ethereum

### **SECONDARY TIER (20% capital)**

#### 5. **MOODENG**
- **Network:** `Ethereum (ERC-20)` ⚠️ **VERIFY THIS**
- **Coinbase Parameter:** `{'network': 'ETH'}` or `{'network': 'Ethereum'}`
- **Transfer Time:** ~3-15 minutes (depends on gas)
- **Fee:** FREE on Coinbase
- **Notes:** ⚠️ **NEEDS VERIFICATION** - Check Coinbase for exact network

#### 6. **AMP**
- **Network:** `Ethereum (ERC-20)`
- **Coinbase Parameter:** `{'network': 'ETH'}` or `{'network': 'Ethereum'}`
- **Transfer Time:** ~3-15 minutes (depends on gas)
- **Fee:** FREE on Coinbase
- **Notes:** ERC-20 token on Ethereum

#### 7. **INJ (Injective)**
- **Network:** `Ethereum (ERC-20)`
- **Coinbase Parameter:** `{'network': 'ETH'}` or `{'network': 'Ethereum'}`
- **Transfer Time:** ~3-15 minutes (depends on gas)
- **Fee:** FREE on Coinbase
- **Notes:** ERC-20 token on Ethereum

### **HIGH RISK TIER (10% capital)**

#### 8. **API3**
- **Network:** `Ethereum (ERC-20)`
- **Coinbase Parameter:** `{'network': 'ETH'}` or `{'network': 'Ethereum'}`
- **Transfer Time:** ~3-15 minutes (depends on gas)
- **Fee:** FREE on Coinbase
- **Notes:** ERC-20 token on Ethereum

#### 9. **IMX (Immutable X)**
- **Network:** `Ethereum (ERC-20)`
- **Coinbase Parameter:** `{'network': 'ETH'}` or `{'network': 'Ethereum'}`
- **Transfer Time:** ~3-15 minutes (depends on gas)
- **Fee:** FREE on Coinbase
- **Notes:** ERC-20 token on Ethereum

---

## 🔧 **API Implementation**

### **For XRP (XRP Ledger):**
```python
withdraw_params = {
    'network': 'XRP',
    'destination_tag': tag  # Required for some exchanges
}
```

### **For ZEC (Zcash Network):**
```python
withdraw_params = {
    'network': 'ZEC'  # or 'Zcash'
}
```

### **For All ERC-20 Tokens (BAT, COMP, QNT, AMP, INJ, API3, IMX):**
```python
withdraw_params = {
    'network': 'ETH'  # or 'Ethereum'
}
```

### **For MOODENG (Verify First):**
```python
withdraw_params = {
    'network': 'ETH'  # Likely Ethereum, but VERIFY
}
```

---

## ⚠️ **CRITICAL WARNINGS**

### **1. Network Mismatch = Lost Funds**
- **XRP on Ethereum network** = ❌ **FUNDS LOST**
- **ZEC on Ethereum network** = ❌ **FUNDS LOST**
- **BAT on Zcash network** = ❌ **FUNDS LOST**
- **Always use correct network!**

### **2. Ethereum Gas Fees**
- **ERC-20 tokens** (BAT, COMP, QNT, AMP, INJ, API3, IMX) use Ethereum gas
- **Gas fees vary** based on network congestion
- **Coinbase covers fees** for withdrawals

### **3. MOODENG Verification Needed**
- **MOODENG network** needs verification
- **Check Coinbase** for exact network requirements
- **Test with small amount** first

---

## 🧪 **Testing Strategy**

### **Phase 1: Test XRP (Fastest)**
```python
# XRP uses XRP Ledger network
withdraw_params = {'network': 'XRP', 'destination_tag': tag}
```

### **Phase 2: Test ZEC (Safest)**
```python
# ZEC uses native Zcash network
withdraw_params = {'network': 'ZEC'}
```

### **Phase 3: Test ERC-20 (BAT)**
```python
# BAT uses Ethereum network
withdraw_params = {'network': 'ETH'}
```

### **Phase 4: Test MOODENG**
```python
# MOODENG - VERIFY NETWORK FIRST
withdraw_params = {'network': 'ETH'}  # Likely, but verify
```

---

## 📋 **Whitelist Requirements**

### **On Coinbase:**
1. **XRP addresses** (XRP Ledger network)
2. **ZEC addresses** (Zcash network)
3. **Ethereum addresses** (for BAT, COMP, QNT, AMP, INJ, API3, IMX)
4. **MOODENG addresses** (verify network first)

### **On Gemini:**
1. **XRP addresses** (XRP Ledger network)
2. **ZEC addresses** (Zcash network)
3. **Ethereum addresses** (for ERC-20 tokens)
4. **MOODENG addresses** (verify network first)

---

## 🚀 **Quick Reference**

| Crypto | Network | Parameter | Transfer Time | Fee |
|--------|---------|-----------|---------------|-----|
| XRP | XRP Ledger | `{'network': 'XRP'}` | ~3-5 min | FREE |
| ZEC | Zcash | `{'network': 'ZEC'}` | ~10 min | FREE |
| BAT | Ethereum | `{'network': 'ETH'}` | ~3-15 min | FREE |
| COMP | Ethereum | `{'network': 'ETH'}` | ~3-15 min | FREE |
| QNT | Ethereum | `{'network': 'ETH'}` | ~3-15 min | FREE |
| MOODENG | Ethereum? | `{'network': 'ETH'}` | ~3-15 min | FREE |
| AMP | Ethereum | `{'network': 'ETH'}` | ~3-15 min | FREE |
| INJ | Ethereum | `{'network': 'ETH'}` | ~3-15 min | FREE |
| API3 | Ethereum | `{'network': 'ETH'}` | ~3-15 min | FREE |
| IMX | Ethereum | `{'network': 'ETH'}` | ~3-15 min | FREE |

---

## ⚡ **IMMEDIATE ACTION**

### **1. Verify MOODENG Network**
- Check Coinbase for MOODENG network requirements
- Test with small amount first

### **2. Update Bot Code**
- Add network parameters to withdrawal calls
- Test each crypto individually

### **3. Whitelist Addresses**
- Add addresses for each network type
- XRP addresses (XRP Ledger network)
- ZEC addresses (Zcash network)
- Ethereum addresses (ERC-20 tokens)

---

**The network information is CRITICAL - wrong network = lost funds!** 🚨
