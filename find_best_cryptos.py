#!/usr/bin/env python3
"""
COMPREHENSIVE CRYPTO SCANNER
Find the BEST cryptos for arbitrage between Coinbase & Gemini
"""

import ccxt
import time
from coinbase_gemini_config import Config

def scan_all_cryptos():
    print("\n" + "="*100)
    print("🔍 COMPREHENSIVE CRYPTO SCANNER - FINDING BEST ARBITRAGE OPPORTUNITIES")
    print("="*100 + "\n")
    
    print("Initializing exchanges...")
    cb = ccxt.coinbase({
        'apiKey': Config.COINBASE_API_KEY,
        'secret': Config.COINBASE_SECRET_KEY,
        'enableRateLimit': True
    })
    gem = ccxt.gemini({
        'apiKey': Config.GEMINI_API_KEY,
        'secret': Config.GEMINI_SECRET_KEY,
        'enableRateLimit': True
    })
    
    cb.load_markets()
    gem.load_markets()
    
    # Get ALL common USD pairs (exclude stablecoins)
    cb_usd = [s for s in cb.markets.keys() if s.endswith('/USD') and not any(stable in s for stable in ['USDC', 'USDT', 'DAI', 'BUSD'])]
    gem_usd = [s for s in gem.markets.keys() if s.endswith('/USD') and not any(stable in s for stable in ['USDC', 'USDT', 'DAI', 'BUSD'])]
    common = sorted(set(cb_usd) & set(gem_usd))
    
    print(f"✅ Found {len(common)} common USD pairs")
    print(f"⏱️  Scanning all pairs (this will take ~2-3 minutes)...\n")
    
    results = []
    errors = []
    scanned = 0
    
    for i, symbol in enumerate(common, 1):
        try:
            # Fetch tickers with rate limiting
            cb_ticker = cb.fetch_ticker(symbol)
            time.sleep(0.1)  # Rate limit protection
            gem_ticker = gem.fetch_ticker(symbol)
            time.sleep(0.1)
            
            cb_ask = cb_ticker.get('ask')
            cb_bid = cb_ticker.get('bid')
            gem_ask = gem_ticker.get('ask')
            gem_bid = gem_ticker.get('bid')
            
            if not all([cb_ask, cb_bid, gem_ask, gem_bid]):
                errors.append(f"{symbol}: Missing price data")
                continue
            
            # Calculate spreads both directions
            spread_cb_to_gem = ((gem_bid - cb_ask) / cb_ask) * 100
            spread_gem_to_cb = ((cb_bid - gem_ask) / gem_ask) * 100
            best_spread = max(spread_cb_to_gem, spread_gem_to_cb)
            direction = 'CB→GEM' if spread_cb_to_gem > spread_gem_to_cb else 'GEM→CB'
            
            # Get volume data
            cb_volume = cb_ticker.get('quoteVolume', 0)
            gem_volume = gem_ticker.get('quoteVolume', 0)
            total_volume = cb_volume + gem_volume
            
            results.append({
                'symbol': symbol,
                'spread': best_spread,
                'direction': direction,
                'cb_ask': cb_ask,
                'cb_bid': cb_bid,
                'gem_ask': gem_ask,
                'gem_bid': gem_bid,
                'volume': total_volume,
                'cb_volume': cb_volume,
                'gem_volume': gem_volume,
            })
            
            scanned += 1
            
            # Progress indicator
            if i % 10 == 0:
                print(f"  📊 Scanned {i}/{len(common)} pairs...")
            
        except Exception as e:
            errors.append(f"{symbol}: {str(e)[:60]}")
    
    print(f"\n✅ Successfully scanned {scanned} cryptos")
    print(f"❌ {len(errors)} errors\n")
    
    # Sort by spread (descending)
    results.sort(key=lambda x: x['spread'], reverse=True)
    
    print("\n" + "="*100)
    print("🏆 TOP 40 CRYPTOS BY SPREAD (REAL-TIME DATA)")
    print("="*100)
    print(f"{'Rank':<6} {'Symbol':<15} {'Spread':<12} {'Direction':<12} {'CB Ask':<15} {'GEM Bid':<15} {'Volume (24h)':<15}")
    print("-"*100)
    
    for i, r in enumerate(results[:40], 1):
        marker = '🔥' if r['spread'] > 1.0 else '✅' if r['spread'] > 0.5 else '⚠️' if r['spread'] > 0.2 else '  '
        price_sell = r['gem_bid'] if r['direction'] == 'CB→GEM' else r['cb_bid']
        price_buy = r['cb_ask'] if r['direction'] == 'CB→GEM' else r['gem_ask']
        
        print(f"{marker} {i:<4} {r['symbol']:<15} {r['spread']:>7.3f}%     {r['direction']:<12} ${price_buy:<14.4f} ${price_sell:<14.4f} ${r['volume']:>12,.0f}")
    
    print("="*100)
    
    # Show profitable opportunities
    profitable = [r for r in results if r['spread'] > 0.5]
    moderate = [r for r in results if 0.2 < r['spread'] <= 0.5]
    
    print(f"\n💰 PROFITABLE OPPORTUNITIES (Spread > 0.5%): {len(profitable)}")
    print("-"*100)
    if profitable:
        for r in profitable:
            print(f"  🔥 {r['symbol']:<15} {r['spread']:>6.3f}%  {r['direction']:<10} Vol: ${r['volume']:>12,.0f}")
    else:
        print("  ❌ No cryptos with spread > 0.5% found")
    
    print(f"\n⚠️  MODERATE OPPORTUNITIES (Spread 0.2-0.5%): {len(moderate)}")
    print("-"*100)
    if moderate:
        for r in moderate[:15]:  # Show top 15
            print(f"  ⚠️  {r['symbol']:<15} {r['spread']:>6.3f}%  {r['direction']:<10} Vol: ${r['volume']:>12,.0f}")
    else:
        print("  ❌ No cryptos with spread 0.2-0.5% found")
    
    print("\n" + "="*100)
    print("📊 SUMMARY STATISTICS")
    print("="*100)
    print(f"  Total cryptos scanned:     {scanned}")
    print(f"  Spread > 1.0%:             {len([r for r in results if r['spread'] > 1.0])}")
    print(f"  Spread > 0.5%:             {len([r for r in results if r['spread'] > 0.5])}")
    print(f"  Spread > 0.3%:             {len([r for r in results if r['spread'] > 0.3])}")
    print(f"  Spread > 0.2%:             {len([r for r in results if r['spread'] > 0.2])}")
    print(f"  Spread > 0.1%:             {len([r for r in results if r['spread'] > 0.1])}")
    print(f"  Negative spreads:          {len([r for r in results if r['spread'] < 0])}")
    print("="*100)
    
    # Show recommended cryptos
    print("\n" + "="*100)
    print("🎯 RECOMMENDED CRYPTOS FOR BOT (Top 15 by spread)")
    print("="*100)
    recommended = results[:15]
    if recommended:
        crypto_list = [r['symbol'] for r in recommended]
        print("\nAdd these to your config:\n")
        print("TRADING_PAIRS = [")
        for crypto in crypto_list:
            print(f"    '{crypto}',")
        print("]\n")
        
        print("Spread details:")
        for r in recommended:
            print(f"  {r['symbol']:<15} Spread: {r['spread']:>6.3f}%  Volume: ${r['volume']:>12,.0f}")
    
    print("="*100 + "\n")

if __name__ == "__main__":
    scan_all_cryptos()

