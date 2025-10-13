#!/usr/bin/env python3
"""
Analyze scan results and find the BEST cryptos
Takes absolute value of spreads (we can trade either direction!)
Filters by profitability, volume, and suitability
"""

import re
from collections import defaultdict

# Paste your scan results here (the lines with crypto data)
SCAN_DATA = """
Put the scan output here - I'll parse it
"""

def parse_scan_line(line):
    """Parse a single scan result line"""
    try:
        # Example: [2228/2343] VENOM/USDT      | Spread:  -1.193% | Net:  -1.693% | Profit: $  -1.69 | Vol: $      67,429 | GEM→CB
        match = re.search(r'\[\d+/\d+\]\s+(\S+)\s+\|\s+Spread:\s+([-\d.]+)%\s+\|\s+Net:\s+([-\d.]+)%\s+\|\s+Profit:\s+\$\s+([-\d.]+)\s+\|\s+Vol:\s+\$\s+([\d,]+)\s+\|\s+(\S+)', line)
        
        if match:
            symbol = match.group(1)
            gross_spread = abs(float(match.group(2)))  # Take absolute value!
            net_spread = gross_spread - 0.50  # Recalculate with maker fees
            net_profit = net_spread  # Per $100
            volume = float(match.group(5).replace(',', ''))
            direction = match.group(6)
            
            return {
                'symbol': symbol,
                'gross_spread': gross_spread,
                'net_spread': net_spread,
                'net_profit': net_profit,
                'volume': volume,
                'direction': direction,
            }
    except:
        pass
    return None

def categorize_crypto(symbol):
    """Categorize crypto by type and estimate transfer speed"""
    # Fast transfer cryptos (< 1 min)
    fast_transfer = ['XRP', 'XLM', 'ALGO', 'NANO', 'HBAR', 'IOTA', 'SOL', 'AVAX', 'NEAR', 'FTM', 'ONE', 'MATIC', 'POL']
    
    # Medium transfer (1-5 min)
    medium_transfer = ['LTC', 'BCH', 'DOGE', 'ADA', 'DOT', 'ATOM', 'TRX', 'EOS', 'XTZ', 'DASH']
    
    # Slow transfer (> 5 min)
    slow_transfer = ['BTC', 'ETH', 'ZEC', 'XMR']
    
    # Stablecoins (instant but not useful for arb)
    stablecoins = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'GUSD', 'USDD']
    
    # Fiat pairs (not crypto)
    fiat = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']
    
    base = symbol.split('/')[0]
    
    if any(f in base for f in fiat):
        return 'fiat', 0, False
    elif any(s in base for s in stablecoins):
        return 'stablecoin', 0, False
    elif any(f in base for f in fast_transfer):
        return 'fast', 30, True  # 30 seconds
    elif any(m in base for m in medium_transfer):
        return 'medium', 180, True  # 3 minutes
    elif any(s in base for s in slow_transfer):
        return 'slow', 600, True  # 10 minutes
    else:
        return 'unknown', 120, True  # 2 minutes default

