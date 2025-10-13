#!/usr/bin/env python3
"""
Simple public API scan - no authentication needed
"""

import ccxt
import time

def scan_public():
    print("\n" + "="*100)
    print("🔍 SCANNING ALL CRYPTOS (PUBLIC API - NO AUTH)")
    print("="*100 + "\n")
    
    # Initialize exchanges WITHOUT API keys (public data only)
    cb = ccxt.coinbase({'enableRateLimit': True})
    gem = ccxt.gemini({'enableRateLimit': True})
    
    print("Loading markets...")
    cb.load_markets()
    gem.load_markets()
    
    # Get common USD pairs
    cb_usd = [s for s in cb.markets.keys() if s.endswith('/USD') and not any(x in s for x in ['USDC', 'USDT', 'DAI'])]
    gem_usd = [s for s in gem.markets.keys() if s.endswith('/USD') and not any(x in s for x in ['USDC', 'USDT', 'DAI'])]
    common = sorted(set(cb_usd) & set(gem_usd))
    
    print(f"✅ Found {len(common)} common USD pairs\n")
    print(f"Pairs to scan: {', '.join(common[:20])}...\n")
    
    results = []
    errors = []
    
    for i, symbol in enumerate(common, 1):
        try:
            # Fetch public ticker data
            cb_ticker = cb.fetch_ticker(symbol)
            time.sleep(0.15)
            gem_ticker = gem.fetch_ticker(symbol)
            time.sleep(0.15)
            
            cb_ask = cb_ticker.get('ask')
            cb_bid = cb_ticker.get('bid')
            gem_ask = gem_ticker.get('ask')
            gem_bid = gem_ticker.get('bid')
            
            if not all([cb_ask, cb_bid, gem_ask, gem_bid]):
                errors.append(f"{symbol}: Missing prices")
                continue
            
            # Calculate spreads
            spread_cb_to_gem = ((gem_bid - cb_ask) / cb_ask) * 100
            spread_gem_to_cb = ((cb_bid - gem_ask) / gem_ask) * 100
            best_spread = max(spread_cb_to_gem, spread_gem_to_cb)
            direction = 'CB→GEM' if spread_cb_to_gem > spread_gem_to_cb else 'GEM→CB'
            
            cb_vol = cb_ticker.get('quoteVolume') or cb_ticker.get('baseVolume') or 0
            gem_vol = gem_ticker.get('quoteVolume') or gem_ticker.get('baseVolume') or 0
            volume = cb_vol + gem_vol
            
            results.append({
                'symbol': symbol,
                'spread': best_spread,
                'direction': direction,
                'cb_ask': cb_ask,
                'cb_bid': cb_bid,
                'gem_ask': gem_ask,
                'gem_bid': gem_bid,
                'volume': volume,
            })
            
            if i % 10 == 0:
                print(f"  Scanned {i}/{len(common)}...")
            
        except Exception as e:
            errors.append(f"{symbol}: {str(e)[:50]}")
            if i <= 5:  # Show first few errors for debugging
                print(f"  ❌ {symbol}: {str(e)[:80]}")
    
    print(f"\n✅ Scanned {len(results)} successfully")
    print(f"❌ {len(errors)} errors\n")
    
    # Sort by spread
    results.sort(key=lambda x: x['spread'], reverse=True)
    
    print("="*100)
    print("🏆 TOP 30 CRYPTOS BY SPREAD")
    print("="*100)
    print(f"{'#':<5} {'Symbol':<15} {'Spread':<12} {'Direction':<12} {'CB Ask':<15} {'GEM Bid':<15}")
    print("-"*100)
    
    for i, r in enumerate(results[:30], 1):
        marker = '🔥' if r['spread'] > 0.5 else '✅' if r['spread'] > 0.2 else '  '
        print(f"{marker}{i:<4} {r['symbol']:<15} {r['spread']:>7.3f}%     {r['direction']:<12} ${r['cb_ask']:<14.4f} ${r['gem_bid']:<14.4f}")
    
    print("="*100)
    
    # Show best opportunities
    good = [r for r in results if r['spread'] > 0.3]
    print(f"\n💰 CRYPTOS WITH SPREAD > 0.3%: {len(good)}")
    if good:
        for r in good:
            print(f"  🔥 {r['symbol']:<15} {r['spread']:>6.3f}%  {r['direction']}")
    else:
        print("  ❌ None found")
    
    print("\n" + "="*100)
    print("SUMMARY:")
    print(f"  Spread > 0.5%: {len([r for r in results if r['spread'] > 0.5])}")
    print(f"  Spread > 0.3%: {len([r for r in results if r['spread'] > 0.3])}")
    print(f"  Spread > 0.2%: {len([r for r in results if r['spread'] > 0.2])}")
    print(f"  Spread > 0.1%: {len([r for r in results if r['spread'] > 0.1])}")
    print("="*100 + "\n")
    
    # Show top 15 for config
    if results[:15]:
        print("🎯 TOP 15 FOR CONFIG:")
        print("\nTRADING_PAIRS = [")
        for r in results[:15]:
            print(f"    '{r['symbol']}',  # Spread: {r['spread']:.3f}%")
        print("]\n")

if __name__ == "__main__":
    scan_public()

