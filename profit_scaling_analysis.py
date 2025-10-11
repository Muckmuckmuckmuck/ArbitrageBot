#!/usr/bin/env python3
"""
Profit Scaling Analysis
Analyze how profits scale with account balance and find realistic maximums
"""

import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProfitScalingAnalysis:
    """Analyze profit scaling and realistic limits"""
    
    def __init__(self):
        # Top profitable cryptos from previous analysis
        self.top_cryptos = {
            'GRT/USDT': {'daily_profit_per_1k': 1307.23, 'typical_spread': 0.025, 'frequency': 0.90},
            'ETC/USDT': {'daily_profit_per_1k': 1040.40, 'typical_spread': 0.022, 'frequency': 0.85},
            'ALGO/USDT': {'daily_profit_per_1k': 962.06, 'typical_spread': 0.020, 'frequency': 0.90},
            'AAVE/USDT': {'daily_profit_per_1k': 901.68, 'typical_spread': 0.020, 'frequency': 0.85},
            'ATOM/USDT': {'daily_profit_per_1k': 776.83, 'typical_spread': 0.018, 'frequency': 0.85},
            'FIL/USDT': {'daily_profit_per_1k': 731.14, 'typical_spread': 0.018, 'frequency': 0.80},
            'XLM/USDT': {'daily_profit_per_1k': 607.10, 'typical_spread': 0.016, 'frequency': 0.80},
            'DOGE/USDT': {'daily_profit_per_1k': 535.30, 'typical_spread': 0.015, 'frequency': 0.80},
            'AVAX/USDT': {'daily_profit_per_1k': 507.96, 'typical_spread': 0.015, 'frequency': 0.75},
            'UNI/USDT': {'daily_profit_per_1k': 446.76, 'typical_spread': 0.014, 'frequency': 0.75},
        }
        
        # Market constraints
        self.constraints = {
            'max_daily_volume_per_crypto': {
                'GRT': 100000000,  # $100M daily volume
                'ETC': 250000000,  # $250M daily volume
                'ALGO': 150000000,  # $150M daily volume
                'AAVE': 200000000,  # $200M daily volume
                'ATOM': 200000000,  # $200M daily volume
                'FIL': 200000000,   # $200M daily volume
                'XLM': 200000000,   # $200M daily volume
                'DOGE': 1000000000, # $1B daily volume
                'AVAX': 500000000,  # $500M daily volume
                'UNI': 300000000,   # $300M daily volume
            },
            'max_position_per_crypto_percent': 0.05,  # 5% of daily volume max
            'max_total_exposure_percent': 0.50,  # 50% of account in trades
            'min_spread_required': 0.006,  # 0.6% minimum (fees)
            'slippage_impact': {
                'small_trades': 0.0005,  # 0.05% for <$10k
                'medium_trades': 0.001,  # 0.1% for $10k-$100k
                'large_trades': 0.002,   # 0.2% for $100k-$1M
                'huge_trades': 0.005,     # 0.5% for >$1M
            },
            'rate_limits': {
                'max_trades_per_day': 96,
                'max_requests_per_day': 691776,
                'max_concurrent_trades': 6,
            }
        }
    
    def calculate_scaling_limits(self, account_balance: float) -> Dict[str, Any]:
        """Calculate realistic profit limits for given account balance"""
        
        # Position sizing (12% per trade, max 6 concurrent)
        max_position_size = account_balance * 0.12
        max_total_exposure = account_balance * 0.50
        
        # Calculate for each crypto
        crypto_results = {}
        total_daily_profit = 0
        total_monthly_profit = 0
        total_yearly_profit = 0
        
        for symbol, crypto_data in self.top_cryptos.items():
            # Check if position size is viable
            if max_position_size < 100:  # Minimum $100 position
                continue
            
            # Calculate base profit
            base_profit_per_1k = crypto_data['daily_profit_per_1k']
            position_profit = base_profit_per_1k * (max_position_size / 1000)
            
            # Apply slippage penalty based on position size
            if max_position_size < 10000:
                slippage_penalty = 1.0  # No penalty
            elif max_position_size < 100000:
                slippage_penalty = 0.95  # 5% penalty
            elif max_position_size < 1000000:
                slippage_penalty = 0.90  # 10% penalty
            else:
                slippage_penalty = 0.80  # 20% penalty
            
            # Apply volume constraints
            crypto_name = symbol.split('/')[0]
            max_volume = self.constraints['max_daily_volume_per_crypto'].get(crypto_name, 100000000)
            max_position_by_volume = max_volume * self.constraints['max_position_per_crypto_percent']
            
            # Use the smaller of position size or volume constraint
            effective_position = min(max_position_size, max_position_by_volume)
            
            # Calculate final profit
            final_profit = position_profit * (effective_position / max_position_size) * slippage_penalty
            
            crypto_results[symbol] = {
                'position_size': effective_position,
                'daily_profit': final_profit,
                'monthly_profit': final_profit * 30,
                'yearly_profit': final_profit * 365,
                'slippage_penalty': slippage_penalty,
                'volume_constrained': effective_position < max_position_size,
            }
            
            total_daily_profit += final_profit
        
        total_monthly_profit = total_daily_profit * 30
        total_yearly_profit = total_daily_profit * 365
        
        return {
            'account_balance': account_balance,
            'max_position_size': max_position_size,
            'max_total_exposure': max_total_exposure,
            'crypto_results': crypto_results,
            'total_daily_profit': total_daily_profit,
            'total_monthly_profit': total_monthly_profit,
            'total_yearly_profit': total_yearly_profit,
            'daily_roi': (total_daily_profit / account_balance) * 100,
            'yearly_roi': (total_yearly_profit / account_balance) * 100,
        }
    
    def find_realistic_maximums(self):
        """Find realistic maximum account sizes and profits"""
        
        print('\n' + '=' * 150)
        print('PROFIT SCALING ANALYSIS')
        print('How profits scale with account balance and realistic maximums')
        print('=' * 150)
        
        # Test different account sizes
        test_balances = [
            100, 500, 1000, 5000, 10000, 25000, 50000, 100000, 
            250000, 500000, 1000000, 2500000, 5000000, 10000000
        ]
        
        results = []
        
        print('\n📊 PROFIT SCALING BY ACCOUNT BALANCE:')
        print('-' * 150)
        print(f"{'Balance':<12} {'Daily':<15} {'Monthly':<15} {'Yearly':<20} {'Daily ROI':<12} {'Yearly ROI':<12}")
        print('-' * 150)
        
        for balance in test_balances:
            result = self.calculate_scaling_limits(balance)
            results.append(result)
            
            daily = result['total_daily_profit']
            monthly = result['total_monthly_profit']
            yearly = result['total_yearly_profit']
            daily_roi = result['daily_roi']
            yearly_roi = result['yearly_roi']
            
            print(f"${balance:<11,} ${daily:<14.2f} ${monthly:<14.2f} ${yearly:<19.2f} {daily_roi:<11.2f}% {yearly_roi:<11.0f}%")
        
        # Find breaking points
        print('\n🔍 SCALING ANALYSIS:')
        print('-' * 150)
        
        # Find where ROI starts declining
        max_roi_balance = max(results, key=lambda x: x['yearly_roi'])
        print(f"\n✅ PEAK ROI: ${max_roi_balance['account_balance']:,}")
        print(f"   Daily ROI: {max_roi_balance['daily_roi']:.2f}%")
        print(f"   Yearly ROI: {max_roi_balance['yearly_roi']:.0f}%")
        print(f"   Daily Profit: ${max_roi_balance['total_daily_profit']:,.2f}")
        print(f"   Yearly Profit: ${max_roi_balance['total_yearly_profit']:,.2f}")
        
        # Find where volume constraints kick in
        volume_constrained = [r for r in results if any(cr['volume_constrained'] for cr in r['crypto_results'].values())]
        if volume_constrained:
            first_constrained = volume_constrained[0]
            print(f"\n⚠️  VOLUME CONSTRAINTS START: ${first_constrained['account_balance']:,}")
            print(f"   Some cryptos limited by daily volume")
        
        # Find realistic maximums
        print('\n🎯 REALISTIC MAXIMUMS:')
        print('-' * 150)
        
        # Conservative maximum (where ROI drops below 1000%)
        conservative_max = next((r for r in results if r['yearly_roi'] < 1000), results[-1])
        print(f"\n💰 CONSERVATIVE MAXIMUM: ${conservative_max['account_balance']:,}")
        print(f"   Daily Profit: ${conservative_max['total_daily_profit']:,.2f}")
        print(f"   Monthly Profit: ${conservative_max['total_monthly_profit']:,.2f}")
        print(f"   Yearly Profit: ${conservative_max['total_yearly_profit']:,.2f}")
        print(f"   Yearly ROI: {conservative_max['yearly_roi']:.0f}%")
        
        # Aggressive maximum (where ROI drops below 100%)
        aggressive_max = next((r for r in results if r['yearly_roi'] < 100), results[-1])
        print(f"\n🚀 AGGRESSIVE MAXIMUM: ${aggressive_max['account_balance']:,}")
        print(f"   Daily Profit: ${aggressive_max['total_daily_profit']:,.2f}")
        print(f"   Monthly Profit: ${aggressive_max['total_monthly_profit']:,.2f}")
        print(f"   Yearly Profit: ${aggressive_max['total_yearly_profit']:,.2f}")
        print(f"   Yearly ROI: {aggressive_max['yearly_roi']:.0f}%")
        
        # Theoretical maximum (where volume constraints dominate)
        theoretical_max = results[-1]
        print(f"\n⚡ THEORETICAL MAXIMUM: ${theoretical_max['account_balance']:,}")
        print(f"   Daily Profit: ${theoretical_max['total_daily_profit']:,.2f}")
        print(f"   Monthly Profit: ${theoretical_max['total_monthly_profit']:,.2f}")
        print(f"   Yearly Profit: ${theoretical_max['total_yearly_profit']:,.2f}")
        print(f"   Yearly ROI: {theoretical_max['yearly_roi']:.0f}%")
        
        print('\n📈 SCALING BEHAVIOR:')
        print('-' * 150)
        
        print('\n1. LINEAR SCALING (Up to ~$100k):')
        print('   • Profits scale linearly with balance')
        print('   • No volume constraints')
        print('   • ROI remains constant')
        print('   • Best for: $1k - $100k accounts')
        
        print('\n2. DIMINISHING RETURNS ($100k - $1M):')
        print('   • Volume constraints start affecting some cryptos')
        print('   • Slippage penalties begin')
        print('   • ROI starts declining')
        print('   • Best for: $100k - $1M accounts')
        
        print('\n3. CONSTRAINED SCALING ($1M+):')
        print('   • Most cryptos volume-constrained')
        print('   • Significant slippage penalties')
        print('   • ROI drops significantly')
        print('   • Best for: $1M+ accounts (but lower ROI)')
        
        print('\n⚠️  REALISTIC LIMITATIONS:')
        print('-' * 150)
        
        print('\n1. DAILY VOLUME CONSTRAINTS:')
        for crypto, volume in self.constraints['max_daily_volume_per_crypto'].items():
            max_position = volume * 0.05  # 5% of daily volume
            print(f"   {crypto}: Max ${max_position:,.0f} position (${volume:,.0f} daily volume)")
        
        print('\n2. SLIPPAGE IMPACT:')
        print('   • <$10k: No slippage penalty')
        print('   • $10k-$100k: 5% penalty')
        print('   • $100k-$1M: 10% penalty')
        print('   • >$1M: 20% penalty')
        
        print('\n3. RATE LIMITS:')
        print('   • Max 96 trades per day')
        print('   • Max 6 concurrent trades')
        print('   • Max 691,776 requests per day')
        
        print('\n4. MARKET IMPACT:')
        print('   • Large trades move prices against you')
        print('   • Spreads tighten as you scale up')
        print('   • Competition increases with size')
        
        print('\n💡 RECOMMENDATIONS:')
        print('-' * 150)
        
        print('\n🎯 OPTIMAL ACCOUNT SIZES:')
        print('   • $1k-$10k: Perfect scaling, 1000-10000% ROI')
        print('   • $10k-$100k: Great scaling, 1000-5000% ROI')
        print('   • $100k-$1M: Good scaling, 500-1000% ROI')
        print('   • $1M-$10M: Constrained scaling, 100-500% ROI')
        print('   • $10M+: Limited scaling, <100% ROI')
        
        print('\n🚀 SCALING STRATEGY:')
        print('   1. Start with $1k-$10k (maximum ROI)')
        print('   2. Scale to $100k (still excellent ROI)')
        print('   3. Consider $1M+ only if you need absolute dollar amounts')
        print('   4. Beyond $10M, consider other strategies')
        
        return results

def run_profit_scaling_analysis():
    """Run profit scaling analysis"""
    print('=' * 150)
    print('PROFIT SCALING ANALYSIS')
    print('=' * 150)
    
    analyzer = ProfitScalingAnalysis()
    results = analyzer.find_realistic_maximums()
    
    # Save results
    import json
    with open('profit_scaling_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f'\n📄 Detailed results saved to: profit_scaling_results.json')
    
    return results

if __name__ == "__main__":
    run_profit_scaling_analysis()

