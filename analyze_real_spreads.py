#!/usr/bin/env python3
"""
Analyze REAL spreads on Coinbase + Gemini
Find cryptos with: High spreads + Fast transfers + Good liquidity
"""

import ccxt
import asyncio
import time
from coinbase_gemini_config import Config

# Transfer time estimates (in seconds)
TRANSFER_TIMES = {
    # Ultra-fast (< 1 min)
    'XRP': 4, 'SOL': 20, 'ALGO': 5, 'XLM': 5, 'TRX': 3,
    
    # Very fast (1-3 min)
    'AVAX': 90, 'MATIC': 120, 'DOT': 60, 'ATOM': 60, 'NEAR': 60,
    'ARB': 120, 'OP': 120, 'FTM': 60,
    
    # Fast (3-10 min)
    'DOGE': 180, 'LTC': 150, 'BCH': 180, 'LINK': 180, 'UNI': 180,
    'AAVE': 180, 'COMP': 180, 'SUSHI': 180, 'CRV': 180,
    
    # Slow (10-30 min)
    'BTC': 600, 'ETH': 600, 'SHIB': 600, 'PEPE': 600, 'FLOKI': 600,
    'BONK': 300, 'WIF': 300,
    
    # Very slow (30+ min)
    'MANA': 900, 'SAND': 900, 'AXS': 900, 'GALA': 900,
}

async def analyze_spreads():
    """Analyze real spreads and rank cryptos"""
    
    print("Initializing exchanges...")
    coinbase = ccxt.coinbase({
        'apiKey': Config.COINBASE_API_KEY,
        'secret': Config.COINBASE_SECRET_KEY,
    })
    
    gemini = ccxt.gemini({
        'apiKey': Config.GEMINI_API_KEY,
        'secret': Config.GEMINI_SECRET_KEY,
    })
    
    coinbase.load_markets()
    gemini.load_markets()
    
    # Get common USD pairs
    coinbase_usd = [s for s in coinbase.markets.keys() if '/USD' in s and '/USDC' not in s and '/USDT' not in s]
    gemini_usd = [s for s in gemini.markets.keys() if '/USD' in s and '/USDC' not in s and '/USDT' not in s]
    common = sorted(set(coinbase_usd) & set(gemini_usd))
    
    print(f"\n✅ Found {len(common)} common USD pairs\n")
    print("Fetching real-time spreads (this takes ~30 seconds)...\n")
    
    results = []
    
    for symbol in common:
        try:
            # Fetch tickers
            cb_ticker = coinbase.fetch_ticker(symbol)
            gem_ticker = gemini.fetch_ticker(symbol)
            
            if not cb_ticker or not gem_ticker:
                continue
            
            cb_bid = cb_ticker.get('bid')
            cb_ask = cb_ticker.get('ask')
            gem_bid = gem_ticker.get('bid')
            gem_ask = gem_ticker.get('ask')
            
            if not all([cb_bid, cb_ask, gem_bid, gem_ask]):
                continue
            
            # Calculate spreads both directions
            spread_cb_to_gem = ((gem_bid - cb_ask) / cb_ask) * 100
            spread_gem_to_cb = ((cb_bid - gem_ask) / gem_ask) * 100
            best_spread = max(spread_cb_to_gem, spread_gem_to_cb)
            
            # Get transfer time
            base = symbol.split('/')[0]
            transfer_time = TRANSFER_TIMES.get(base, 300)  # Default 5 min
            
            # Get volume (liquidity indicator)
            volume = (cb_ticker.get('quoteVolume', 0) + gem_ticker.get('quoteVolume', 0)) / 2
            
            results.append({
                'symbol': symbol,
                'spread': best_spread,
                'transfer_time': transfer_time,
                'volume': volume,
                'cb_ask': cb_ask,
                'gem_ask': gem_ask,
            })
            
            time.sleep(0.1)  # Rate limit protection
            
        except Exception as e:
            print(f"  ⚠️  {symbol}: {e}")
            continue
    
    # Sort by spread (highest first)
    results.sort(key=lambda x: x['spread'], reverse=True)
    
    print("\n" + "=" * 100)
    print("TOP CRYPTOS BY SPREAD (Real-time data)")
    print("=" * 100)
    print(f"{'Symbol':<12} {'Spread':<10} {'Transfer':<12} {'Volume (24h)':<15} {'Score':<8}")
    print("-" * 100)
    
    for r in results[:30]:  # Top 30
        # Calculate score: spread * (1 / transfer_time_minutes) * log(volume)
        transfer_min = r['transfer_time'] / 60
        import math
        volume_score = math.log10(max(r['volume'], 1))
        score = r['spread'] * (1 / max(transfer_min, 0.1)) * volume_score
        
        print(f"{r['symbol']:<12} {r['spread']:>6.3f}%    {r['transfer_time']:>4}s ({transfer_min:>4.1f}m)  "
              f"${r['volume']:>12,.0f}    {score:>6.3f}")
    
    print("=" * 100)
    
    # Recommend best 10-15 based on: spread + fast transfer + good volume
    print("\n" + "=" * 100)
    print("🎯 RECOMMENDED CRYPTOS (Spread + Speed + Liquidity)")
    print("=" * 100)
    
    # Filter: spread > 0.3%, transfer < 5 min, volume > $100k
    good_ones = [r for r in results if r['spread'] > 0.3 and r['transfer_time'] < 300 and r['volume'] > 100000]
    
    if good_ones:
        print(f"\nFound {len(good_ones)} cryptos with good characteristics:\n")
        for r in good_ones[:15]:
            transfer_min = r['transfer_time'] / 60
            print(f"  ✅ {r['symbol']:<12} Spread: {r['spread']:>5.2f}%  Transfer: {transfer_min:>4.1f}m  Volume: ${r['volume']:>10,.0f}")
    else:
        print("\n⚠️  No cryptos currently meet criteria (spread > 0.3%, transfer < 5min, volume > $100k)")
        print("    Market is very tight right now. Showing best available:\n")
        
        # Show best by spread regardless
        for r in results[:15]:
            transfer_min = r['transfer_time'] / 60
            print(f"  {r['symbol']:<12} Spread: {r['spread']:>5.2f}%  Transfer: {transfer_min:>4.1f}m  Volume: ${r['volume']:>10,.0f}")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    asyncio.run(analyze_spreads())
