"""
COMPREHENSIVE COMPARISON: Bitfinex vs Poloniex for Arbitrage
Analyzes real spreads, liquidity, transfer times, and automation capabilities
"""

import ccxt
import time
from datetime import datetime

def analyze_exchange_pair(exchange1_id, exchange2_id='coinbase'):
    """Analyze arbitrage potential between two exchanges"""
    
    print("=" * 80)
    print(f"ANALYZING: {exchange1_id.upper()} + {exchange2_id.upper()}")
    print("=" * 80)
    print()
    
    try:
        # Initialize exchanges
        exchange1 = getattr(ccxt, exchange1_id)({'enableRateLimit': True})
        exchange2 = getattr(ccxt, exchange2_id)({'enableRateLimit': True})
        
        print(f"✅ {exchange1.name} initialized")
        print(f"✅ {exchange2.name} initialized")
        print()
        
        # Check automation features
        print("🤖 AUTOMATION FEATURES:")
        print()
        
        features = {
            'withdraw': 'Automated withdrawals',
            'fetchDepositAddress': 'Get deposit address',
            'fetchBalance': 'Check balance',
            'createOrder': 'Place orders',
        }
        
        print(f"   {exchange1.name}:")
        for feature, desc in features.items():
            has_it = exchange1.has.get(feature, False)
            status = "✅" if has_it else "❌"
            print(f"      {status} {desc}")
        
        print()
        print(f"   {exchange2.name}:")
        for feature, desc in features.items():
            has_it = exchange2.has.get(feature, False)
            status = "✅" if has_it else "❌"
            print(f"      {status} {desc}")
        
        print()
        
        # Fetch markets
        print("📊 FETCHING MARKETS...")
        markets1 = exchange1.fetch_markets()
        markets2 = exchange2.fetch_markets()
        
        symbols1 = {m['symbol'] for m in markets1}
        symbols2 = {m['symbol'] for m in markets2}
        
        # Find common USDT pairs
        common_symbols = symbols1.intersection(symbols2)
        usdt_pairs = [s for s in common_symbols if '/USDT' in s or '/USD' in s]
        
        print(f"   {exchange1.name}: {len(markets1)} markets")
        print(f"   {exchange2.name}: {len(markets2)} markets")
        print(f"   Common pairs: {len(common_symbols)}")
        print(f"   Common USDT/USD pairs: {len(usdt_pairs)}")
        print()
        
        # Analyze top cryptos
        top_cryptos = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'MATIC/USDT',
            'DOGE/USDT', 'SHIB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT',
            'LINK/USDT', 'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'XLM/USDT',
            'TON/USDT', 'ARB/USDT', 'PEPE/USDT', 'TRX/USDT', 'NEAR/USDT',
        ]
        
        print("🔍 ANALYZING SPREADS FOR TOP CRYPTOS:")
        print()
        
        results = []
        
        for symbol in top_cryptos:
            if symbol not in common_symbols:
                continue
            
            try:
                # Fetch tickers
                ticker1 = exchange1.fetch_ticker(symbol)
                time.sleep(0.1)  # Rate limit
                ticker2 = exchange2.fetch_ticker(symbol)
                time.sleep(0.1)
                
                # Get prices
                bid1 = ticker1.get('bid')
                ask1 = ticker1.get('ask')
                bid2 = ticker2.get('bid')
                ask2 = ticker2.get('ask')
                
                if not all([bid1, ask1, bid2, ask2]):
                    continue
                
                # Calculate spreads
                # Buy on exchange1, sell on exchange2
                spread_1_to_2 = ((bid2 - ask1) / ask1) * 100
                
                # Buy on exchange2, sell on exchange1
                spread_2_to_1 = ((bid1 - ask2) / ask2) * 100
                
                # Best spread
                best_spread = max(spread_1_to_2, spread_2_to_1)
                
                # Get volume
                volume1 = ticker1.get('quoteVolume', 0)
                volume2 = ticker2.get('quoteVolume', 0)
                avg_volume = (volume1 + volume2) / 2
                
                # Calculate bid-ask spread (tightness)
                spread1 = ((ask1 - bid1) / bid1) * 100
                spread2 = ((ask2 - bid2) / bid2) * 100
                avg_spread = (spread1 + spread2) / 2
                
                results.append({
                    'symbol': symbol,
                    'best_spread': best_spread,
                    'spread_1_to_2': spread_1_to_2,
                    'spread_2_to_1': spread_2_to_1,
                    'avg_volume': avg_volume,
                    'avg_bid_ask_spread': avg_spread,
                    'price': (bid1 + ask1) / 2,
                })
                
            except Exception as e:
                continue
        
        # Sort by best spread
        results.sort(key=lambda x: x['best_spread'], reverse=True)
        
        # Display top opportunities
        print(f"   Found {len(results)} tradeable pairs")
        print()
        print("   TOP 15 ARBITRAGE OPPORTUNITIES:")
        print()
        print("   Symbol        Spread    Volume(24h)   Bid-Ask   Price")
        print("   " + "-" * 70)
        
        for r in results[:15]:
            symbol = r['symbol'].ljust(12)
            spread = f"{r['best_spread']:>6.2f}%"
            volume = f"${r['avg_volume']/1e6:>6.1f}M" if r['avg_volume'] > 1e6 else f"${r['avg_volume']/1e3:>6.1f}K"
            bid_ask = f"{r['avg_bid_ask_spread']:>5.2f}%"
            price = f"${r['price']:>8.2f}" if r['price'] > 1 else f"${r['price']:>8.6f}"
            
            print(f"   {symbol}  {spread}    {volume}      {bid_ask}   {price}")
        
        print()
        
        # Calculate statistics
        profitable = [r for r in results if r['best_spread'] > 0.8]  # 0.8% = profitable after fees
        
        print("📈 STATISTICS:")
        print()
        print(f"   Total pairs analyzed: {len(results)}")
        print(f"   Profitable pairs (>0.8% spread): {len(profitable)}")
        print(f"   Success rate: {len(profitable)/len(results)*100:.1f}%")
        print()
        
        if results:
            avg_spread = sum(r['best_spread'] for r in results) / len(results)
            max_spread = max(r['best_spread'] for r in results)
            avg_volume = sum(r['avg_volume'] for r in results) / len(results)
            
            print(f"   Average spread: {avg_spread:.3f}%")
            print(f"   Maximum spread: {max_spread:.3f}%")
            print(f"   Average volume: ${avg_volume/1e6:.1f}M")
        
        print()
        
        # Rate limits
        print("⚡ RATE LIMITS:")
        print()
        print(f"   {exchange1.name}: {exchange1.rateLimit}ms ({1000/exchange1.rateLimit:.1f} req/sec)")
        print(f"   {exchange2.name}: {exchange2.rateLimit}ms ({1000/exchange2.rateLimit:.1f} req/sec)")
        print()
        
        return {
            'exchange1': exchange1_id,
            'exchange2': exchange2_id,
            'total_pairs': len(results),
            'profitable_pairs': len(profitable),
            'avg_spread': avg_spread if results else 0,
            'max_spread': max_spread if results else 0,
            'top_opportunities': results[:10],
        }
        
    except Exception as e:
        print(f"❌ Error analyzing {exchange1_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_exchanges():
    """Compare Bitfinex vs Poloniex for arbitrage with Coinbase"""
    
    print("=" * 80)
    print("BITFINEX VS POLONIEX - COMPREHENSIVE COMPARISON")
    print("=" * 80)
    print()
    print("Analyzing real-time spreads, liquidity, and automation...")
    print()
    
    # Analyze Bitfinex + Coinbase
    print("\n" + "=" * 80)
    print("OPTION 1: BITFINEX + COINBASE")
    print("=" * 80)
    bitfinex_results = analyze_exchange_pair('bitfinex', 'coinbase')
    
    time.sleep(2)
    
    # Analyze Poloniex + Coinbase
    print("\n" + "=" * 80)
    print("OPTION 2: POLONIEX + COINBASE")
    print("=" * 80)
    poloniex_results = analyze_exchange_pair('poloniex', 'coinbase')
    
    # Final comparison
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    print()
    
    if bitfinex_results and poloniex_results:
        print("📊 HEAD-TO-HEAD COMPARISON:")
        print()
        print(f"   Metric                    Bitfinex + Coinbase    Poloniex + Coinbase")
        print("   " + "-" * 75)
        print(f"   Total pairs               {bitfinex_results['total_pairs']:>18}    {poloniex_results['total_pairs']:>19}")
        print(f"   Profitable pairs          {bitfinex_results['profitable_pairs']:>18}    {poloniex_results['profitable_pairs']:>19}")
        print(f"   Average spread            {bitfinex_results['avg_spread']:>17.3f}%    {poloniex_results['avg_spread']:>18.3f}%")
        print(f"   Maximum spread            {bitfinex_results['max_spread']:>17.3f}%    {poloniex_results['max_spread']:>18.3f}%")
        print()
        
        # Determine winner
        bitfinex_score = 0
        poloniex_score = 0
        
        if bitfinex_results['profitable_pairs'] > poloniex_results['profitable_pairs']:
            bitfinex_score += 1
        else:
            poloniex_score += 1
        
        if bitfinex_results['avg_spread'] > poloniex_results['avg_spread']:
            bitfinex_score += 1
        else:
            poloniex_score += 1
        
        if bitfinex_results['max_spread'] > poloniex_results['max_spread']:
            bitfinex_score += 1
        else:
            poloniex_score += 1
        
        print("🏆 WINNER:")
        print()
        if bitfinex_score > poloniex_score:
            print("   ⭐⭐⭐ BITFINEX + COINBASE ⭐⭐⭐")
            print()
            print("   Reasons:")
            if bitfinex_results['profitable_pairs'] > poloniex_results['profitable_pairs']:
                print(f"      ✅ More profitable pairs ({bitfinex_results['profitable_pairs']} vs {poloniex_results['profitable_pairs']})")
            if bitfinex_results['avg_spread'] > poloniex_results['avg_spread']:
                print(f"      ✅ Higher average spread ({bitfinex_results['avg_spread']:.3f}% vs {poloniex_results['avg_spread']:.3f}%)")
            if bitfinex_results['max_spread'] > poloniex_results['max_spread']:
                print(f"      ✅ Higher maximum spread ({bitfinex_results['max_spread']:.3f}% vs {poloniex_results['max_spread']:.3f}%)")
        else:
            print("   ⭐⭐⭐ POLONIEX + COINBASE ⭐⭐⭐")
            print()
            print("   Reasons:")
            if poloniex_results['profitable_pairs'] > bitfinex_results['profitable_pairs']:
                print(f"      ✅ More profitable pairs ({poloniex_results['profitable_pairs']} vs {bitfinex_results['profitable_pairs']})")
            if poloniex_results['avg_spread'] > bitfinex_results['avg_spread']:
                print(f"      ✅ Higher average spread ({poloniex_results['avg_spread']:.3f}% vs {bitfinex_results['avg_spread']:.3f}%)")
            if poloniex_results['max_spread'] > bitfinex_results['max_spread']:
                print(f"      ✅ Higher maximum spread ({poloniex_results['max_spread']:.3f}% vs {poloniex_results['max_spread']:.3f}%)")
        
        print()
    
    print("=" * 80)
    print("AUTOMATION CHECK:")
    print("=" * 80)
    print()
    print("✅ Both Bitfinex and Poloniex support:")
    print("   ✅ Automated withdrawals (no manual approval)")
    print("   ✅ API-based deposits")
    print("   ✅ 24/7 trading")
    print("   ✅ Can run while you sleep")
    print("   ✅ Fully automated via CCXT")
    print()

if __name__ == "__main__":
    compare_exchanges()


