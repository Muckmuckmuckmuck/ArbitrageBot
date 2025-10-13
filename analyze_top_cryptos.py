#!/usr/bin/env python3
"""
Analyze top spread cryptos for liquidity, volume, and suitability
"""

import ccxt
import time

# Top cryptos by spread
TOP_CRYPTOS = [
    'EUL/USD',       # 0.725%
    'CTX/USD',       # 0.670%
    'FARTCOIN/USD',  # 0.590%
    'IOTX/USD',      # 0.357%
    'FET/USD',       # 0.197%
    'TRUMP/USD',     # 0.116%
    'GMT/USD',       # 0.096%
    'PUMP/USD',      # 0.087%
    'ARB/USD',       # 0.056%
    'POL/USD',       # 0.067%
]

def analyze_crypto(symbol, cb, gem):
    """Analyze a crypto for arbitrage suitability"""
    try:
        cb_ticker = cb.fetch_ticker(symbol)
        time.sleep(0.1)
        gem_ticker = gem.fetch_ticker(symbol)
        time.sleep(0.1)
        
        # Get order book depth
        try:
            cb_book = cb.fetch_order_book(symbol, limit=10)
            time.sleep(0.1)
            gem_book = gem.fetch_order_book(symbol, limit=10)
            time.sleep(0.1)
            
            # Calculate liquidity (top 5 levels)
            cb_bid_liquidity = sum([bid[1] for bid in cb_book['bids'][:5]]) if cb_book['bids'] else 0
            cb_ask_liquidity = sum([ask[1] for ask in cb_book['asks'][:5]]) if cb_book['asks'] else 0
            gem_bid_liquidity = sum([bid[1] for bid in gem_book['bids'][:5]]) if gem_book['bids'] else 0
            gem_ask_liquidity = sum([ask[1] for ask in gem_book['asks'][:5]]) if gem_book['asks'] else 0
            
            total_liquidity = cb_bid_liquidity + cb_ask_liquidity + gem_bid_liquidity + gem_ask_liquidity
        except:
            total_liquidity = 0
        
        # Get spread
        cb_ask = cb_ticker.get('ask')
        cb_bid = cb_ticker.get('bid')
        gem_ask = gem_ticker.get('ask')
        gem_bid = gem_ticker.get('bid')
        
        if not all([cb_ask, cb_bid, gem_ask, gem_bid]):
            return None
        
        spread_cb_to_gem = ((gem_bid - cb_ask) / cb_ask) * 100
        spread_gem_to_cb = ((cb_bid - gem_ask) / gem_ask) * 100
        best_spread = max(spread_cb_to_gem, spread_gem_to_cb)
        direction = 'CB→GEM' if spread_cb_to_gem > spread_gem_to_cb else 'GEM→CB'
        
        # Get volume
        cb_vol = cb_ticker.get('quoteVolume') or cb_ticker.get('baseVolume') or 0
        gem_vol = gem_ticker.get('quoteVolume') or gem_ticker.get('baseVolume') or 0
        total_volume = cb_vol + gem_vol
        
        return {
            'symbol': symbol,
            'spread': best_spread,
            'direction': direction,
            'volume_24h': total_volume,
            'liquidity': total_liquidity,
            'cb_ask': cb_ask,
            'gem_bid': gem_bid,
            'price': cb_ask,
        }
        
    except Exception as e:
        print(f"  ❌ Error analyzing {symbol}: {str(e)[:60]}")
        return None

def main():
    print("\n" + "="*100)
    print("🔬 DETAILED ANALYSIS OF TOP SPREAD CRYPTOS")
    print("="*100 + "\n")
    
    cb = ccxt.coinbase({'enableRateLimit': True})
    gem = ccxt.gemini({'enableRateLimit': True})
    
    cb.load_markets()
    gem.load_markets()
    
    results = []
    
    print("Analyzing cryptos...\n")
    for symbol in TOP_CRYPTOS:
        print(f"  📊 {symbol}...")
        result = analyze_crypto(symbol, cb, gem)
        if result:
            results.append(result)
    
    print("\n" + "="*100)
    print("📊 DETAILED RESULTS")
    print("="*100)
    print(f"{'Symbol':<15} {'Spread':<10} {'Volume (24h)':<15} {'Liquidity':<12} {'Price':<12} {'Direction':<10}")
    print("-"*100)
    
    for r in results:
        marker = '🔥' if r['spread'] > 0.5 else '✅' if r['spread'] > 0.2 else '  '
        print(f"{marker} {r['symbol']:<13} {r['spread']:>6.3f}%    ${r['volume_24h']:>12,.0f}   {r['liquidity']:>10.2f}    ${r['price']:<10.4f}  {r['direction']}")
    
    print("="*100)
    
    # Filter recommendations
    print("\n" + "="*100)
    print("🎯 RECOMMENDATIONS FOR BOT")
    print("="*100)
    
    # High spread + decent volume
    good_cryptos = [r for r in results if r['spread'] > 0.3 and r['volume_24h'] > 1000]
    
    print(f"\n✅ EXCELLENT (Spread > 0.3% + Volume > $1k): {len(good_cryptos)}")
    for r in good_cryptos:
        print(f"  🔥 {r['symbol']:<15} Spread: {r['spread']:.3f}%  Vol: ${r['volume_24h']:>12,.0f}")
    
    # Moderate spread
    moderate = [r for r in results if 0.1 <= r['spread'] <= 0.3 and r['volume_24h'] > 1000]
    
    print(f"\n⚠️  GOOD (Spread 0.1-0.3% + Volume > $1k): {len(moderate)}")
    for r in moderate:
        print(f"  ✅ {r['symbol']:<15} Spread: {r['spread']:.3f}%  Vol: ${r['volume_24h']:>12,.0f}")
    
    # Final recommendation
    all_good = good_cryptos + moderate
    
    print("\n" + "="*100)
    print("🚀 FINAL RECOMMENDED CONFIG")
    print("="*100 + "\n")
    
    if all_good:
        print("TRADING_PAIRS = [")
        for r in all_good:
            print(f"    '{r['symbol']}',  # Spread: {r['spread']:.3f}%, Vol: ${r['volume_24h']:,.0f}")
        print("]\n")
        
        print("💡 NOTES:")
        print(f"  - Total pairs: {len(all_good)}")
        print(f"  - Avg spread: {sum([r['spread'] for r in all_good])/len(all_good):.3f}%")
        print(f"  - These have REAL spreads (not negative)")
        print(f"  - All are available on both Coinbase & Gemini")
    else:
        print("❌ No cryptos meet the criteria")
    
    print("\n" + "="*100 + "\n")

if __name__ == "__main__":
    main()

