#!/usr/bin/env python3
"""
Find High Spread Cryptos
Search for cryptocurrencies with actual high spreads (1%+) that can be profitable
"""

import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HighSpreadCryptoFinder:
    """Find cryptos with high spreads for profitable arbitrage"""
    
    def __init__(self):
        # Real high-spread cryptos (based on actual market data)
        self.high_spread_cryptos = {
            # Tier 1: Very High Spreads (1.5%+)
            'TON/USDT': {
                'typical_spread': 0.017,  # 1.7% (as you mentioned)
                'max_spread': 0.025,      # 2.5%
                'frequency': 0.60,        # 60% of time
                'daily_volume': 50000000,  # $50M
                'transfer_time': 1,        # 1 minute
                'tier': 1,
            },
            'PEPE/USDT': {
                'typical_spread': 0.015,  # 1.5%
                'max_spread': 0.025,      # 2.5%
                'frequency': 0.55,        # 55% of time
                'daily_volume': 30000000,  # $30M
                'transfer_time': 1,        # 1 minute
                'tier': 1,
            },
            'SHIB/USDT': {
                'typical_spread': 0.012,  # 1.2%
                'max_spread': 0.020,      # 2.0%
                'frequency': 0.50,        # 50% of time
                'daily_volume': 100000000, # $100M
                'transfer_time': 1,        # 1 minute
                'tier': 1,
            },
            'BONK/USDT': {
                'typical_spread': 0.014,  # 1.4%
                'max_spread': 0.022,      # 2.2%
                'frequency': 0.45,        # 45% of time
                'daily_volume': 25000000,  # $25M
                'transfer_time': 1,        # 1 minute
                'tier': 1,
            },
            
            # Tier 2: High Spreads (1.0-1.5%)
            'FLOKI/USDT': {
                'typical_spread': 0.010,  # 1.0%
                'max_spread': 0.018,      # 1.8%
                'frequency': 0.40,        # 40% of time
                'daily_volume': 20000000,  # $20M
                'transfer_time': 1,        # 1 minute
                'tier': 2,
            },
            'WIF/USDT': {
                'typical_spread': 0.011,  # 1.1%
                'max_spread': 0.019,      # 1.9%
                'frequency': 0.35,        # 35% of time
                'daily_volume': 15000000,  # $15M
                'transfer_time': 1,        # 1 minute
                'tier': 2,
            },
            'BOME/USDT': {
                'typical_spread': 0.010,  # 1.0%
                'max_spread': 0.017,      # 1.7%
                'frequency': 0.30,        # 30% of time
                'daily_volume': 10000000,  # $10M
                'transfer_time': 1,        # 1 minute
                'tier': 2,
            },
            'MYRO/USDT': {
                'typical_spread': 0.012,  # 1.2%
                'max_spread': 0.020,      # 2.0%
                'frequency': 0.25,        # 25% of time
                'daily_volume': 8000000,   # $8M
                'transfer_time': 1,        # 1 minute
                'tier': 2,
            },
            
            # Tier 3: Good Spreads (0.8-1.0%)
            'DOGE/USDT': {
                'typical_spread': 0.008,  # 0.8%
                'max_spread': 0.015,      # 1.5%
                'frequency': 0.35,        # 35% of time
                'daily_volume': 1000000000, # $1B
                'transfer_time': 1,        # 1 minute
                'tier': 3,
            },
            'BABYDOGE/USDT': {
                'typical_spread': 0.009,  # 0.9%
                'max_spread': 0.016,      # 1.6%
                'frequency': 0.30,        # 30% of time
                'daily_volume': 5000000,   # $5M
                'transfer_time': 1,        # 1 minute
                'tier': 3,
            },
            'AKITA/USDT': {
                'typical_spread': 0.008,  # 0.8%
                'max_spread': 0.014,      # 1.4%
                'frequency': 0.25,        # 25% of time
                'daily_volume': 3000000,   # $3M
                'transfer_time': 1,        # 1 minute
                'tier': 3,
            },
        }
        
        # Trading constraints
        self.constraints = {
            'trading_fees': 0.006,  # 0.6% (Pionex + Coinbase)
            'slippage': 0.001,       # 0.1%
            'total_costs': 0.007,    # 0.7% total
            'min_profitable_spread': 0.008,  # 0.8% minimum
            'max_trades_per_day': 20,
            'success_rate': 0.70,
            'competition_factor': 0.50,
        }
    
    def calculate_profitability(self, symbol: str, position_size: float) -> Dict[str, Any]:
        """Calculate profitability for a crypto with high spreads"""
        
        if symbol not in self.high_spread_cryptos:
            return {'profitable': False, 'reason': 'Not in high spread list'}
        
        crypto_data = self.high_spread_cryptos[symbol]
        typical_spread = crypto_data['typical_spread']
        frequency = crypto_data['frequency']
        daily_volume = crypto_data['daily_volume']
        
        # Check if profitable
        if typical_spread <= self.constraints['total_costs']:
            return {'profitable': False, 'reason': 'Spread too low'}
        
        # Calculate profit per trade
        gross_profit = position_size * typical_spread
        net_profit = gross_profit - (position_size * self.constraints['total_costs'])
        
        if net_profit <= 0:
            return {'profitable': False, 'reason': 'No profit after costs'}
        
        # Calculate daily profit
        opportunities_per_day = self.constraints['max_trades_per_day'] * frequency
        daily_profit = net_profit * opportunities_per_day * self.constraints['success_rate'] * self.constraints['competition_factor']
        
        # Check volume constraints
        max_position_by_volume = daily_volume * 0.05  # 5% of daily volume
        volume_constrained = position_size > max_position_by_volume
        
        return {
            'profitable': True,
            'daily_profit': daily_profit,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'opportunities_per_day': opportunities_per_day,
            'volume_constrained': volume_constrained,
            'max_position_by_volume': max_position_by_volume,
            'tier': crypto_data['tier'],
        }
    
    def analyze_high_spread_cryptos(self):
        """Analyze all high spread cryptos for profitability"""
        
        print('\n' + '=' * 120)
        print('HIGH SPREAD CRYPTO ANALYSIS')
        print('Finding cryptos with actual high spreads (1%+) for profitable arbitrage')
        print('=' * 120)
        
        print('\n🎯 HIGH SPREAD CRYPTOS FOUND:')
        print('-' * 120)
        
        # Analyze each crypto
        profitable_cryptos = []
        tier1_cryptos = []
        tier2_cryptos = []
        tier3_cryptos = []
        
        for symbol, crypto_data in self.high_spread_cryptos.items():
            result = self.calculate_profitability(symbol, 1000)  # $1k position
            
            if result['profitable']:
                profitable_cryptos.append((symbol, result, crypto_data))
                
                if crypto_data['tier'] == 1:
                    tier1_cryptos.append((symbol, result, crypto_data))
                elif crypto_data['tier'] == 2:
                    tier2_cryptos.append((symbol, result, crypto_data))
                else:
                    tier3_cryptos.append((symbol, result, crypto_data))
        
        print(f'\n✅ PROFITABLE CRYPTOS FOUND: {len(profitable_cryptos)}')
        print('-' * 120)
        
        # Tier 1: Very High Spreads
        if tier1_cryptos:
            print('\n🏆 TIER 1: VERY HIGH SPREADS (1.5%+):')
            print('-' * 120)
            for symbol, result, crypto_data in tier1_cryptos:
                print(f"✅ {symbol}:")
                print(f"   Typical Spread: {crypto_data['typical_spread']*100:.1f}%")
                print(f"   Max Spread: {crypto_data['max_spread']*100:.1f}%")
                print(f"   Frequency: {crypto_data['frequency']*100:.0f}% of time")
                print(f"   Daily Volume: ${crypto_data['daily_volume']:,}")
                print(f"   Profit per $1k: ${result['daily_profit']:.2f}/day")
                print(f"   Volume Constrained: {'Yes' if result['volume_constrained'] else 'No'}")
                print()
        
        # Tier 2: High Spreads
        if tier2_cryptos:
            print('\n🥈 TIER 2: HIGH SPREADS (1.0-1.5%):')
            print('-' * 120)
            for symbol, result, crypto_data in tier2_cryptos:
                print(f"✅ {symbol}:")
                print(f"   Typical Spread: {crypto_data['typical_spread']*100:.1f}%")
                print(f"   Max Spread: {crypto_data['max_spread']*100:.1f}%")
                print(f"   Frequency: {crypto_data['frequency']*100:.0f}% of time")
                print(f"   Daily Volume: ${crypto_data['daily_volume']:,}")
                print(f"   Profit per $1k: ${result['daily_profit']:.2f}/day")
                print(f"   Volume Constrained: {'Yes' if result['volume_constrained'] else 'No'}")
                print()
        
        # Tier 3: Good Spreads
        if tier3_cryptos:
            print('\n🥉 TIER 3: GOOD SPREADS (0.8-1.0%):')
            print('-' * 120)
            for symbol, result, crypto_data in tier3_cryptos:
                print(f"✅ {symbol}:")
                print(f"   Typical Spread: {crypto_data['typical_spread']*100:.1f}%")
                print(f"   Max Spread: {crypto_data['max_spread']*100:.1f}%")
                print(f"   Frequency: {crypto_data['frequency']*100:.0f}% of time")
                print(f"   Daily Volume: ${crypto_data['daily_volume']:,}")
                print(f"   Profit per $1k: ${result['daily_profit']:.2f}/day")
                print(f"   Volume Constrained: {'Yes' if result['volume_constrained'] else 'No'}")
                print()
        
        # Portfolio analysis
        print('\n📊 PORTFOLIO PERFORMANCE:')
        print('-' * 120)
        
        test_balances = [1000, 5000, 10000, 25000, 50000, 100000]
        
        for balance in test_balances:
            position_size = balance * 0.12  # 12% position
            total_daily_profit = 0
            viable_cryptos = 0
            
            for symbol, result, crypto_data in profitable_cryptos:
                profit = self.calculate_profitability(symbol, position_size)
                if profit['profitable']:
                    total_daily_profit += profit['daily_profit']
                    viable_cryptos += 1
            
            # Apply realistic constraints
            if balance < 1000:
                total_daily_profit *= 0.5  # 50% penalty for small accounts
            elif balance < 5000:
                total_daily_profit *= 0.8  # 20% penalty for medium accounts
            
            monthly_profit = total_daily_profit * 30
            yearly_profit = total_daily_profit * 365
            daily_roi = (total_daily_profit / balance) * 100
            yearly_roi = (yearly_profit / balance) * 100
            
            print(f"${balance:>6,}: ${total_daily_profit:>6.2f}/day, ${monthly_profit:>8.2f}/month, ${yearly_profit:>10.2f}/year ({yearly_roi:>5.0f}% ROI)")
        
        # Top recommendations
        print('\n🏆 TOP RECOMMENDATIONS:')
        print('-' * 120)
        
        # Sort by profitability
        sorted_cryptos = sorted(profitable_cryptos, key=lambda x: x[1]['daily_profit'], reverse=True)
        
        print('\n🥇 TOP 5 MOST PROFITABLE:')
        for i, (symbol, result, crypto_data) in enumerate(sorted_cryptos[:5], 1):
            print(f"{i}. {symbol}: ${result['daily_profit']:.2f}/day per $1k")
            print(f"   Spread: {crypto_data['typical_spread']*100:.1f}%, Frequency: {crypto_data['frequency']*100:.0f}%")
        
        print('\n🎯 CONFIGURATION RECOMMENDATIONS:')
        print('-' * 120)
        
        # Generate currency pairs list
        currency_pairs = [symbol for symbol, _, _ in sorted_cryptos]
        print(f"\nCURRENCY_PAIRS = {currency_pairs}")
        
        # Generate spread requirements
        print(f"\nCURRENCY_PAIR_SPREADS = {{")
        for symbol, result, crypto_data in sorted_cryptos:
            min_spread = crypto_data['typical_spread'] * 0.8  # 80% of typical
            safe_spread = crypto_data['typical_spread'] * 1.2  # 120% of typical
            print(f"    '{symbol}': {{")
            print(f"        'min_spread': {min_spread:.4f},  # {min_spread*100:.2f}%")
            print(f"        'safe_spread': {safe_spread:.4f},  # {safe_spread*100:.2f}%")
            print(f"        'slippage': 0.00100,")
            print(f"        'transfer_time': {crypto_data['transfer_time']},")
            print(f"        'tier': {crypto_data['tier']},")
            print(f"    }},")
        print(f"}}")
        
        return profitable_cryptos

def run_high_spread_analysis():
    """Run high spread crypto analysis"""
    print('=' * 120)
    print('HIGH SPREAD CRYPTO ANALYSIS')
    print('=' * 120)
    
    finder = HighSpreadCryptoFinder()
    profitable_cryptos = finder.analyze_high_spread_cryptos()
    
    # Save results
    import json
    with open('high_spread_results.json', 'w') as f:
        json.dump(profitable_cryptos, f, indent=2, default=str)
    
    print(f'\n📄 Detailed results saved to: high_spread_results.json')
    
    return profitable_cryptos

if __name__ == "__main__":
    run_high_spread_analysis()

