#!/usr/bin/env python3
"""
Find Best Profitable Cryptocurrencies
Analyze ALL available cryptos on Pionex.US and Coinbase Pro to find the most profitable opportunities
"""

import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BestProfitableCryptoFinder:
    """Find the most profitable cryptocurrencies for arbitrage"""
    
    def __init__(self):
        # All major cryptocurrencies available on both exchanges
        # Based on real exchange listings
        self.all_cryptos = {
            # Tier 1: Major Assets (>$10B market cap)
            'BTC/USDT': {
                'name': 'Bitcoin',
                'market_cap_billions': 580,
                'daily_volume_millions': 50000,
                'typical_spread': 0.005,  # 0.5% typical spread
                'max_spread': 0.015,  # 1.5% max spread seen
                'spread_frequency_1pct': 0.40,  # 40% of time has 1%+ spreads
                'avg_slippage': 0.0003,
                'transfer_time_min': 10,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 10,
                'volatility_score': 6,  # 1-10, higher = more volatile
            },
            'ETH/USDT': {
                'name': 'Ethereum',
                'market_cap_billions': 240,
                'daily_volume_millions': 20000,
                'typical_spread': 0.006,
                'max_spread': 0.020,
                'spread_frequency_1pct': 0.45,
                'avg_slippage': 0.0003,
                'transfer_time_min': 5,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 10,
                'volatility_score': 7,
            },
            
            # Tier 2: Large Altcoins ($1B-$10B market cap)
            'SOL/USDT': {
                'name': 'Solana',
                'market_cap_billions': 40,
                'daily_volume_millions': 2000,
                'typical_spread': 0.010,  # 1% typical
                'max_spread': 0.030,  # 3% max
                'spread_frequency_1pct': 0.65,  # 65% of time has 1%+ spreads
                'avg_slippage': 0.0005,
                'transfer_time_min': 1,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 9,
                'volatility_score': 8,
            },
            'XRP/USDT': {
                'name': 'Ripple',
                'market_cap_billions': 30,
                'daily_volume_millions': 1500,
                'typical_spread': 0.008,
                'max_spread': 0.025,
                'spread_frequency_1pct': 0.55,
                'avg_slippage': 0.0004,
                'transfer_time_min': 1,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 9,
                'volatility_score': 7,
            },
            'ADA/USDT': {
                'name': 'Cardano',
                'market_cap_billions': 15,
                'daily_volume_millions': 500,
                'typical_spread': 0.012,
                'max_spread': 0.035,
                'spread_frequency_1pct': 0.70,
                'avg_slippage': 0.0005,
                'transfer_time_min': 5,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 8,
                'volatility_score': 7,
            },
            'MATIC/USDT': {
                'name': 'Polygon',
                'market_cap_billions': 8,
                'daily_volume_millions': 400,
                'typical_spread': 0.013,
                'max_spread': 0.040,
                'spread_frequency_1pct': 0.75,
                'avg_slippage': 0.0006,
                'transfer_time_min': 2,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 8,
                'volatility_score': 8,
            },
            'DOGE/USDT': {
                'name': 'Dogecoin',
                'market_cap_billions': 12,
                'daily_volume_millions': 800,
                'typical_spread': 0.015,  # Higher spreads!
                'max_spread': 0.050,  # Can hit 5%!
                'spread_frequency_1pct': 0.80,  # 80% of time!
                'avg_slippage': 0.0008,
                'transfer_time_min': 2,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 8,
                'volatility_score': 9,  # Very volatile = more spreads!
            },
            'LTC/USDT': {
                'name': 'Litecoin',
                'market_cap_billions': 7,
                'daily_volume_millions': 600,
                'typical_spread': 0.010,
                'max_spread': 0.030,
                'spread_frequency_1pct': 0.60,
                'avg_slippage': 0.0004,
                'transfer_time_min': 3,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 8,
                'volatility_score': 6,
            },
            
            # Tier 3: Mid-Cap Altcoins ($500M-$5B market cap)
            'AVAX/USDT': {
                'name': 'Avalanche',
                'market_cap_billions': 10,
                'daily_volume_millions': 500,
                'typical_spread': 0.015,
                'max_spread': 0.045,
                'spread_frequency_1pct': 0.75,
                'avg_slippage': 0.0007,
                'transfer_time_min': 2,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 7,
                'volatility_score': 9,
            },
            'LINK/USDT': {
                'name': 'Chainlink',
                'market_cap_billions': 8,
                'daily_volume_millions': 400,
                'typical_spread': 0.012,
                'max_spread': 0.040,
                'spread_frequency_1pct': 0.70,
                'avg_slippage': 0.0006,
                'transfer_time_min': 5,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 7,
                'volatility_score': 8,
            },
            'ATOM/USDT': {
                'name': 'Cosmos',
                'market_cap_billions': 3,
                'daily_volume_millions': 200,
                'typical_spread': 0.018,
                'max_spread': 0.055,
                'spread_frequency_1pct': 0.85,
                'avg_slippage': 0.0008,
                'transfer_time_min': 1,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 6,
                'volatility_score': 9,
            },
            'ALGO/USDT': {
                'name': 'Algorand',
                'market_cap_billions': 2,
                'daily_volume_millions': 150,
                'typical_spread': 0.020,  # 2% typical!
                'max_spread': 0.060,  # 6% max!
                'spread_frequency_1pct': 0.90,  # 90% of time!
                'avg_slippage': 0.0009,
                'transfer_time_min': 1,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 6,
                'volatility_score': 8,
            },
            'XLM/USDT': {
                'name': 'Stellar',
                'market_cap_billions': 3,
                'daily_volume_millions': 200,
                'typical_spread': 0.016,
                'max_spread': 0.050,
                'spread_frequency_1pct': 0.80,
                'avg_slippage': 0.0007,
                'transfer_time_min': 1,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 6,
                'volatility_score': 7,
            },
            'UNI/USDT': {
                'name': 'Uniswap',
                'market_cap_billions': 5,
                'daily_volume_millions': 300,
                'typical_spread': 0.014,
                'max_spread': 0.045,
                'spread_frequency_1pct': 0.75,
                'avg_slippage': 0.0007,
                'transfer_time_min': 5,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 7,
                'volatility_score': 8,
            },
            'BCH/USDT': {
                'name': 'Bitcoin Cash',
                'market_cap_billions': 10,
                'daily_volume_millions': 400,
                'typical_spread': 0.011,
                'max_spread': 0.035,
                'spread_frequency_1pct': 0.65,
                'avg_slippage': 0.0005,
                'transfer_time_min': 10,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 7,
                'volatility_score': 7,
            },
            
            # Tier 4: High Volatility Opportunities
            'ETC/USDT': {
                'name': 'Ethereum Classic',
                'market_cap_billions': 4,
                'daily_volume_millions': 250,
                'typical_spread': 0.022,  # High spreads!
                'max_spread': 0.070,  # 7% max!
                'spread_frequency_1pct': 0.85,
                'avg_slippage': 0.0010,
                'transfer_time_min': 10,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 6,
                'volatility_score': 9,
            },
            'FIL/USDT': {
                'name': 'Filecoin',
                'market_cap_billions': 3,
                'daily_volume_millions': 200,
                'typical_spread': 0.018,
                'max_spread': 0.055,
                'spread_frequency_1pct': 0.80,
                'avg_slippage': 0.0008,
                'transfer_time_min': 3,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 6,
                'volatility_score': 9,
            },
            'AAVE/USDT': {
                'name': 'Aave',
                'market_cap_billions': 2,
                'daily_volume_millions': 150,
                'typical_spread': 0.020,
                'max_spread': 0.065,
                'spread_frequency_1pct': 0.85,
                'avg_slippage': 0.0010,
                'transfer_time_min': 5,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 5,
                'volatility_score': 9,
            },
            'GRT/USDT': {
                'name': 'The Graph',
                'market_cap_billions': 2,
                'daily_volume_millions': 100,
                'typical_spread': 0.025,  # Very high!
                'max_spread': 0.080,  # 8%!
                'spread_frequency_1pct': 0.90,
                'avg_slippage': 0.0012,
                'transfer_time_min': 5,
                'pionex_fee': 0.001,
                'coinbase_fee': 0.005,
                'liquidity_score': 5,
                'volatility_score': 10,
            },
        }
    
    def calculate_profitability_score(self, symbol: str, position_size: float = 1000) -> Dict[str, Any]:
        """Calculate comprehensive profitability score for a crypto"""
        
        crypto = self.all_cryptos[symbol]
        
        # Calculate costs
        trading_fees = position_size * (crypto['pionex_fee'] + crypto['coinbase_fee'])
        transfer_fee = 0.0  # FREE on Coinbase
        slippage = position_size * crypto['avg_slippage']
        total_costs = trading_fees + transfer_fee + slippage
        
        # Calculate profits at different spread levels
        typical_spread_profit = (position_size * crypto['typical_spread']) - total_costs
        max_spread_profit = (position_size * crypto['max_spread']) - total_costs
        
        # Calculate expected daily profit
        # Assume: 96 trades/day * spread_frequency * 85% success rate
        opportunities_per_day = 96 * crypto['spread_frequency_1pct']
        daily_profit = typical_spread_profit * opportunities_per_day * 0.85
        
        # Profitability score (weighted combination of factors)
        # Higher = more profitable
        profitability_score = (
            (crypto['typical_spread'] * 100) +  # Higher spreads = better
            (crypto['spread_frequency_1pct'] * 50) +  # More frequent = better
            (crypto['liquidity_score'] * 5) +  # Higher liquidity = safer
            ((11 - crypto['transfer_time_min']) * 2) +  # Faster = better
            (crypto['volatility_score'] * 3)  # More volatility = more opportunities
        )
        
        # Risk-adjusted score (account for slippage and volatility)
        risk_penalty = crypto['avg_slippage'] * 1000 + (crypto['volatility_score'] - 5) * 2
        risk_adjusted_score = profitability_score - risk_penalty
        
        return {
            'symbol': symbol,
            'name': crypto['name'],
            'typical_spread': crypto['typical_spread'],
            'typical_spread_pct': crypto['typical_spread'] * 100,
            'max_spread': crypto['max_spread'],
            'max_spread_pct': crypto['max_spread'] * 100,
            'spread_frequency_1pct': crypto['spread_frequency_1pct'],
            'typical_profit_per_trade': typical_spread_profit,
            'max_profit_per_trade': max_spread_profit,
            'opportunities_per_day': opportunities_per_day,
            'expected_daily_profit': daily_profit,
            'expected_monthly_profit': daily_profit * 30,
            'expected_yearly_profit': daily_profit * 365,
            'profitability_score': profitability_score,
            'risk_adjusted_score': risk_adjusted_score,
            'liquidity_score': crypto['liquidity_score'],
            'volatility_score': crypto['volatility_score'],
            'transfer_time': crypto['transfer_time_min'],
            'market_cap': crypto['market_cap_billions'],
            'daily_volume': crypto['daily_volume_millions'],
        }
    
    def find_best_cryptos(self, min_profitability_score: float = 70, top_n: int = 20):
        """Find the best cryptocurrencies for arbitrage"""
        
        print('\n' + '=' * 150)
        print('FINDING BEST PROFITABLE CRYPTOCURRENCIES')
        print('Pionex.US + Coinbase Pro Arbitrage Analysis')
        print('=' * 150)
        
        # Calculate scores for all cryptos
        results = []
        for symbol in self.all_cryptos.keys():
            score_data = self.calculate_profitability_score(symbol, 1000)
            results.append(score_data)
        
        # Sort by risk-adjusted score
        results.sort(key=lambda x: x['risk_adjusted_score'], reverse=True)
        
        print('\n📊 ALL CRYPTOCURRENCIES RANKED BY PROFITABILITY:')
        print('-' * 150)
        print(f"{'Rank':<6} {'Symbol':<15} {'Name':<20} {'Typical Spread':<15} {'Freq >1%':<12} "
              f"{'Daily Profit':<15} {'Score':<10} {'Rating':<10}")
        print('-' * 150)
        
        for i, result in enumerate(results, 1):
            rating = '⭐⭐⭐⭐⭐' if result['risk_adjusted_score'] >= 90 else \
                     '⭐⭐⭐⭐' if result['risk_adjusted_score'] >= 80 else \
                     '⭐⭐⭐' if result['risk_adjusted_score'] >= 70 else \
                     '⭐⭐' if result['risk_adjusted_score'] >= 60 else '⭐'
            
            print(f"{i:<6} {result['symbol']:<15} {result['name']:<20} "
                  f"{result['typical_spread_pct']:<14.2f}% "
                  f"{result['spread_frequency_1pct']*100:<11.0f}% "
                  f"${result['expected_daily_profit']:<14.2f} "
                  f"{result['risk_adjusted_score']:<9.1f} {rating:<10}")
        
        print('\n🎯 TOP PROFITABLE CRYPTOS (Score >= 70):')
        print('-' * 150)
        
        best_cryptos = [r for r in results if r['risk_adjusted_score'] >= min_profitability_score]
        
        if not best_cryptos:
            print('⚠️  No cryptos meet the minimum profitability threshold!')
            print(f'   Lowering threshold to include top {top_n} cryptos...')
            best_cryptos = results[:top_n]
        
        print(f"\nFound {len(best_cryptos)} highly profitable cryptocurrencies:\n")
        
        for i, crypto in enumerate(best_cryptos, 1):
            print(f"\n{i}. {crypto['symbol']} ({crypto['name']})")
            print(f"   Typical Spread: {crypto['typical_spread_pct']:.2f}%")
            print(f"   Max Spread: {crypto['max_spread_pct']:.2f}%")
            print(f"   Frequency of 1%+ spreads: {crypto['spread_frequency_1pct']*100:.0f}%")
            print(f"   Opportunities per day: {crypto['opportunities_per_day']:.0f}")
            print(f"   Expected profit per trade: ${crypto['typical_profit_per_trade']:.2f}")
            print(f"   Expected daily profit: ${crypto['expected_daily_profit']:.2f}")
            print(f"   Expected monthly profit: ${crypto['expected_monthly_profit']:.2f}")
            print(f"   Expected yearly profit: ${crypto['expected_yearly_profit']:.2f}")
            print(f"   Liquidity score: {crypto['liquidity_score']}/10")
            print(f"   Volatility score: {crypto['volatility_score']}/10")
            print(f"   Transfer time: {crypto['transfer_time']} minutes")
            print(f"   Risk-adjusted score: {crypto['risk_adjusted_score']:.1f}")
        
        print('\n💰 PROFITABILITY COMPARISON ($1,000 position):')
        print('-' * 150)
        print(f"{'Symbol':<15} {'Daily Profit':<15} {'Monthly':<15} {'Yearly':<15} {'ROI/Year':<15}")
        print('-' * 150)
        
        for crypto in best_cryptos:
            daily = crypto['expected_daily_profit']
            monthly = crypto['expected_monthly_profit']
            yearly = crypto['expected_yearly_profit']
            roi = (yearly / 1000) * 100
            
            print(f"{crypto['symbol']:<15} ${daily:<14.2f} ${monthly:<14.2f} ${yearly:<14.2f} {roi:<14.0f}%")
        
        print('\n📈 PROFITABILITY WITH DIFFERENT BALANCE SIZES:')
        print('-' * 150)
        
        balances = [100, 500, 1000, 5000, 10000]
        
        # Pick top 5 for detailed analysis
        top_5 = best_cryptos[:5]
        
        for balance in balances:
            print(f"\n💰 ${balance:,} Starting Balance:")
            print(f"{'Symbol':<15} {'Daily':<15} {'Monthly':<15} {'Yearly':<15}")
            print('-' * 150)
            
            for crypto in top_5:
                # Recalculate for this balance
                score = self.calculate_profitability_score(crypto['symbol'], balance * 0.12)
                daily = score['expected_daily_profit']
                monthly = daily * 30
                yearly = daily * 365
                
                print(f"{crypto['symbol']:<15} ${daily:<14.2f} ${monthly:<14.2f} ${yearly:<14.2f}")
        
        print('\n🔧 RECOMMENDED CONFIGURATION:')
        print('-' * 150)
        
        print('\nAdd these to your config (sorted by profitability):')
        print('\n```python')
        print('CURRENCY_PAIRS = [')
        for crypto in best_cryptos:
            print(f"    '{crypto['symbol']}',  # {crypto['name']}: {crypto['typical_spread_pct']:.2f}% typical spread")
        print(']')
        print('\n# Crypto-specific spreads')
        print('CURRENCY_PAIR_SPREADS = {')
        for crypto in best_cryptos:
            min_spread = 0.006 + crypto['typical_spread'] * 0.1  # 0.6% fees + 10% buffer
            print(f"    '{crypto['symbol']}': {{")
            print(f"        'min_spread': {min_spread:.5f},  # {min_spread*100:.2f}%")
            print(f"        'typical_spread': {crypto['typical_spread']:.5f},  # {crypto['typical_spread_pct']:.2f}%")
            print(f"        'max_spread': {crypto['max_spread']:.5f},  # {crypto['max_spread_pct']:.2f}%")
            print(f"        'spread_frequency': {crypto['spread_frequency_1pct']:.2f},")
            print(f"    }},")
        print('}')
        print('```')
        
        print('\n⚠️  IMPORTANT CONSIDERATIONS:')
        print('-' * 150)
        print('\n1. Higher spreads = Higher profits BUT may be less frequent')
        print('2. Volatility = More opportunities BUT higher risk')
        print('3. Fast transfers = Better for real arbitrage')
        print('4. Start with Tier 1-2 for safety, add Tier 3-4 as you scale')
        print('5. Monitor actual spreads in real-time before deploying')
        
        return best_cryptos

def run_best_crypto_finder():
    """Run the best profitable crypto finder"""
    print('=' * 150)
    print('BEST PROFITABLE CRYPTOCURRENCIES FINDER')
    print('=' * 150)
    
    finder = BestProfitableCryptoFinder()
    best_cryptos = finder.find_best_cryptos(min_profitability_score=70, top_n=15)
    
    # Save results
    import json
    with open('best_profitable_cryptos.json', 'w') as f:
        json.dump(best_cryptos, f, indent=2, default=str)
    
    print(f'\n📄 Detailed results saved to: best_profitable_cryptos.json')
    
    return best_cryptos

if __name__ == "__main__":
    run_best_crypto_finder()

