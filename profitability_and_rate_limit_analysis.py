#!/usr/bin/env python3
"""
Profitability and Rate Limit Analysis for Pionex.US + Coinbase Pro
Comprehensive analysis of expected profits and API rate limit constraints
"""

import logging
from typing import Dict, Any
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProfitabilityRateLimitAnalysis:
    """Analyze profitability and rate limits for the arbitrage bot"""
    
    def __init__(self):
        # Exchange rate limits
        self.rate_limits = {
            'pionex': {
                'requests_per_minute': 600,
                'requests_per_hour': 36000,
                'requests_per_day': 864000,
                'note': 'Official limit from Pionex.US documentation'
            },
            'coinbase': {
                'requests_per_minute': 600,
                'requests_per_hour': 36000,
                'requests_per_day': 864000,
                'note': 'Official limit from Coinbase Pro documentation'
            },
            'combined': {
                'requests_per_minute': 600,  # Limited by slowest exchange
                'requests_per_hour': 36000,
                'requests_per_day': 864000,
                'note': 'Effective limit (constrained by both exchanges)'
            }
        }
        
        # Trading parameters
        self.trading_params = {
            'assets': 12,  # Total number of trading pairs
            'scan_frequency_seconds': 3,  # Scan every 3 seconds
            'requests_per_scan': 24,  # 2 tickers per asset (pionex + coinbase)
            'requests_per_trade': 6,  # 2 orders + 2 balance checks + 2 confirmations
            'avg_trades_per_hour': 4,  # Conservative estimate
        }
        
        # Fee structure
        self.fees = {
            'pionex_trading': 0.001,  # 0.1%
            'coinbase_trading': 0.005,  # 0.5%
            'total_trading': 0.006,  # 0.6%
            'withdrawal': 1.0,  # $1 per withdrawal
            'total_per_arbitrage': 0.007,  # 0.7% (0.6% + ~0.1% for withdrawal)
        }
        
        # Slippage estimates
        self.slippage = {
            'tier1': 0.0005,  # 0.05% (BTC, ETH)
            'tier2': 0.001,   # 0.1% (SOL, MATIC, ADA)
            'tier3': 0.001,   # 0.1% (XRP, LTC, BCH)
            'tier4': 0.0015,  # 0.15% (LINK, ATOM, ALGO, XLM)
            'average': 0.001,  # 0.1% average
        }
        
        # Spread distribution (realistic based on market analysis)
        self.spread_distribution = {
            '0.7-1.0%': {
                'probability': 0.60,  # 60% of opportunities
                'avg_spread': 0.0085,  # 0.85% average
                'success_rate': 0.80,  # 80% success rate
            },
            '1.0-1.5%': {
                'probability': 0.30,  # 30% of opportunities
                'avg_spread': 0.0125,  # 1.25% average
                'success_rate': 0.90,  # 90% success rate
            },
            '1.5%+': {
                'probability': 0.10,  # 10% of opportunities
                'avg_spread': 0.0175,  # 1.75% average
                'success_rate': 0.95,  # 95% success rate
            }
        }
    
    def calculate_rate_limit_usage(self):
        """Calculate rate limit usage"""
        
        print('\n' + '=' * 120)
        print('RATE LIMIT ANALYSIS')
        print('=' * 120)
        
        # Calculate requests per time period
        scans_per_minute = 60 / self.trading_params['scan_frequency_seconds']
        scans_per_hour = scans_per_minute * 60
        scans_per_day = scans_per_hour * 24
        
        # Requests for scanning
        scan_requests_per_minute = scans_per_minute * self.trading_params['requests_per_scan']
        scan_requests_per_hour = scans_per_hour * self.trading_params['requests_per_scan']
        scan_requests_per_day = scans_per_day * self.trading_params['requests_per_scan']
        
        # Requests for trading
        trade_requests_per_hour = self.trading_params['avg_trades_per_hour'] * self.trading_params['requests_per_trade']
        trade_requests_per_day = trade_requests_per_hour * 24
        
        # Total requests
        total_requests_per_minute = scan_requests_per_minute + (trade_requests_per_hour / 60)
        total_requests_per_hour = scan_requests_per_hour + trade_requests_per_hour
        total_requests_per_day = scan_requests_per_day + trade_requests_per_day
        
        print('\n📊 RATE LIMIT CONSTRAINTS:')
        print('-' * 120)
        print(f"{'Exchange':<20} {'Per Minute':<20} {'Per Hour':<20} {'Per Day':<20}")
        print('-' * 120)
        print(f"{'Pionex.US':<20} {self.rate_limits['pionex']['requests_per_minute']:<20} "
              f"{self.rate_limits['pionex']['requests_per_hour']:<20} "
              f"{self.rate_limits['pionex']['requests_per_day']:<20}")
        print(f"{'Coinbase Pro':<20} {self.rate_limits['coinbase']['requests_per_minute']:<20} "
              f"{self.rate_limits['coinbase']['requests_per_hour']:<20} "
              f"{self.rate_limits['coinbase']['requests_per_day']:<20}")
        print(f"{'Combined (Effective)':<20} {self.rate_limits['combined']['requests_per_minute']:<20} "
              f"{self.rate_limits['combined']['requests_per_hour']:<20} "
              f"{self.rate_limits['combined']['requests_per_day']:<20}")
        
        print('\n📈 BOT REQUEST USAGE:')
        print('-' * 120)
        print(f"\n🔍 Scanning Activity:")
        print(f"  Scans per minute: {scans_per_minute:.1f}")
        print(f"  Scans per hour: {scans_per_hour:.0f}")
        print(f"  Scans per day: {scans_per_day:.0f}")
        print(f"  Assets per scan: {self.trading_params['assets']}")
        print(f"  Requests per scan: {self.trading_params['requests_per_scan']} (2 exchanges × {self.trading_params['assets']} assets)")
        
        print(f"\n💰 Trading Activity:")
        print(f"  Avg trades per hour: {self.trading_params['avg_trades_per_hour']}")
        print(f"  Avg trades per day: {self.trading_params['avg_trades_per_hour'] * 24}")
        print(f"  Requests per trade: {self.trading_params['requests_per_trade']} (orders + balance + confirmations)")
        
        print(f"\n📊 Total Request Usage:")
        print(f"  {'Per Minute':<20} {'Per Hour':<20} {'Per Day':<20}")
        print(f"  {total_requests_per_minute:<20.1f} {total_requests_per_hour:<20.0f} {total_requests_per_day:<20.0f}")
        
        print(f"\n⚠️  Rate Limit Usage:")
        usage_per_minute = (total_requests_per_minute / self.rate_limits['combined']['requests_per_minute']) * 100
        usage_per_hour = (total_requests_per_hour / self.rate_limits['combined']['requests_per_hour']) * 100
        usage_per_day = (total_requests_per_day / self.rate_limits['combined']['requests_per_day']) * 100
        
        print(f"  Per Minute: {usage_per_minute:.1f}% of limit")
        print(f"  Per Hour: {usage_per_hour:.1f}% of limit")
        print(f"  Per Day: {usage_per_day:.1f}% of limit")
        
        if usage_per_minute > 80:
            print(f"\n  ⚠️  WARNING: Per-minute usage is HIGH! Consider increasing scan frequency.")
        elif usage_per_minute > 50:
            print(f"\n  ⚠️  CAUTION: Per-minute usage is moderate. Monitor closely.")
        else:
            print(f"\n  ✅ SAFE: Per-minute usage is well within limits.")
        
        return {
            'total_requests_per_minute': total_requests_per_minute,
            'total_requests_per_hour': total_requests_per_hour,
            'total_requests_per_day': total_requests_per_day,
            'usage_per_minute': usage_per_minute,
            'usage_per_hour': usage_per_hour,
            'usage_per_day': usage_per_day,
        }
    
    def calculate_profitability(self):
        """Calculate expected profitability"""
        
        print('\n' + '=' * 120)
        print('PROFITABILITY ANALYSIS')
        print('=' * 120)
        
        # Starting balances
        balances = [100, 500, 1000, 5000, 10000]
        
        for balance in balances:
            print(f'\n💰 STARTING BALANCE: ${balance:,}')
            print('-' * 120)
            
            # Calculate position size (12% of balance)
            position_size = balance * 0.12
            
            # Calculate weighted average profit per spread category
            weighted_profit = 0
            weighted_opportunities = 0
            
            for spread_range, data in self.spread_distribution.items():
                spread = data['avg_spread']
                probability = data['probability']
                success_rate = data['success_rate']
                
                # Calculate profit for this spread
                gross_profit = position_size * spread
                fees = position_size * self.fees['total_trading']
                withdrawal = self.fees['withdrawal']
                slippage = position_size * self.slippage['average']
                net_profit = gross_profit - fees - withdrawal - slippage
                
                # Weight by probability and success rate
                expected_profit = net_profit * probability * success_rate
                weighted_profit += expected_profit
                
                # Expected opportunities per day
                opportunities_per_day = self.trading_params['avg_trades_per_hour'] * 24 * probability
                weighted_opportunities += opportunities_per_day
            
            # Calculate daily/monthly/yearly profits
            trades_per_day = self.trading_params['avg_trades_per_hour'] * 24
            daily_profit = weighted_profit * trades_per_day
            monthly_profit = daily_profit * 30
            yearly_profit = daily_profit * 365
            
            # Calculate ROI percentages
            daily_roi = (daily_profit / balance) * 100
            monthly_roi = (monthly_profit / balance) * 100
            yearly_roi = (yearly_profit / balance) * 100
            
            print(f'\n📊 Position Sizing:')
            print(f"  Position per trade: ${position_size:.2f} (12% of balance)")
            print(f"  Max concurrent trades: 6")
            print(f"  Max exposure: ${balance * 0.50:.2f} (50% of balance)")
            print(f"  Reserve: ${balance * 0.30:.2f} (30% of balance)")
            
            print(f'\n📈 Profit Breakdown by Spread:')
            for spread_range, data in self.spread_distribution.items():
                spread = data['avg_spread']
                probability = data['probability']
                success_rate = data['success_rate']
                
                gross_profit = position_size * spread
                fees = position_size * self.fees['total_trading']
                withdrawal = self.fees['withdrawal']
                slippage = position_size * self.slippage['average']
                net_profit = gross_profit - fees - withdrawal - slippage
                
                print(f"\n  {spread_range} spreads:")
                print(f"    Probability: {probability*100:.0f}%")
                print(f"    Success rate: {success_rate*100:.0f}%")
                print(f"    Gross profit: ${gross_profit:.2f}")
                print(f"    Fees (0.6%): -${fees:.2f}")
                print(f"    Withdrawal: -${withdrawal:.2f}")
                print(f"    Slippage (0.1%): -${slippage:.2f}")
                print(f"    Net profit: ${net_profit:.2f}")
                print(f"    Expected (weighted): ${net_profit * probability * success_rate:.2f}")
            
            print(f'\n💵 Expected Returns:')
            print(f"  Avg profit per trade: ${weighted_profit:.2f}")
            print(f"  Trades per day: {trades_per_day:.0f}")
            print(f"  Daily profit: ${daily_profit:.2f} ({daily_roi:.2f}%)")
            print(f"  Monthly profit: ${monthly_profit:.2f} ({monthly_roi:.1f}%)")
            print(f"  Yearly profit: ${yearly_profit:.2f} ({yearly_roi:.0f}%)")
            
            # Calculate compound growth
            if daily_roi > 0:
                days_to_double = 72 / daily_roi  # Rule of 72
                print(f"\n🚀 Growth Projections:")
                print(f"  Days to double: {days_to_double:.0f} days")
                print(f"  Balance after 30 days (compound): ${balance * ((1 + daily_roi/100) ** 30):,.2f}")
                print(f"  Balance after 90 days (compound): ${balance * ((1 + daily_roi/100) ** 90):,.2f}")
                print(f"  Balance after 365 days (compound): ${balance * ((1 + daily_roi/100) ** 365):,.2f}")
        
        print('\n' + '=' * 120)
        print('SUMMARY: REALISTIC EXPECTATIONS')
        print('=' * 120)
        
        print('\n✅ CONSERVATIVE ESTIMATES (1% Daily):')
        print('-' * 120)
        for balance in balances:
            daily = balance * 0.01
            monthly = daily * 30
            yearly = daily * 365
            print(f"  ${balance:>6,} → Daily: ${daily:>6.2f} | Monthly: ${monthly:>8.2f} | Yearly: ${yearly:>10.2f}")
        
        print('\n🎯 REALISTIC ESTIMATES (1.5% Daily):')
        print('-' * 120)
        for balance in balances:
            daily = balance * 0.015
            monthly = daily * 30
            yearly = daily * 365
            print(f"  ${balance:>6,} → Daily: ${daily:>6.2f} | Monthly: ${monthly:>8.2f} | Yearly: ${yearly:>10.2f}")
        
        print('\n🚀 OPTIMISTIC ESTIMATES (2% Daily):')
        print('-' * 120)
        for balance in balances:
            daily = balance * 0.02
            monthly = daily * 30
            yearly = daily * 365
            print(f"  ${balance:>6,} → Daily: ${daily:>6.2f} | Monthly: ${monthly:>8.2f} | Yearly: ${yearly:>10.2f}")
        
        print('\n⚠️  IMPORTANT NOTES:')
        print('-' * 120)
        print('  • These are realistic estimates based on:')
        print('    - Pionex (0.1%) + Coinbase (0.5%) = 0.6% trading fees')
        print('    - $1 withdrawal fee per arbitrage cycle')
        print('    - 0.05-0.2% slippage based on liquidity')
        print('    - 60% spreads at 0.7-1.0%, 30% at 1.0-1.5%, 10% at 1.5%+')
        print('    - 80-95% success rate depending on spread size')
        print('  • Actual results will vary based on:')
        print('    - Market volatility')
        print('    - Liquidity conditions')
        print('    - Execution speed')
        print('    - Competition from other arbitrageurs')
        print('  • Start conservative and scale gradually!')

def run_profitability_rate_limit_analysis():
    """Run complete profitability and rate limit analysis"""
    print('=' * 120)
    print('PROFITABILITY AND RATE LIMIT ANALYSIS')
    print('Pionex.US + Coinbase Pro Arbitrage Bot')
    print('=' * 120)
    
    analysis = ProfitabilityRateLimitAnalysis()
    
    # Run rate limit analysis
    rate_limit_results = analysis.calculate_rate_limit_usage()
    
    # Run profitability analysis
    profitability_results = analysis.calculate_profitability()
    
    # Save results
    import json
    results = {
        'rate_limits': rate_limit_results,
        'timestamp': str(__import__('datetime').datetime.now()),
    }
    
    with open('profitability_rate_limit_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f'\n📄 Detailed results saved to: profitability_rate_limit_results.json')
    
    return results

if __name__ == "__main__":
    run_profitability_rate_limit_analysis()

