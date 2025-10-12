"""
Find US-compatible exchanges that support automated withdrawals
"""

import ccxt

def find_us_exchanges():
    """Find exchanges that work in the US with automated withdrawals"""
    
    print("=" * 80)
    print("FINDING US-COMPATIBLE EXCHANGES WITH AUTOMATED WITHDRAWALS")
    print("=" * 80)
    print()
    
    # Known US-compatible exchanges
    us_compatible = [
        'coinbase',  # Coinbase Advanced (works in US)
        'kraken',    # Kraken (works in US)
        'gemini',    # Gemini (works in US)
        'bitstamp',  # Bitstamp (works in US)
        'bitfinex',  # Bitfinex (limited US)
        'poloniex',  # Poloniex (works in US)
        'bittrex',   # Bittrex (works in US)
        'cex',       # CEX.IO (works in US)
    ]
    
    our_cryptos = ['TON/USDT', 'SHIB/USDT', 'SOL/USDT', 'AVAX/USDT', 
                   'ARB/USDT', 'PEPE/USDT', 'DOGE/USDT', 'ATOM/USDT', 
                   'XLM/USDT', 'UNI/USDT']
    
    results = []
    
    for exchange_id in us_compatible:
        if exchange_id not in ccxt.exchanges:
            continue
            
        try:
            exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True})
            
            # Check if it has withdraw feature
            has_withdraw = exchange.has.get('withdraw', False)
            has_deposit_address = exchange.has.get('fetchDepositAddress', False)
            
            if not (has_withdraw and has_deposit_address):
                continue
            
            # Fetch markets
            markets = exchange.fetch_markets()
            available_symbols = [m['symbol'] for m in markets]
            
            # Count how many of our cryptos are available
            available_count = sum(1 for crypto in our_cryptos if crypto in available_symbols)
            
            if available_count > 0:
                results.append({
                    'id': exchange_id,
                    'name': exchange.name,
                    'available_cryptos': available_count,
                    'total_markets': len(markets),
                    'has_withdraw': has_withdraw,
                    'has_deposit_address': has_deposit_address,
                })
                
                print(f"✅ {exchange.name} ({exchange_id})")
                print(f"   Available cryptos: {available_count}/10")
                print(f"   Total markets: {len(markets)}")
                print(f"   Withdraw: {'✅' if has_withdraw else '❌'}")
                print(f"   Deposit address: {'✅' if has_deposit_address else '❌'}")
                print()
                
        except Exception as e:
            print(f"❌ {exchange_id}: {e}")
            print()
    
    # Sort by available cryptos
    results.sort(key=lambda x: x['available_cryptos'], reverse=True)
    
    print("=" * 80)
    print("BEST US-COMPATIBLE EXCHANGES:")
    print("=" * 80)
    print()
    
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result['name']} ({result['id']})")
        print(f"   Cryptos: {result['available_cryptos']}/10")
        print()
    
    return results

if __name__ == "__main__":
    find_us_exchanges()


