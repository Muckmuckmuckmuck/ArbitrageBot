#!/usr/bin/env python3
"""Simple real-time spread checker"""

import ccxt
from coinbase_gemini_config import Config

def check_spreads():
    print("Initializing...")
    cb = ccxt.coinbase({'apiKey': Config.COINBASE_API_KEY, 'secret': Config.COINBASE_SECRET_KEY})
    gem = ccxt.gemini({'apiKey': Config.GEMINI_API_KEY, 'secret': Config.GEMINI_SECRET_KEY})
    
    cb.load_markets()
    gem.load_markets()
    
    # Test cryptos
    test_symbols = [
        'BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'DOGE/USD',
        'AVAX/USD', 'LINK/USD', 'UNI/USD', 'AAVE/USD', 'ATOM/USD',
        'PEPE/USD', 'BONK/USD', 'WIF/USD', 'FLOKI/USD',
        'ARB/USD', 'OP/USD', 'INJ/USD', 'RNDR/USD',
        'SAND/USD', 'MANA/USD', 'IMX/USD',
    ]
    
    print("\n" + "=" * 80)
    print("REAL-TIME SPREADS (Coinbase vs Gemini)")
    print("=" * 80)
    print(f"{'Symbol':<15} {'CB Ask':<12} {'GEM Bid':<12} {'Spread %':<10} {'Direction'}")
    print("-" * 80)
    
    results = []
    
    for symbol in test_symbols:
        try:
            cb_ticker = cb.fetch_ticker(symbol)
            gem_ticker = gem.fetch_ticker(symbol)
            
            cb_ask = cb_ticker['ask']
            cb_bid = cb_ticker['bid']
            gem_ask = gem_ticker['ask']
            gem_bid = gem_ticker['bid']
            
            # Both directions
            spread_cb_to_gem = ((gem_bid - cb_ask) / cb_ask) * 100
            spread_gem_to_cb = ((cb_bid - gem_ask) / gem_ask) * 100
            
            best_spread = max(spread_cb_to_gem, spread_gem_to_cb)
            direction = 'CB→GEM' if spread_cb_to_gem > spread_gem_to_cb else 'GEM→CB'
            
            results.append({
                'symbol': symbol,
                'spread': best_spread,
                'direction': direction,
                'cb_ask': cb_ask,
                'gem_bid': gem_bid if direction == 'CB→GEM' else cb_bid,
            })
            
            status = '✅' if best_spread > 0.5 else '  '
            print(f"{status} {symbol:<15} ${cb_ask:<11.6f} ${gem_bid:<11.6f} {best_spread:>6.3f}%    {direction}")
            
        except Exception as e:
            print(f"   {symbol:<15} Error: {str(e)[:40]}")
    
    print("=" * 80)
    
    # Sort by spread
    results.sort(key=lambda x: x['spread'], reverse=True)
    
    print("\n🏆 TOP 15 BY SPREAD:")
    print("-" * 80)
    for i, r in enumerate(results[:15], 1):
        print(f"{i:2d}. {r['symbol']:<12} {r['spread']:>6.3f}%  {r['direction']}")
    print("=" * 80)

if __name__ == "__main__":
    check_spreads()