def main():
    print("\n" + "="*100)
    print("🔍 ANALYZING SCAN RESULTS - FINDING PROFITABLE CRYPTOS")
    print("="*100)
    print("💡 Taking ABSOLUTE VALUE of spreads (we can trade either direction!)")
    print("💡 Filtering by: Spread > 0.5% (profitable after 0.50% fees)")
    print("="*100 + "\n")
    
    # Read scan results from stdin or file
    print("Paste your scan results (Ctrl+D when done):")
    print("-"*100)
    
    import sys
    lines = sys.stdin.readlines()
    
    results = []
    for line in lines:
        parsed = parse_scan_line(line)
        if parsed:
            results.append(parsed)
    
    print(f"\n✅ Parsed {len(results)} cryptos from scan results\n")
    
    # Filter profitable cryptos (net spread > 0 after fees)
    profitable = [r for r in results if r['net_spread'] > 0]
    
    print("="*100)
    print(f"💰 PROFITABLE CRYPTOS (Spread > 0.5%, Net Profit > $0)")
    print("="*100)
    print(f"Found {len(profitable)} profitable cryptos!\n")
    
    # Add categorization
    for r in profitable:
        category, transfer_time, is_crypto = categorize_crypto(r['symbol'])
        r['category'] = category
        r['transfer_time'] = transfer_time
        r['is_crypto'] = is_crypto
    
    # Filter out fiat and stablecoins
    crypto_only = [r for r in profitable if r['is_crypto']]
    
    print(f"After removing fiat/stablecoins: {len(crypto_only)} cryptos\n")
    
    # Sort by net profit
    crypto_only.sort(key=lambda x: x['net_profit'], reverse=True)
    
    # Show top 50
    print("="*100)
    print("🏆 TOP 50 PROFITABLE CRYPTOS (Sorted by Net Profit)")
    print("="*100)
    print(f"{'Rank':<6} {'Symbol':<20} {'Gross Spread':<14} {'Net Profit':<12} {'Volume':<15} {'Transfer':<12}")
    print("-"*100)
    
    for i, r in enumerate(crypto_only[:50], 1):
        marker = '🔥' if r['net_profit'] > 1.0 else '✅' if r['net_profit'] > 0.5 else '⚠️'
        print(f"{marker} {i:<4} {r['symbol']:<20} {r['gross_spread']:>6.3f}%        ${r['net_profit']:>6.2f}      ${r['volume']:>12,.0f}  {r['category']:<10}")
    
    print("="*100 + "\n")
    
    # Filter by criteria
    print("="*100)
    print("🎯 FILTERING BY QUALITY CRITERIA")
    print("="*100)
    
    # Excellent: High profit + good volume + fast transfer
    excellent = [
        r for r in crypto_only 
        if r['net_profit'] > 0.5 
        and r['volume'] > 10000 
        and r['transfer_time'] < 300
    ]
    
    # Good: Medium profit + decent volume
    good = [
        r for r in crypto_only 
        if 0.2 < r['net_profit'] <= 0.5 
        and r['volume'] > 5000
    ]
    
    # Marginal: Low profit but high volume
    marginal = [
        r for r in crypto_only 
        if 0.05 < r['net_profit'] <= 0.2 
        and r['volume'] > 50000
    ]
    
    print(f"🔥 EXCELLENT (Profit > $0.50, Vol > $10k, Fast transfer): {len(excellent)}")
    print(f"✅ GOOD (Profit $0.20-$0.50, Vol > $5k): {len(good)}")
    print(f"⚠️  MARGINAL (Profit $0.05-$0.20, Vol > $50k): {len(marginal)}")
    print("="*100 + "\n")
    
    # Show excellent opportunities
    if excellent:
        print("="*100)
        print("🔥 EXCELLENT OPPORTUNITIES")
        print("="*100)
        for r in excellent:
            print(f"  🔥 {r['symbol']:<20} Profit: ${r['net_profit']:>5.2f} | Spread: {r['gross_spread']:>5.3f}% | Vol: ${r['volume']:>12,.0f} | Transfer: {r['transfer_time']}s")
        print("="*100 + "\n")
    
    # Show good opportunities
    if good:
        print("="*100)
        print("✅ GOOD OPPORTUNITIES")
        print("="*100)
        for r in good[:20]:  # Top 20
            print(f"  ✅ {r['symbol']:<20} Profit: ${r['net_profit']:>5.2f} | Spread: {r['gross_spread']:>5.3f}% | Vol: ${r['volume']:>12,.0f} | Transfer: {r['transfer_time']}s")
        print("="*100 + "\n")
    
    # Final recommendations
    recommended = excellent + good[:10]  # Top 10 from good
    
    if recommended:
        print("="*100)
        print("🚀 FINAL RECOMMENDATIONS FOR BOT")
        print("="*100)
        print(f"\nTop {len(recommended)} cryptos for arbitrage:\n")
        print("CURRENCY_PAIRS = [")
        for r in recommended:
            print(f"    '{r['symbol']}',  # Profit: ${r['net_profit']:.2f}, Spread: {r['gross_spread']:.3f}%, Vol: ${r['volume']:,.0f}, Transfer: {r['transfer_time']}s")
        print("]\n")
        print("="*100)
    else:
        print("="*100)
        print("❌ NO CRYPTOS MEET ALL CRITERIA")
        print("="*100)
        print("Try lowering thresholds or checking market conditions.")
    
    print("\n")

if __name__ == "__main__":
    main()

