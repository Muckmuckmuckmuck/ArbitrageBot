#!/usr/bin/env python3
"""
Check what pairs Gemini supports for intra-exchange arbitrage
Specifically looking for cryptos with multiple USD/USDC/USDT pairs
"""

import asyncio
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager

async def check_gemini_pairs():
    """Check Gemini pairs for intra-exchange arbitrage"""
    
    exchange_manager = CoinbaseGeminiExchangeManager()
    await exchange_manager.initialize()
    
    gemini = exchange_manager.get_exchange('gemini')
    
    print("=" * 80)
    print("GEMINI PAIR ANALYSIS FOR INTRA-EXCHANGE ARBITRAGE")
    print("=" * 80)
    print()
    
    # Count pairs by base crypto and quote currency
    crypto_pairs = {}
    
    for symbol, market_info in gemini.markets.items():
        if not market_info.get('active', True):
            continue
        
        # Skip futures/derivatives
        if market_info.get('future', False) or market_info.get('swap', False):
            continue
        if ':' in symbol:
            continue
        
        base = market_info.get('base', '').strip().upper()
        quote = market_info.get('quote', '').strip().upper()
        
        # Only count USD/USDC/USDT pairs
        if base and quote in ['USD', 'USDC', 'USDT']:
            if base not in crypto_pairs:
                crypto_pairs[base] = []
            crypto_pairs[base].append((symbol, quote))
    
    # Find cryptos with 2+ pairs (needed for intra-exchange arbitrage)
    arbitrage_cryptos = {}
    for crypto, pairs in crypto_pairs.items():
        if len(pairs) >= 2:
            arbitrage_cryptos[crypto] = pairs
    
    print(f"📊 Total cryptos with USD/USDC/USDT pairs: {len(crypto_pairs)}")
    print(f"✅ Cryptos with 2+ pairs (intra-exchange arbitrage possible): {len(arbitrage_cryptos)}")
    print()
    
    if arbitrage_cryptos:
        print("🎯 GEMINI INTRA-EXCHANGE ARBITRAGE OPPORTUNITIES:")
        print()
        for crypto, pairs in sorted(arbitrage_cryptos.items()):
            print(f"   {crypto}:")
            for pair, quote in pairs:
                print(f"      - {pair} ({quote})")
            print()
    else:
        print("❌ NO INTRA-EXCHANGE ARBITRAGE OPPORTUNITIES ON GEMINI")
        print()
        print("   Reason: Gemini doesn't have multiple USD/USDC/USDT pairs for the same crypto")
        print("   Intra-exchange arbitrage requires comparing:")
        print("   - BTC/USD vs BTC/USDC vs BTC/USDT")
        print("   - But Gemini likely only has one quote currency per crypto")
        print()
    
    # Compare with Coinbase
    print("=" * 80)
    print("COMPARISON WITH COINBASE:")
    print("=" * 80)
    print()
    
    coinbase = exchange_manager.get_exchange('coinbase')
    coinbase_crypto_pairs = {}
    
    for symbol, market_info in coinbase.markets.items():
        if not market_info.get('active', True):
            continue
        if market_info.get('future', False) or market_info.get('swap', False):
            continue
        if ':' in symbol:
            continue
        
        base = market_info.get('base', '').strip().upper()
        quote = market_info.get('quote', '').strip().upper()
        
        if base and quote in ['USD', 'USDC', 'USDT']:
            if base not in coinbase_crypto_pairs:
                coinbase_crypto_pairs[base] = []
            coinbase_crypto_pairs[base].append((symbol, quote))
    
    coinbase_arbitrage_cryptos = {c: p for c, p in coinbase_crypto_pairs.items() if len(p) >= 2}
    
    print(f"Coinbase: {len(coinbase_arbitrage_cryptos)} cryptos with 2+ USD/USDC/USDT pairs")
    print(f"Gemini:   {len(arbitrage_cryptos)} cryptos with 2+ USD/USDC/USDT pairs")
    print()
    
    if len(arbitrage_cryptos) == 0:
        print("⚠️  CONCLUSION: Gemini is NOT suitable for intra-exchange arbitrage")
        print("   Gemini likely only supports one quote currency per crypto (probably USD)")
        print("   You need multiple quote currencies (USD/USDC/USDT) to compare prices")
        print()
        print("💡 RECOMMENDATION:")
        print("   - Use Coinbase for intra-exchange arbitrage (works great)")
        print("   - Consider Gemini only for cross-exchange arbitrage (if transfers work)")
    else:
        print("✅ CONCLUSION: Gemini CAN work for intra-exchange arbitrage")
        print(f"   Found {len(arbitrage_cryptos)} cryptos with multiple quote currency pairs")
        print()
        print("⚠️  BUT NOTE: Gemini has price controls that may limit opportunities:")
        print("   - Orders >5% away from mid-price are rejected")
        print("   - Large spreads may restrict order execution")
        print("   - This could reduce profitable opportunities")

if __name__ == '__main__':
    asyncio.run(check_gemini_pairs())

