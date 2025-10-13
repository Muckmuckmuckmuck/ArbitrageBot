#!/usr/bin/env python3
"""
Extract and analyze the BEST cryptos from scan results
Flips negative spreads to positive (we can trade either direction!)
"""

import re

# Your scan results (I'll extract from the logs you provided)
SCAN_RESULTS = """
[2228/2343] VENOM/USDT      | Spread:  -1.193% | Net:  -1.693% | Profit: $  -1.69 | Vol: $      67,429 | GEM→CB
[2229/2343] VET/USDT        | Spread:  -0.349% | Net:  -0.849% | Profit: $  -0.85 | Vol: $     297,932 | GEM→CB
"""

def extract_and_analyze():
    """Extract all cryptos with spread > 0.5% (absolute value)"""
    
    # Read the full log from Railway (you'll need to paste it)
    print("="*100)
    print("🔍 CRYPTO ANALYZER - Finding Best Arbitrage Opportunities")
    print("="*100)
    print("\n💡 Key Insight: ALL spreads can be profitable by trading the opposite direction!")
    print("💡 We need: Absolute Spread > 0.5% (to cover 0.50% maker fees)\n")
    print("="*100 + "\n")
    
    # Parse from your log output
    # Based on your logs, here are the cryptos with highest absolute spreads:
    
    cryptos = [
        # From your logs - taking ABSOLUTE value of spreads
        {'symbol': 'VET3L/USDT', 'spread': 98.894, 'volume': 2707},
        {'symbol': 'WAXP/USDT', 'spread': 29.933, 'volume': 180},
        {'symbol': 'VOXEL/USDT', 'spread': 14.253, 'volume': 69},
        {'symbol': 'YFI/USDT', 'spread': 12.541, 'volume': 0},
        {'symbol': 'XNO/USDT', 'spread': 9.505, 'volume': 541},
        {'symbol': 'ZEN/USDT', 'spread': 6.889, 'volume': 87345},
        {'symbol': 'WAN/USDT', 'spread': 6.201, 'volume': 86384},
        {'symbol': 'WLD/USDT', 'spread': 3.965, 'volume': 21289},
        {'symbol': 'AUD/USD', 'spread': 3.357, 'volume': 13298052},  # FIAT - skip
        {'symbol': 'VRTX/USDT', 'spread': 2.899, 'volume': 5782},
        {'symbol': 'ZELIX/USDT', 'spread': 2.778, 'volume': 8592},
        {'symbol': 'VIRTUAL/USDT', 'spread': 2.464, 'volume': 12217},
        {'symbol': 'XCV/USDT', 'spread': 2.157, 'volume': 47300},
        {'symbol': 'YAMA/USDT', 'spread': 2.164, 'volume': 973547},
        {'symbol': 'VISION/USDT', 'spread': 1.894, 'volume': 6383},
        {'symbol': 'WLDUP/USDT', 'spread': 1.538, 'volume': 128106},
        {'symbol': 'VTHO/USDT', 'spread': 1.481, 'volume': 11598},
        {'symbol': 'ZERO/USDT', 'spread': 1.434, 'volume': 12510},
        {'symbol': 'XYM/USDT', 'spread': 0.893, 'volume': 117921},
        {'symbol': 'ZCX/USDT', 'spread': 0.896, 'volume': 83711},
        {'symbol': 'XEN/USDT', 'spread': 0.857, 'volume': 66725},
        {'symbol': 'IOTX/USD', 'spread': 0.848, 'volume': 1260},
        {'symbol': 'DEC/USDT', 'spread': 0.717, 'volume': 18950},
        {'symbol': 'XRD/USDT', 'spread': 0.692, 'volume': 151559},
        {'symbol': 'FARTCOIN/USD', 'spread': 0.646, 'volume': 1731},
        {'symbol': 'ELON/USD', 'spread': 0.618, 'volume': 11086},
        {'symbol': 'CTX/USDC', 'spread': 0.543, 'volume': 3129},
        {'symbol': 'CTX/USD', 'spread': 0.534, 'volume': 3129},
    ]
    
    # Calculate net profit after 0.50% fees
    for c in cryptos:
        c['net_spread'] = c['spread'] - 0.50
        c['net_profit'] = c['net_spread']  # Per $100
        c['profitable'] = c['net_spread'] > 0
    
    # Filter profitable only
    profitable = [c for c in cryptos if c['profitable']]
    
    print(f"📊 ANALYSIS RESULTS:")
    print(f"  Total cryptos analyzed: {len(cryptos)}")
    print(f"  Profitable (spread > 0.5%): {len(profitable)}")
    print("\n" + "="*100)
    print("🏆 PROFITABLE CRYPTOS (After 0.50% Maker Fees)")
    print("="*100)
    print(f"{'Rank':<6} {'Symbol':<20} {'Gross Spread':<14} {'Net Profit':<14} {'Volume':<15} {'Status':<10}")
    print("-"*100)
    
    for i, c in enumerate(profitable, 1):
        marker = '🔥' if c['net_profit'] > 2.0 else '✅' if c['net_profit'] > 1.0 else '⚠️'
        print(f"{marker} {i:<4} {c['symbol']:<20} {c['spread']:>7.3f}%       ${c['net_profit']:>7.2f}       ${c['volume']:>12,.0f}  {'GOOD' if c['volume'] > 10000 else 'LOW VOL'}")
    
    print("="*100 + "\n")
    
    # Filter by quality
    excellent = [c for c in profitable if c['net_profit'] > 2.0 and c['volume'] > 10000]
    good = [c for c in profitable if 1.0 < c['net_profit'] <= 2.0 and c['volume'] > 5000]
    marginal = [c for c in profitable if 0.5 < c['net_profit'] <= 1.0 and c['volume'] > 1000]
    
    print("="*100)
    print("📊 QUALITY BREAKDOWN")
    print("="*100)
    print(f"🔥 EXCELLENT (Profit > $2, Vol > $10k): {len(excellent)}")
    print(f"✅ GOOD (Profit $1-$2, Vol > $5k): {len(good)}")
    print(f"⚠️  MARGINAL (Profit $0.5-$1, Vol > $1k): {len(marginal)}")
    print("="*100 + "\n")
    
    # Show details
    if excellent:
        print("="*100)
        print("🔥 EXCELLENT OPPORTUNITIES")
        print("="*100)
        for c in excellent:
            print(f"  🔥 {c['symbol']:<20} Net: ${c['net_profit']:>6.2f} | Spread: {c['spread']:>6.3f}% | Vol: ${c['volume']:>12,.0f}")
        print("="*100 + "\n")
    
    if good:
        print("="*100)
        print("✅ GOOD OPPORTUNITIES")
        print("="*100)
        for c in good:
            print(f"  ✅ {c['symbol']:<20} Net: ${c['net_profit']:>6.2f} | Spread: {c['spread']:>6.3f}% | Vol: ${c['volume']:>12,.0f}")
        print("="*100 + "\n")
    
    if marginal:
        print("="*100)
        print("⚠️  MARGINAL OPPORTUNITIES")
        print("="*100)
        for c in marginal:
            print(f"  ⚠️  {c['symbol']:<20} Net: ${c['net_profit']:>6.2f} | Spread: {c['spread']:>6.3f}% | Vol: ${c['volume']:>12,.0f}")
        print("="*100 + "\n")
    
    # Final recommendations (filter out low volume and weird pairs)
    recommended = [
        c for c in profitable 
        if c['volume'] > 10000  # Good volume
        and c['net_profit'] > 0.5  # Profitable
        and 'USD' in c['symbol']  # USD pairs only (easier)
        and not any(x in c['symbol'] for x in ['AUD', 'EUR', 'GBP'])  # No fiat
    ]
    
    print("="*100)
    print("🚀 FINAL RECOMMENDATIONS FOR BOT")
    print("="*100)
    print(f"\nBest {len(recommended)} cryptos for arbitrage:\n")
    
    if recommended:
        print("CURRENCY_PAIRS = [")
        for c in recommended:
            print(f"    '{c['symbol']}',  # Net: ${c['net_profit']:.2f}, Spread: {c['spread']:.3f}%, Vol: ${c['volume']:,.0f}")
        print("]\n")
    else:
        print("❌ No cryptos meet all criteria (Vol > $10k, USD pairs, no fiat)")
        print("\nRelaxing criteria... showing best available:\n")
        
        # Relaxed criteria
        relaxed = [c for c in profitable if c['volume'] > 1000 and 'USD' in c['symbol']][:10]
        if relaxed:
            print("CURRENCY_PAIRS = [")
            for c in relaxed:
                print(f"    '{c['symbol']}',  # Net: ${c['net_profit']:.2f}, Spread: {c['spread']:.3f}%, Vol: ${c['volume']:,.0f}")
            print("]\n")
    
    print("="*100)
    print("\n💡 KEY INSIGHTS:")
    print(f"  - Found {len(profitable)} profitable cryptos (spread > 0.5%)")
    print(f"  - Best opportunity: {profitable[0]['symbol']} with ${profitable[0]['net_profit']:.2f} profit per $100")
    print(f"  - Most have LOW volume - may need to use smaller position sizes")
    print(f"  - Consider using USDT pairs if USD pairs have low volume")
    print("="*100 + "\n")

if __name__ == "__main__":
    extract_and_analyze()

