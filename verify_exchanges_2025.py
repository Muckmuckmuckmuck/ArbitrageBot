"""
COMPREHENSIVE EXCHANGE VERIFICATION - October 2025
Verifies Pionex.US and Coinbase Pro current status, API support, and feature availability
"""

import ccxt
import sys
from datetime import datetime

def verify_exchange_support():
    """Verify both exchanges are supported by CCXT and check their current status"""
    
    print("=" * 80)
    print("EXCHANGE VERIFICATION - October 2025")
    print("=" * 80)
    print()
    
    results = {
        'pionex': {'supported': False, 'features': {}, 'issues': []},
        'coinbase': {'supported': False, 'features': {}, 'issues': []}
    }
    
    # Check CCXT version
    print(f"📦 CCXT Version: {ccxt.__version__}")
    print()
    
    # List all supported exchanges
    all_exchanges = ccxt.exchanges
    print(f"📊 Total CCXT Supported Exchanges: {len(all_exchanges)}")
    print()
    
    # Define our cryptos (accessible everywhere)
    our_cryptos = ['TON/USDT', 'SHIB/USDT', 'SOL/USDT', 'AVAX/USDT', 
                   'ARB/USDT', 'PEPE/USDT', 'DOGE/USDT', 'ATOM/USDT', 
                   'XLM/USDT', 'UNI/USDT']
    
    # Define features to check (moved here so it's accessible everywhere)
    features_to_check = {
        'fetchBalance': 'Fetch account balance',
        'fetchTicker': 'Fetch price ticker',
        'fetchOrderBook': 'Fetch order book',
        'createOrder': 'Create orders (buy/sell)',
        'fetchOrder': 'Fetch order status',
        'fetchOpenOrders': 'Fetch open orders',
        'fetchClosedOrders': 'Fetch closed orders',
        'cancelOrder': 'Cancel orders',
        'withdraw': 'Withdraw crypto (CRITICAL FOR TRANSFERS)',
        'fetchDepositAddress': 'Get deposit address',
        'fetchDeposits': 'Fetch deposit history',
        'fetchWithdrawals': 'Fetch withdrawal history',
        'fetchTradingFees': 'Fetch trading fees',
        'fetchMarkets': 'Fetch available markets',
    }
    
    # ============================================================================
    # VERIFY PIONEX.US
    # ============================================================================
    
    print("=" * 80)
    print("1. PIONEX.US VERIFICATION")
    print("=" * 80)
    print()
    
    # Check if pionex is in CCXT
    if 'pionex' in all_exchanges:
        print("✅ Pionex is supported by CCXT")
        results['pionex']['supported'] = True
        
        try:
            # Initialize exchange (without API keys)
            exchange = ccxt.pionex({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                }
            })
            
            print(f"✅ Exchange initialized successfully")
            print(f"   Name: {exchange.name}")
            print(f"   ID: {exchange.id}")
            print()
            
            # Check critical features
            print("🔍 CHECKING CRITICAL FEATURES:")
            print()
            
            for feature, description in features_to_check.items():
                has_feature = exchange.has.get(feature, False)
                results['pionex']['features'][feature] = has_feature
                
                if has_feature:
                    print(f"   ✅ {description}: SUPPORTED")
                else:
                    print(f"   ❌ {description}: NOT SUPPORTED")
                    if feature in ['withdraw', 'fetchDepositAddress']:
                        results['pionex']['issues'].append(f"Missing critical feature: {feature}")
            
            print()
            
            # Try to fetch markets (public endpoint, no API key needed)
            print("🔍 TESTING PUBLIC API (No API key needed):")
            print()
            
            try:
                markets = exchange.fetch_markets()
                print(f"   ✅ Successfully fetched {len(markets)} markets")
                
                # Check for our cryptos
                available_symbols = [m['symbol'] for m in markets]
                
                print()
                print("   📊 CHECKING OUR 10 CRYPTOS:")
                print()
                
                available_count = 0
                for symbol in our_cryptos:
                    if symbol in available_symbols:
                        print(f"      ✅ {symbol}: AVAILABLE")
                        available_count += 1
                    else:
                        print(f"      ❌ {symbol}: NOT AVAILABLE")
                        results['pionex']['issues'].append(f"Market not available: {symbol}")
                
                print()
                print(f"   📊 Available: {available_count}/10 cryptos")
                
                if available_count < 10:
                    results['pionex']['issues'].append(f"Only {available_count}/10 cryptos available")
                
            except Exception as e:
                print(f"   ❌ Failed to fetch markets: {e}")
                results['pionex']['issues'].append(f"Cannot fetch markets: {e}")
            
            print()
            
            # Check rate limits
            print("🔍 RATE LIMITS:")
            print()
            if hasattr(exchange, 'rateLimit'):
                print(f"   Rate Limit: {exchange.rateLimit}ms between requests")
                print(f"   Requests per second: ~{1000 / exchange.rateLimit:.1f}")
                print(f"   Requests per minute: ~{60000 / exchange.rateLimit:.0f}")
            else:
                print("   ⚠️  Rate limit info not available")
            
            print()
            
        except Exception as e:
            print(f"❌ Failed to initialize Pionex: {e}")
            results['pionex']['issues'].append(f"Initialization failed: {e}")
    else:
        print("❌ Pionex is NOT supported by CCXT")
        results['pionex']['issues'].append("Not supported by CCXT")
    
    print()
    
    # ============================================================================
    # VERIFY COINBASE PRO
    # ============================================================================
    
    print("=" * 80)
    print("2. COINBASE PRO (ADVANCED TRADE API) VERIFICATION")
    print("=" * 80)
    print()
    
    # Check if coinbasepro is in CCXT
    coinbase_ids = ['coinbasepro', 'coinbase', 'coinbaseadvanced']
    coinbase_id = None
    
    for cid in coinbase_ids:
        if cid in all_exchanges:
            coinbase_id = cid
            break
    
    if coinbase_id:
        print(f"✅ Coinbase is supported by CCXT (ID: {coinbase_id})")
        results['coinbase']['supported'] = True
        
        try:
            # Initialize exchange (without API keys)
            if coinbase_id == 'coinbasepro':
                exchange = ccxt.coinbasepro({
                    'enableRateLimit': True,
                })
            elif coinbase_id == 'coinbase':
                exchange = ccxt.coinbase({
                    'enableRateLimit': True,
                })
            else:
                exchange = getattr(ccxt, coinbase_id)({
                    'enableRateLimit': True,
                })
            
            print(f"✅ Exchange initialized successfully")
            print(f"   Name: {exchange.name}")
            print(f"   ID: {exchange.id}")
            print()
            
            # Check critical features
            print("🔍 CHECKING CRITICAL FEATURES:")
            print()
            
            for feature, description in features_to_check.items():
                has_feature = exchange.has.get(feature, False)
                results['coinbase']['features'][feature] = has_feature
                
                if has_feature:
                    print(f"   ✅ {description}: SUPPORTED")
                else:
                    print(f"   ❌ {description}: NOT SUPPORTED")
                    if feature in ['withdraw', 'fetchDepositAddress']:
                        results['coinbase']['issues'].append(f"Missing critical feature: {feature}")
            
            print()
            
            # Try to fetch markets (public endpoint, no API key needed)
            print("🔍 TESTING PUBLIC API (No API key needed):")
            print()
            
            try:
                markets = exchange.fetch_markets()
                print(f"   ✅ Successfully fetched {len(markets)} markets")
                
                # Check for our cryptos
                available_symbols = [m['symbol'] for m in markets]
                
                print()
                print("   📊 CHECKING OUR 10 CRYPTOS:")
                print()
                
                available_count = 0
                for symbol in our_cryptos:
                    if symbol in available_symbols:
                        print(f"      ✅ {symbol}: AVAILABLE")
                        available_count += 1
                    else:
                        print(f"      ❌ {symbol}: NOT AVAILABLE")
                        results['coinbase']['issues'].append(f"Market not available: {symbol}")
                
                print()
                print(f"   📊 Available: {available_count}/10 cryptos")
                
                if available_count < 10:
                    results['coinbase']['issues'].append(f"Only {available_count}/10 cryptos available")
                
            except Exception as e:
                print(f"   ❌ Failed to fetch markets: {e}")
                results['coinbase']['issues'].append(f"Cannot fetch markets: {e}")
            
            print()
            
            # Check rate limits
            print("🔍 RATE LIMITS:")
            print()
            if hasattr(exchange, 'rateLimit'):
                print(f"   Rate Limit: {exchange.rateLimit}ms between requests")
                print(f"   Requests per second: ~{1000 / exchange.rateLimit:.1f}")
                print(f"   Requests per minute: ~{60000 / exchange.rateLimit:.0f}")
            else:
                print("   ⚠️  Rate limit info not available")
            
            print()
            
        except Exception as e:
            print(f"❌ Failed to initialize Coinbase: {e}")
            results['coinbase']['issues'].append(f"Initialization failed: {e}")
    else:
        print("❌ Coinbase is NOT supported by CCXT")
        results['coinbase']['issues'].append("Not supported by CCXT")
    
    print()
    
    # ============================================================================
    # FINAL VERDICT
    # ============================================================================
    
    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    print()
    
    # Pionex verdict
    print("1. PIONEX.US:")
    if results['pionex']['supported'] and len(results['pionex']['issues']) == 0:
        print("   ✅ FULLY SUPPORTED - Ready to use!")
    elif results['pionex']['supported'] and len(results['pionex']['issues']) > 0:
        print("   ⚠️  PARTIALLY SUPPORTED - Has issues:")
        for issue in results['pionex']['issues']:
            print(f"      - {issue}")
    else:
        print("   ❌ NOT SUPPORTED - Cannot use")
    
    print()
    
    # Coinbase verdict
    print("2. COINBASE PRO:")
    if results['coinbase']['supported'] and len(results['coinbase']['issues']) == 0:
        print("   ✅ FULLY SUPPORTED - Ready to use!")
    elif results['coinbase']['supported'] and len(results['coinbase']['issues']) > 0:
        print("   ⚠️  PARTIALLY SUPPORTED - Has issues:")
        for issue in results['coinbase']['issues']:
            print(f"      - {issue}")
    else:
        print("   ❌ NOT SUPPORTED - Cannot use")
    
    print()
    
    # Overall verdict
    print("=" * 80)
    print("OVERALL VERDICT:")
    print("=" * 80)
    print()
    
    pionex_ok = results['pionex']['supported'] and len(results['pionex']['issues']) == 0
    coinbase_ok = results['coinbase']['supported'] and len(results['coinbase']['issues']) == 0
    
    if pionex_ok and coinbase_ok:
        print("✅✅✅ BOTH EXCHANGES FULLY SUPPORTED! ✅✅✅")
        print()
        print("Your arbitrage bot will work perfectly with these exchanges!")
        print()
        return True
    else:
        print("⚠️⚠️⚠️ ISSUES DETECTED ⚠️⚠️⚠️")
        print()
        if not pionex_ok:
            print("❌ Pionex.US has issues - see details above")
        if not coinbase_ok:
            print("❌ Coinbase Pro has issues - see details above")
        print()
        print("⚠️  YOUR BOT MAY NOT WORK AS EXPECTED!")
        print()
        return False

if __name__ == "__main__":
    try:
        success = verify_exchange_support()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

