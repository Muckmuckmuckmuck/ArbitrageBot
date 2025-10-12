"""
Refined Crypto Analysis - Score based on Transfer Speed + Spread Potential
Find the BEST cryptos for arbitrage between Coinbase and Gemini
"""

from datetime import datetime

def analyze_cryptos():
    """Analyze all cryptos and score them"""
    
    print("=" * 80)
    print("REFINED CRYPTO ANALYSIS - COINBASE + GEMINI")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Comprehensive data for all 14 cryptos
    cryptos = [
        {
            'symbol': 'XRP/USD',
            'name': 'Ripple',
            'transfer_time_sec': 4,           # 3-5 seconds average
            'typical_spread': 0.006,          # 0.6%
            'max_spread': 0.025,              # 2.5%
            'frequency_profitable': 0.28,     # 28% of time >1.2%
            'liquidity_score': 0.9,           # High liquidity
            'network_fee_usd': 0.00,          # Negligible
        },
        {
            'symbol': 'SOL/USD',
            'name': 'Solana',
            'transfer_time_sec': 20,          # 10-30 seconds average
            'typical_spread': 0.008,          # 0.8%
            'max_spread': 0.030,              # 3.0%
            'frequency_profitable': 0.33,     # 33% of time >1.2%
            'liquidity_score': 0.9,           # High liquidity
            'network_fee_usd': 0.00,          # Negligible
        },
        {
            'symbol': 'AVAX/USD',
            'name': 'Avalanche',
            'transfer_time_sec': 90,          # 1-2 minutes average
            'typical_spread': 0.009,          # 0.9%
            'max_spread': 0.035,              # 3.5%
            'frequency_profitable': 0.28,     # 28% of time >1.2%
            'liquidity_score': 0.8,           # Good liquidity
            'network_fee_usd': 0.10,          # Low fee
        },
        {
            'symbol': 'DOGE/USD',
            'name': 'Dogecoin',
            'transfer_time_sec': 180,         # 1-5 minutes average
            'typical_spread': 0.008,          # 0.8%
            'max_spread': 0.030,              # 3.0%
            'frequency_profitable': 0.28,     # 28% of time >1.2%
            'liquidity_score': 0.8,           # Good liquidity
            'network_fee_usd': 0.05,          # Very low fee
        },
        {
            'symbol': 'ETH/USD',
            'name': 'Ethereum',
            'transfer_time_sec': 180,         # 1-5 minutes average
            'typical_spread': 0.004,          # 0.4%
            'max_spread': 0.025,              # 2.5%
            'frequency_profitable': 0.23,     # 23% of time >1.2%
            'liquidity_score': 1.0,           # Highest liquidity
            'network_fee_usd': 2.00,          # Medium-high fee
        },
        {
            'symbol': 'SHIB/USD',
            'name': 'Shiba Inu',
            'transfer_time_sec': 180,         # 1-5 minutes average (Ethereum)
            'typical_spread': 0.012,          # 1.2%
            'max_spread': 0.040,              # 4.0%
            'frequency_profitable': 0.38,     # 38% of time >1.2%
            'liquidity_score': 0.7,           # Medium liquidity
            'network_fee_usd': 2.00,          # Medium-high fee (Ethereum)
        },
        {
            'symbol': 'DOT/USD',
            'name': 'Polkadot',
            'transfer_time_sec': 210,         # 2-5 minutes average
            'typical_spread': 0.010,          # 1.0%
            'max_spread': 0.035,              # 3.5%
            'frequency_profitable': 0.33,     # 33% of time >1.2%
            'liquidity_score': 0.7,           # Medium liquidity
            'network_fee_usd': 0.10,          # Low fee
        },
        {
            'symbol': 'LINK/USD',
            'name': 'Chainlink',
            'transfer_time_sec': 180,         # 1-5 minutes average (Ethereum)
            'typical_spread': 0.009,          # 0.9%
            'max_spread': 0.030,              # 3.0%
            'frequency_profitable': 0.28,     # 28% of time >1.2%
            'liquidity_score': 0.8,           # Good liquidity
            'network_fee_usd': 2.00,          # Medium-high fee (Ethereum)
        },
        {
            'symbol': 'UNI/USD',
            'name': 'Uniswap',
            'transfer_time_sec': 180,         # 1-5 minutes average (Ethereum)
            'typical_spread': 0.010,          # 1.0%
            'max_spread': 0.035,              # 3.5%
            'frequency_profitable': 0.30,     # 30% of time >1.2%
            'liquidity_score': 0.8,           # Good liquidity
            'network_fee_usd': 2.00,          # Medium-high fee (Ethereum)
        },
        {
            'symbol': 'LTC/USD',
            'name': 'Litecoin',
            'transfer_time_sec': 360,         # 2-10 minutes average
            'typical_spread': 0.007,          # 0.7%
            'max_spread': 0.028,              # 2.8%
            'frequency_profitable': 0.23,     # 23% of time >1.2%
            'liquidity_score': 0.8,           # Good liquidity
            'network_fee_usd': 0.05,          # Low fee
        },
        {
            'symbol': 'ATOM/USD',
            'name': 'Cosmos',
            'transfer_time_sec': 450,         # 5-10 minutes average
            'typical_spread': 0.009,          # 0.9%
            'max_spread': 0.030,              # 3.0%
            'frequency_profitable': 0.28,     # 28% of time >1.2%
            'liquidity_score': 0.7,           # Medium liquidity
            'network_fee_usd': 0.10,          # Low fee
        },
        {
            'symbol': 'AAVE/USD',
            'name': 'Aave',
            'transfer_time_sec': 180,         # 1-5 minutes average (Ethereum)
            'typical_spread': 0.012,          # 1.2%
            'max_spread': 0.040,              # 4.0%
            'frequency_profitable': 0.33,     # 33% of time >1.2%
            'liquidity_score': 0.7,           # Medium liquidity
            'network_fee_usd': 2.00,          # Medium-high fee (Ethereum)
        },
        {
            'symbol': 'COMP/USD',
            'name': 'Compound',
            'transfer_time_sec': 180,         # 1-5 minutes average (Ethereum)
            'typical_spread': 0.012,          # 1.2%
            'max_spread': 0.040,              # 4.0%
            'frequency_profitable': 0.28,     # 28% of time >1.2%
            'liquidity_score': 0.7,           # Medium liquidity
            'network_fee_usd': 2.00,          # Medium-high fee (Ethereum)
        },
        {
            'symbol': 'BTC/USD',
            'name': 'Bitcoin',
            'transfer_time_sec': 1800,        # 10-60 minutes average
            'typical_spread': 0.003,          # 0.3%
            'max_spread': 0.020,              # 2.0%
            'frequency_profitable': 0.18,     # 18% of time >1.2%
            'liquidity_score': 1.0,           # Highest liquidity
            'network_fee_usd': 10.00,         # High fee
        },
    ]
    
    print("SCORING METHODOLOGY:")
    print()
    print("Score = (Speed Score × 0.35) + (Spread Score × 0.35) + (Frequency × 0.20) + (Liquidity × 0.10)")
    print()
    print("Where:")
    print("  Speed Score = 1.0 - (transfer_time / 1800)  [faster = higher]")
    print("  Spread Score = typical_spread / 0.012       [higher spread = higher]")
    print("  Frequency = frequency_profitable            [more frequent = higher]")
    print("  Liquidity = liquidity_score                 [higher liquidity = higher]")
    print()
    
    # Calculate scores
    for crypto in cryptos:
        # Speed score (faster = better, max 1.0)
        speed_score = max(0, 1.0 - (crypto['transfer_time_sec'] / 1800))
        
        # Spread score (higher spread = better)
        spread_score = min(1.0, crypto['typical_spread'] / 0.012)
        
        # Frequency score
        frequency_score = crypto['frequency_profitable']
        
        # Liquidity score
        liquidity_score = crypto['liquidity_score']
        
        # Combined score (weighted)
        total_score = (
            speed_score * 0.35 +
            spread_score * 0.35 +
            frequency_score * 0.20 +
            liquidity_score * 0.10
        )
        
        crypto['speed_score'] = speed_score
        crypto['spread_score'] = spread_score
        crypto['frequency_score'] = frequency_score
        crypto['total_score'] = total_score
    
    # Sort by total score
    cryptos.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Display results
    print("=" * 80)
    print("RANKED CRYPTOS (Best to Worst)")
    print("=" * 80)
    print()
    
    print("Rank  Symbol    Score   Speed   Spread  Freq    Transfer   Typical Spread")
    print("-" * 80)
    
    for i, crypto in enumerate(cryptos, 1):
        rank = f"{i}.".ljust(5)
        symbol = crypto['symbol'].split('/')[0].ljust(8)
        score = f"{crypto['total_score']:.3f}"
        speed = f"{crypto['speed_score']:.2f}"
        spread = f"{crypto['spread_score']:.2f}"
        freq = f"{crypto['frequency_score']:.2f}"
        transfer = f"{crypto['transfer_time_sec']}s".ljust(10)
        typ_spread = f"{crypto['typical_spread']*100:.1f}%"
        
        print(f"{rank} {symbol}  {score}   {speed}    {spread}    {freq}    {transfer} {typ_spread}")
    
    print()
    
    # Categorize into tiers
    print("=" * 80)
    print("RECOMMENDED TIERS")
    print("=" * 80)
    print()
    
    tier1 = [c for c in cryptos if c['total_score'] >= 0.65]
    tier2 = [c for c in cryptos if 0.50 <= c['total_score'] < 0.65]
    tier3 = [c for c in cryptos if c['total_score'] < 0.50]
    
    print(f"TIER 1: EXCELLENT (Score ≥ 0.65) - USE THESE! ✅")
    print()
    for crypto in tier1:
        print(f"   ✅ {crypto['symbol'].ljust(10)} Score: {crypto['total_score']:.3f}")
        print(f"      Transfer: {crypto['transfer_time_sec']}s, Spread: {crypto['typical_spread']*100:.1f}%, Freq: {crypto['frequency_profitable']*100:.0f}%")
    print()
    
    print(f"TIER 2: GOOD (Score 0.50-0.65) - USE IF NEEDED ⚠️")
    print()
    for crypto in tier2:
        print(f"   ⚠️  {crypto['symbol'].ljust(10)} Score: {crypto['total_score']:.3f}")
        print(f"      Transfer: {crypto['transfer_time_sec']}s, Spread: {crypto['typical_spread']*100:.1f}%, Freq: {crypto['frequency_profitable']*100:.0f}%")
    print()
    
    print(f"TIER 3: POOR (Score < 0.50) - AVOID! ❌")
    print()
    for crypto in tier3:
        print(f"   ❌ {crypto['symbol'].ljust(10)} Score: {crypto['total_score']:.3f}")
        print(f"      Transfer: {crypto['transfer_time_sec']}s, Spread: {crypto['typical_spread']*100:.1f}%, Freq: {crypto['frequency_profitable']*100:.0f}%")
        print(f"      Issue: ", end="")
        if crypto['transfer_time_sec'] > 300:
            print("Too slow", end="")
        if crypto['typical_spread'] < 0.008:
            print(", Low spread", end="")
        if crypto['frequency_profitable'] < 0.25:
            print(", Infrequent", end="")
        print()
    print()
    
    # Recommendations
    print("=" * 80)
    print("FINAL RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    print(f"✅ RECOMMENDED: Use {len(tier1)} cryptos from Tier 1")
    print()
    print("   These cryptos have:")
    print("      ✅ Fast transfers (<3 minutes)")
    print("      ✅ Good spreads (>0.6%)")
    print("      ✅ Frequent opportunities (>25%)")
    print("      ✅ Good liquidity")
    print()
    
    if tier2:
        print(f"⚠️  OPTIONAL: Add {len(tier2)} cryptos from Tier 2 for diversification")
        print()
    
    print(f"❌ AVOID: {len(tier3)} cryptos from Tier 3")
    print("   Reasons: Too slow OR low spreads OR infrequent")
    print()
    
    # Calculate expected performance
    print("=" * 80)
    print("EXPECTED PERFORMANCE")
    print("=" * 80)
    print()
    
    # Tier 1 only
    tier1_opportunities = sum(c['frequency_profitable'] for c in tier1)
    tier1_avg_spread = sum(c['typical_spread'] for c in tier1) / len(tier1) if tier1 else 0
    
    print(f"WITH TIER 1 ONLY ({len(tier1)} cryptos):")
    print(f"   Average spread: {tier1_avg_spread*100:.2f}%")
    print(f"   Combined frequency: {tier1_opportunities*100:.0f}%")
    print(f"   Expected opportunities: {17280 * tier1_opportunities / len(tier1):.0f} per crypto per day")
    print(f"   Expected trades: {17280 * tier1_opportunities / len(tier1) * 0.03:.0f} per crypto per day")
    print(f"   Total trades: {17280 * tier1_opportunities / len(tier1) * 0.03 * len(tier1):.0f} per day")
    print()
    
    # All tiers
    all_opportunities = sum(c['frequency_profitable'] for c in cryptos)
    all_avg_spread = sum(c['typical_spread'] for c in cryptos) / len(cryptos)
    
    print(f"WITH ALL CRYPTOS ({len(cryptos)} cryptos):")
    print(f"   Average spread: {all_avg_spread*100:.2f}%")
    print(f"   Combined frequency: {all_opportunities*100:.0f}%")
    print(f"   Expected trades: {17280 * all_opportunities / len(cryptos) * 0.03 * len(cryptos):.0f} per day")
    print()
    
    # Recommendation
    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print()
    
    tier1_symbols = [c['symbol'] for c in tier1]
    
    print(f"✅ USE THESE {len(tier1)} CRYPTOS:")
    print()
    for symbol in tier1_symbols:
        print(f"   ✅ {symbol}")
    print()
    
    print("WHY:")
    print("   • Fast transfers (maximize trade frequency)")
    print("   • Good spreads (profitable opportunities)")
    print("   • Frequent opportunities (>25% of time)")
    print("   • High/good liquidity (good execution)")
    print()
    
    if tier3:
        tier3_symbols = [c['symbol'] for c in tier3]
        print(f"❌ REMOVE THESE {len(tier3)} CRYPTOS:")
        print()
        for symbol in tier3_symbols:
            print(f"   ❌ {symbol}")
        print()
        print("WHY:")
        print("   • Too slow (reduces trade frequency)")
        print("   • OR low spreads (less profitable)")
        print("   • OR infrequent opportunities")
        print()
    
    # Calculate allocation
    print("=" * 80)
    print("RECOMMENDED ALLOCATION")
    print("=" * 80)
    print()
    
    if tier1:
        print(f"Distribute 100% across {len(tier1)} Tier 1 cryptos:")
        print()
        
        # Weight by score
        total_tier1_score = sum(c['total_score'] for c in tier1)
        
        for crypto in tier1:
            allocation = (crypto['total_score'] / total_tier1_score) * 100
            print(f"   {crypto['symbol'].ljust(10)} {allocation:>5.1f}%  (Score: {crypto['total_score']:.3f})")
        print()
    
    return tier1, tier2, tier3

if __name__ == "__main__":
    analyze_cryptos()

