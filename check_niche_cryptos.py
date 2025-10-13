#!/usr/bin/env python3
"""
Check for niche/volatile cryptos on Coinbase + Gemini
Focus on: meme coins, DeFi tokens, newer listings
"""

import ccxt
import asyncio
from coinbase_gemini_config import Config

async def check_niche_cryptos():
    """Find niche cryptos with potential for higher spreads"""
    
    # Initialize exchanges
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
    
    # Get all USD pairs
    coinbase_usd = [s for s in coinbase.markets.keys() if '/USD' in s]
    gemini_usd = [s for s in gemini.markets.keys() if '/USD' in s]
    
    # Find common pairs
    common = set(coinbase_usd) & set(gemini_usd)
    
    # Categories of interest
    meme_coins = ['SHIB', 'DOGE', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'MEME']
    defi_tokens = ['AAVE', 'COMP', 'UNI', 'SUSHI', 'CRV', 'MKR', 'SNX', 'YFI']
    layer1 = ['SOL', 'AVAX', 'NEAR', 'FTM', 'ALGO', 'ATOM', 'DOT', 'ADA']
    layer2 = ['MATIC', 'ARB', 'OP']
    gaming = ['AXS', 'SAND', 'MANA', 'GALA', 'IMX']
    newer = ['SUI', 'APT', 'SEI', 'TIA', 'INJ']
    
    categories = {
        'Meme Coins': meme_coins,
        'DeFi Tokens': defi_tokens,
        'Layer 1': layer1,
        'Layer 2': layer2,
        'Gaming/Metaverse': gaming,
        'Newer High-Vol': newer,
    }
    
    print("=" * 80)
    print("NICHE CRYPTOS AVAILABLE ON BOTH COINBASE + GEMINI")
    print("=" * 80)
    print()
    
    for category, tokens in categories.items():
        found = []
        for token in tokens:
            symbol = f"{token}/USD"
            if symbol in common:
                found.append(symbol)
        
        if found:
            print(f"{category}:")
            for s in found:
                print(f"  ✅ {s}")
            print()
    
    # Show what we're currently NOT using
    current = set(Config.CURRENCY_PAIRS)
    available_not_used = common - current
    
    print("=" * 80)
    print(f"AVAILABLE BUT NOT USED ({len(available_not_used)} cryptos):")
    print("=" * 80)
    for symbol in sorted(available_not_used):
        print(f"  {symbol}")
    print()
    
    print("=" * 80)
    print(f"TOTAL COMMON PAIRS: {len(common)}")
    print(f"CURRENTLY USING: {len(current)}")
    print(f"AVAILABLE TO ADD: {len(available_not_used)}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(check_niche_cryptos())
