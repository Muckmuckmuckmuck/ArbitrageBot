#!/usr/bin/env python3
"""
COMPREHENSIVE spread scan - check EVERY crypto on both exchanges
"""

import ccxt
import time
from coinbase_gemini_config import Config

def scan_all_spreads():
    print("Initializing exchanges...")
    cb = ccxt.coinbase({'apiKey': Config.COINBASE_API_KEY, 'secret': Config.COINBASE_SECRET_KEY})
    gem = ccxt.gemini({'apiKey': Config.GEMINI_API_KEY, 'secret': Config.GEMINI_SECRET_KEY})
    
    cb.load_markets()
    gem.load_markets()
    
    # Get ALL common USD pairs (not USDC, not USDT)
    cb_usd = [s for s in cb.markets.keys() if s.endswith('/USD') and '/USDC' not in s and '/USDT' not in s]
    gem_usd = [s for s in gem.markets.keys() if s.endswith('/USD') and '/USDC' not in s and '/USDT' not in s]
    common = sorted(set(cb_usd) & set(gem_usd))
    
    print(f"✅ Found {len(common)} common USD pairs")
    print(f"⏱️  Scanning all pairs (will take ~2 minutes)...\n")
    
    results = []
    errors = []
    
    for i, symbol in enumerate(common, 1):
        try:
            # Fetch tickers
            cb_ticker = cb.fetch_ticker(symbol)
            gem_ticker = gem.fetch_ticker(symbol)
            
            cb_ask = cb_ticker.get('ask')
            cb_bid = cb_ticker.get('bid')
            gem_ask = gem_ticker.get('ask')
            gem_bid = gem_ticker.get('bid')
            
            if not all([cb_ask, cb_bid, gem_ask, gem_bid]):
                errors.append(f"{symbol}: Missing price data")
                continue
            
            # Calculate spreads
            spread_cb_to_gem = ((gem_bid - cb_ask) / cb_ask) * 100
            spread_gem_to_cb = ((cb_bid - gem_ask) / gem_ask) * 100
            best_spread = max(spread_cb_to_gem, spread_gem_to_cb)
            direction = 'CB→GEM' if spread_cb_to_gem > spread_gem_to_cb else 'GEM→CB'
            
            results.append({
                'symbol': symbol,
                'spread': best_spread,
                'direction': direction,
                'cb_ask': cb_ask,
                'cb_bid': cb_bid,
                'gem_ask': gem_ask,
                'gem_bid': gem_bid,
            })
            
            # Progress indicator
            if i % 10 == 0:
                print(f"  Scanned {i}/{len(common)}...")
            
            time.sleep(0.15)  # Rate limit protection
            
        except Exception as e:
            errors.append(f"{symbol}: {str(e)[:50]}")
    
    print(f"\n✅ Scanned {len(results)} cryptos successfully")
    print(f"❌ {len(errors)} errors\n")
    
    # Sort by spread
    results.sort(key=lambda x: x['spread'], reverse=True)
    
    print("=" * 90)
    print("🏆 TOP 30 CRYPTOS BY SPREAD (REAL-TIME)")
    print("=" * 90)
    print(f"{'Rank':<6} {'Symbol':<15} {'Spread':<10} {'Direction':<10} {'CB Ask':<15} {'GEM Bid/Bid':<15}")
    print("-" * 90)
    
    for i, r in enumerate(results[:30], 1):
        marker = '🔥' if r['spread'] > 1.0 else '✅' if r['spread'] > 0.5 else '  '
        price = r['gem_bid'] if r['direction'] == 'CB→GEM' else r['cb_bid']
        print(f"{marker} {i:<4} {r['symbol']:<15} {r['spread']:>6.3f}%    {r['direction']:<10} ${r['cb_ask']:<14.6f} ${price:<14.6f}")
    
    print("=" * 90)
    
    # Show cryptos with spread > 0.5%
    good_spreads = [r for r in results if r['spread'] > 0.5]
    
    print(f"\n💰 CRYPTOS WITH SPREAD > 0.5% ({len(good_spreads)} found):")
    print("-" * 90)
    for r in good_spreads:
        print(f"  🔥 {r['symbol']:<15} {r['spread']:>6.3f}%  {r['direction']}")
    
    print("\n" + "=" * 90)
    print(f"SUMMARY:")
    print(f"  Total scanned: {len(results)}")
    print(f"  Spread > 1.0%: {len([r for r in results if r['spread'] > 1.0])}")
    print(f"  Spread > 0.5%: {len([r for r in results if r['spread'] > 0.5])}")
    print(f"  Spread > 0.3%: {len([r for r in results if r['spread'] > 0.3])}")
    print("=" * 90)

if __name__ == "__main__":
    scan_all_spreads()
