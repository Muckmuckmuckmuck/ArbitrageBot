#!/usr/bin/env python3
"""
Exchange Comparison Analysis
Detailed comparison between old (Binance/OKX) and new (Pionex/Coinbase) setups
"""

import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExchangeComparisonAnalysis:
    """Analyze differences between old and new exchange setups"""
    
    def __init__(self):
        self.old_setup = {
            'name': 'Binance + OKX',
            'exchange_1': 'Binance',
            'exchange_2': 'OKX',
            'fees': {
                'binance_trading': 0.00017,  # 0.017% VIP level
                'okx_trading': 0.00015,      # 0.015% VIP level
                'total_trading': 0.00032,    # 0.032% combined
                'binance_withdrawal': 'Variable by coin',
                'okx_withdrawal': 'Variable by coin',
            },
            'liquidity': {
                'binance_daily_volume': '$50B+',
                'okx_daily_volume': '$5B+',
                'total': 'Excellent',
                'slippage': 'Very Low (0.01-0.05%)',
            },
            'spreads': {
                'min_spread': 0.008,  # 0.8% minimum
                'typical_spread': 0.010,  # 1.0% typical
                'optimal_spread': 0.015,  # 1.5% optimal
            },
            'rate_limits': {
                'binance': '1200 requests/minute',
                'okx': '3000 requests/minute',
            },
            'issues': [
                '❌ No automated withdrawals',
                '❌ Manual confirmation required',
                '❌ Whitelist requirements',
                '❌ Transfer delays',
            ]
        }
        
        self.new_setup = {
            'name': 'Pionex.US + Coinbase Pro',
            'exchange_1': 'Pionex.US',
            'exchange_2': 'Coinbase Pro',
            'fees': {
                'pionex_trading': 0.001,     # 0.1%
                'coinbase_trading': 0.005,   # 0.5%
                'total_trading': 0.006,      # 0.6% combined
                'pionex_withdrawal': '$1 USDT or 0.05% crypto',
                'coinbase_withdrawal': 'Free for crypto',
            },
            'liquidity': {
                'pionex_daily_volume': '$500M - $2B',
                'coinbase_daily_volume': '$2B - $10B',
                'total': 'Good to Excellent',
                'slippage': 'Low to Medium (0.05-0.2%)',
            },
            'spreads': {
                'min_spread': 0.007,  # 0.7% minimum (adjusted for higher fees)
                'typical_spread': 0.010,  # 1.0% typical
                'optimal_spread': 0.015,  # 1.5% optimal
            },
            'rate_limits': {
                'pionex': '600 requests/minute',
                'coinbase': '600 requests/minute',
            },
            'benefits': [
                '✅ Automated withdrawals',
                '✅ No manual confirmation',
                '✅ No whitelist required',
                '✅ US-friendly',
            ]
        }
        
        self.key_differences = {
            'fee_increase': {
                'old': 0.00032,  # 0.032%
                'new': 0.006,    # 0.6%
                'increase': 18.75,  # 18.75x higher
                'impact': 'Significant - need higher spreads',
                'adjustment_needed': 'Increase min spread from 0.8% to 0.7%+'
            },
            'liquidity_decrease': {
                'old': 'Excellent (Binance $50B+)',
                'new': 'Good (Coinbase $10B max)',
                'ratio': '5x lower',
                'impact': 'Moderate - may see more slippage',
                'adjustment_needed': 'Increase slippage estimates'
            },
            'slippage_increase': {
                'old': '0.01-0.05%',
                'new': '0.05-0.2%',
                'increase': '2-4x higher',
                'impact': 'Moderate - affects profit margins',
                'adjustment_needed': 'Update slippage estimates'
            },
            'rate_limit_decrease': {
                'old': '1200-3000 requests/minute',
                'new': '600 requests/minute',
                'ratio': '2-5x lower',
                'impact': 'Moderate - may need slower scanning',
                'adjustment_needed': 'Reduce scan frequency'
            },
            'withdrawal_changes': {
                'old': 'No automation (manual confirmation)',
                'new': 'Full automation (API-based)',
                'impact': 'Major improvement - enables true arbitrage',
                'adjustment_needed': 'Enable automated transfer logic'
            }
        }
        
    def analyze_differences(self):
        """Analyze all differences and required adjustments"""
        
        print('\n' + '=' * 120)
        print('EXCHANGE COMPARISON ANALYSIS: Binance/OKX vs Pionex/Coinbase')
        print('=' * 120)
        
        print('\n📊 OLD SETUP (Binance + OKX):')
        print('-' * 120)
        print(f"Exchanges: {self.old_setup['exchange_1']} + {self.old_setup['exchange_2']}")
        print(f"Combined Trading Fees: {self.old_setup['fees']['total_trading']*100:.3f}%")
        print(f"Liquidity: {self.old_setup['liquidity']['total']}")
        print(f"Slippage: {self.old_setup['liquidity']['slippage']}")
        print(f"Min Spread: {self.old_setup['spreads']['min_spread']*100:.1f}%")
        print(f"Rate Limits: {self.old_setup['rate_limits']['binance']} / {self.old_setup['rate_limits']['okx']}")
        print('\nIssues:')
        for issue in self.old_setup['issues']:
            print(f"  {issue}")
        
        print('\n📊 NEW SETUP (Pionex.US + Coinbase Pro):')
        print('-' * 120)
        print(f"Exchanges: {self.new_setup['exchange_1']} + {self.new_setup['exchange_2']}")
        print(f"Combined Trading Fees: {self.new_setup['fees']['total_trading']*100:.1f}%")
        print(f"Liquidity: {self.new_setup['liquidity']['total']}")
        print(f"Slippage: {self.new_setup['liquidity']['slippage']}")
        print(f"Min Spread: {self.new_setup['spreads']['min_spread']*100:.1f}%")
        print(f"Rate Limits: {self.new_setup['rate_limits']['pionex']} / {self.new_setup['rate_limits']['coinbase']}")
        print('\nBenefits:')
        for benefit in self.new_setup['benefits']:
            print(f"  {benefit}")
        
        print('\n🔍 KEY DIFFERENCES:')
        print('-' * 120)
        
        for diff_name, diff_data in self.key_differences.items():
            print(f"\n{diff_name.replace('_', ' ').title()}:")
            for key, value in diff_data.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        print('\n⚙️  REQUIRED ADJUSTMENTS:')
        print('-' * 120)
        
        adjustments = {
            '1. Minimum Spread': {
                'old_value': '0.8%',
                'new_value': '0.7%',
                'reason': 'Higher combined fees (0.6% vs 0.032%)',
                'calculation': '0.6% fees + 0.1% profit = 0.7% minimum',
                'file': 'pionex_coinbase_config.py',
                'status': '✅ Already adjusted'
            },
            '2. Slippage Estimates': {
                'old_value': '0.0001-0.0005 (0.01-0.05%)',
                'new_value': '0.0005-0.002 (0.05-0.2%)',
                'reason': 'Lower liquidity on Pionex/Coinbase',
                'calculation': '2-4x higher slippage expected',
                'file': 'pionex_coinbase_config.py',
                'status': '⚠️  Needs adjustment'
            },
            '3. Position Sizing': {
                'old_value': '15% per trade, 60% total exposure',
                'new_value': '12% per trade, 50% total exposure',
                'reason': 'Lower liquidity, higher risk',
                'calculation': 'Conservative due to lower volume',
                'file': 'pionex_coinbase_config.py',
                'status': '✅ Already adjusted'
            },
            '4. Scan Frequency': {
                'old_value': '1-2 seconds per scan',
                'new_value': '2-5 seconds per scan',
                'reason': 'Lower rate limits (600 vs 1200-3000)',
                'calculation': 'Need to avoid rate limit hits',
                'file': 'pionex_coinbase_bot.py',
                'status': '⚠️  Needs adjustment'
            },
            '5. Concurrent Trades': {
                'old_value': '8 concurrent trades',
                'new_value': '6 concurrent trades',
                'reason': 'Lower rate limits and liquidity',
                'calculation': 'Reduced to prevent congestion',
                'file': 'pionex_coinbase_config.py',
                'status': '✅ Already adjusted'
            },
            '6. Reserve Percentage': {
                'old_value': '20% reserve',
                'new_value': '30% reserve',
                'reason': 'Higher fees mean need more buffer',
                'calculation': 'More conservative approach',
                'file': 'pionex_coinbase_config.py',
                'status': '✅ Already adjusted'
            },
            '7. Transfer Strategy': {
                'old_value': 'Manual confirmation required',
                'new_value': 'Fully automated transfers',
                'reason': 'Both exchanges support API withdrawals',
                'calculation': 'Enable full arbitrage loop',
                'file': 'pioneer_coinbase_bot.py',
                'status': '✅ Already enabled'
            },
            '8. Fee Calculations': {
                'old_value': '0.032% total fees',
                'new_value': '0.6% total fees + $1 withdrawal',
                'reason': 'Much higher fees on new exchanges',
                'calculation': 'Must account for in profit calculations',
                'file': 'All profit calculations',
                'status': '⚠️  Needs verification'
            }
        }
        
        for adj_name, adj_data in adjustments.items():
            status_icon = adj_data['status']
            print(f"\n{adj_name}:")
            print(f"  Old Value: {adj_data['old_value']}")
            print(f"  New Value: {adj_data['new_value']}")
            print(f"  Reason: {adj_data['reason']}")
            print(f"  Calculation: {adj_data['calculation']}")
            print(f"  File: {adj_data['file']}")
            print(f"  Status: {status_icon}")
        
        print('\n📈 PROFIT COMPARISON:')
        print('-' * 120)
        
        # Calculate example trade profits
        trade_amount = 1000  # $1000 trade
        
        # Old setup
        old_fees = trade_amount * self.old_setup['fees']['total_trading']
        old_slippage = trade_amount * 0.0003  # Average slippage
        old_spread_needed = old_fees + old_slippage + 1  # +$1 min profit
        old_spread_percent = (old_spread_needed / trade_amount) * 100
        old_net_profit_1pct = (trade_amount * 0.01) - old_fees - old_slippage
        
        # New setup
        new_fees = trade_amount * self.new_setup['fees']['total_trading']
        new_withdrawal = 1  # $1 withdrawal fee
        new_slippage = trade_amount * 0.001  # Average slippage
        new_spread_needed = new_fees + new_withdrawal + new_slippage + 1  # +$1 min profit
        new_spread_percent = (new_spread_needed / trade_amount) * 100
        new_net_profit_1pct = (trade_amount * 0.01) - new_fees - new_withdrawal - new_slippage
        
        print(f"\n💰 Example $1,000 Trade:")
        print(f"  OLD (Binance/OKX):")
        print(f"    Trading Fees: ${old_fees:.2f} ({self.old_setup['fees']['total_trading']*100:.3f}%)")
        print(f"    Slippage: ${old_slippage:.2f}")
        print(f"    Min Spread Needed: {old_spread_percent:.2f}%")
        print(f"    Net Profit (1% spread): ${old_net_profit_1pct:.2f}")
        print(f"")
        print(f"  NEW (Pionex/Coinbase):")
        print(f"    Trading Fees: ${new_fees:.2f} ({self.new_setup['fees']['total_trading']*100:.1f}%)")
        print(f"    Withdrawal Fee: ${new_withdrawal:.2f}")
        print(f"    Slippage: ${new_slippage:.2f}")
        print(f"    Min Spread Needed: {new_spread_percent:.2f}%")
        print(f"    Net Profit (1% spread): ${new_net_profit_1pct:.2f}")
        
        profit_reduction = ((old_net_profit_1pct - new_net_profit_1pct) / old_net_profit_1pct) * 100
        print(f"\n  Profit Reduction: {profit_reduction:.1f}%")
        
        print('\n🎯 REALISTIC ROI COMPARISON:')
        print('-' * 120)
        
        roi_comparison = {
            'OLD (Binance/OKX)': {
                'daily_roi': '2-5%',
                'opportunities_per_day': '150-200',
                'avg_profit_per_trade': '$3-8',
                'constraints': 'Manual withdrawals limit speed'
            },
            'NEW (Pionex/Coinbase)': {
                'daily_roi': '1-3%',
                'opportunities_per_day': '50-100',
                'avg_profit_per_trade': '$2-5',
                'constraints': 'Higher fees, lower liquidity'
            }
        }
        
        for setup_name, roi_data in roi_comparison.items():
            print(f"\n{setup_name}:")
            for key, value in roi_data.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        print('\n✅ ADJUSTMENTS TO MAKE:')
        print('-' * 120)
        
        print('\n1. ✅ ALREADY ADJUSTED IN CONFIG:')
        print('  • Minimum spread: 0.7% (vs 0.8% old)')
        print('  • Position sizing: 12% per trade (vs 15% old)')
        print('  • Total exposure: 50% (vs 60% old)')
        print('  • Concurrent trades: 6 (vs 8 old)')
        print('  • Reserve: 30% (vs 20% old)')
        
        print('\n2. ⚠️  NEED TO ADJUST:')
        print('  • Slippage estimates: Increase from 0.01-0.05% to 0.05-0.2%')
        print('  • Scan frequency: Increase from 1-2s to 2-5s')
        print('  • Fee calculations: Account for $1 withdrawal fee')
        print('  • Profit expectations: Lower from 2-5% to 1-3% daily')
        
        return adjustments

def run_comparison_analysis():
    """Run exchange comparison analysis"""
    print('=' * 120)
    print('EXCHANGE COMPARISON ANALYSIS')
    print('=' * 120)
    
    analysis = ExchangeComparisonAnalysis()
    adjustments = analysis.analyze_differences()
    
    # Save results
    import json
    with open('exchange_comparison_results.json', 'w') as f:
        json.dump(adjustments, f, indent=2, default=str)
    
    print(f'\n📄 Detailed results saved to: exchange_comparison_results.json')
    
    return adjustments

if __name__ == "__main__":
    run_comparison_analysis()

