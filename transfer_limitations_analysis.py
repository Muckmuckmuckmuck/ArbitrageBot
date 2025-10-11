#!/usr/bin/env python3
"""
Transfer Limitations Analysis
Analyzes rate limits and restrictions for transfers between Binance and OKX
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TransferLimitation:
    """Transfer limitation data"""
    exchange: str
    limitation_type: str
    limit_value: Any
    time_window: str
    description: str
    impact: str

class TransferLimitationsAnalysis:
    """Analysis of transfer limitations between Binance and OKX"""
    
    def __init__(self):
        self.binance_limitations = {
            'withdrawal_limits': {
                'daily_limit_usdt': 100000,  # $100,000 daily withdrawal limit (unverified accounts)
                'daily_limit_verified': 2000000,  # $2M daily withdrawal limit (verified accounts)
                'min_withdrawal': 10,  # $10 minimum withdrawal
                'max_withdrawal_per_transaction': 10000,  # $10,000 per transaction
                'withdrawal_fee_usdt': 1.0,  # $1 USDT withdrawal fee
                'withdrawal_fee_btc': 0.0005,  # 0.0005 BTC withdrawal fee
                'withdrawal_fee_eth': 0.01,  # 0.01 ETH withdrawal fee
            },
            'rate_limits': {
                'withdrawal_requests_per_hour': 5,  # 5 withdrawal requests per hour
                'withdrawal_requests_per_day': 20,  # 20 withdrawal requests per day
                'api_requests_per_minute': 1200,  # 1200 API requests per minute
                'api_requests_per_second': 10,  # 10 API requests per second
                'order_requests_per_second': 10,  # 10 order requests per second
            },
            'security_restrictions': {
                'withdrawal_whitelist_required': True,  # Withdrawal addresses must be whitelisted
                'withdrawal_confirmation_required': True,  # Email/SMS confirmation required
                'withdrawal_cooldown_minutes': 5,  # 5-minute cooldown between withdrawals
                'suspicious_activity_lockout': True,  # Account lockout for suspicious activity
                'ip_restrictions': True,  # IP address restrictions
            },
            'crypto_specific_limits': {
                'TON': {'min_withdrawal': 1, 'fee': 0.1, 'network_fee': 0.05},
                'ALGO': {'min_withdrawal': 1, 'fee': 0.1, 'network_fee': 0.001},
                'VET': {'min_withdrawal': 100, 'fee': 0.1, 'network_fee': 0.01},
                'XLM': {'min_withdrawal': 1, 'fee': 0.1, 'network_fee': 0.00001},
                'TRX': {'min_withdrawal': 1, 'fee': 0.1, 'network_fee': 0.1},
                'FTM': {'min_withdrawal': 1, 'fee': 0.1, 'network_fee': 0.01},
                'MATIC': {'min_withdrawal': 1, 'fee': 0.1, 'network_fee': 0.01},
                'SOL': {'min_withdrawal': 0.1, 'fee': 0.1, 'network_fee': 0.00025},
                'BCH': {'min_withdrawal': 0.001, 'fee': 0.1, 'network_fee': 0.0001},
                'XRP': {'min_withdrawal': 1, 'fee': 0.1, 'network_fee': 0.00001},
                'DASH': {'min_withdrawal': 0.01, 'fee': 0.1, 'network_fee': 0.001},
                'LTC': {'min_withdrawal': 0.001, 'fee': 0.1, 'network_fee': 0.001},
                'HBAR': {'min_withdrawal': 1, 'fee': 0.1, 'network_fee': 0.01},
                'ICP': {'min_withdrawal': 1, 'fee': 0.1, 'network_fee': 0.01},
                'LINK': {'min_withdrawal': 0.1, 'fee': 0.1, 'network_fee': 0.01},
                'ATOM': {'min_withdrawal': 0.1, 'fee': 0.1, 'network_fee': 0.01},
            }
        }
        
        self.okx_limitations = {
            'withdrawal_limits': {
                'daily_limit_usdt': 50000,  # $50,000 daily withdrawal limit (unverified)
                'daily_limit_verified': 1000000,  # $1M daily withdrawal limit (verified)
                'min_withdrawal': 5,  # $5 minimum withdrawal
                'max_withdrawal_per_transaction': 5000,  # $5,000 per transaction
                'withdrawal_fee_usdt': 0.8,  # $0.8 USDT withdrawal fee
                'withdrawal_fee_btc': 0.0003,  # 0.0003 BTC withdrawal fee
                'withdrawal_fee_eth': 0.005,  # 0.005 ETH withdrawal fee
            },
            'rate_limits': {
                'withdrawal_requests_per_hour': 10,  # 10 withdrawal requests per hour
                'withdrawal_requests_per_day': 50,  # 50 withdrawal requests per day
                'api_requests_per_minute': 3000,  # 3000 API requests per minute
                'api_requests_per_second': 20,  # 20 API requests per second
                'order_requests_per_second': 20,  # 20 order requests per second
            },
            'security_restrictions': {
                'withdrawal_whitelist_required': True,  # Withdrawal addresses must be whitelisted
                'withdrawal_confirmation_required': True,  # Email/SMS confirmation required
                'withdrawal_cooldown_minutes': 3,  # 3-minute cooldown between withdrawals
                'suspicious_activity_lockout': True,  # Account lockout for suspicious activity
                'ip_restrictions': True,  # IP address restrictions
            },
            'crypto_specific_limits': {
                'TON': {'min_withdrawal': 1, 'fee': 0.08, 'network_fee': 0.05},
                'ALGO': {'min_withdrawal': 1, 'fee': 0.08, 'network_fee': 0.001},
                'VET': {'min_withdrawal': 100, 'fee': 0.08, 'network_fee': 0.01},
                'XLM': {'min_withdrawal': 1, 'fee': 0.08, 'network_fee': 0.00001},
                'TRX': {'min_withdrawal': 1, 'fee': 0.08, 'network_fee': 0.1},
                'FTM': {'min_withdrawal': 1, 'fee': 0.08, 'network_fee': 0.01},
                'MATIC': {'min_withdrawal': 1, 'fee': 0.08, 'network_fee': 0.01},
                'SOL': {'min_withdrawal': 0.1, 'fee': 0.08, 'network_fee': 0.00025},
                'BCH': {'min_withdrawal': 0.001, 'fee': 0.08, 'network_fee': 0.0001},
                'XRP': {'min_withdrawal': 1, 'fee': 0.08, 'network_fee': 0.00001},
                'DASH': {'min_withdrawal': 0.01, 'fee': 0.08, 'network_fee': 0.001},
                'LTC': {'min_withdrawal': 0.001, 'fee': 0.08, 'network_fee': 0.001},
                'HBAR': {'min_withdrawal': 1, 'fee': 0.08, 'network_fee': 0.01},
                'ICP': {'min_withdrawal': 1, 'fee': 0.08, 'network_fee': 0.01},
                'LINK': {'min_withdrawal': 0.1, 'fee': 0.08, 'network_fee': 0.01},
                'ATOM': {'min_withdrawal': 0.1, 'fee': 0.08, 'network_fee': 0.01},
            }
        }
        
        # Network transfer times and limitations
        self.network_limitations = {
            'TON': {'transfer_time_seconds': 30, 'network_fee': 0.05, 'min_transfer': 1},
            'ALGO': {'transfer_time_seconds': 4, 'network_fee': 0.001, 'min_transfer': 1},
            'VET': {'transfer_time_seconds': 10, 'network_fee': 0.01, 'min_transfer': 100},
            'XLM': {'transfer_time_seconds': 3, 'network_fee': 0.00001, 'min_transfer': 1},
            'TRX': {'transfer_time_seconds': 120, 'network_fee': 0.1, 'min_transfer': 1},
            'FTM': {'transfer_time_seconds': 60, 'network_fee': 0.01, 'min_transfer': 1},
            'MATIC': {'transfer_time_seconds': 90, 'network_fee': 0.01, 'min_transfer': 1},
            'SOL': {'transfer_time_seconds': 10, 'network_fee': 0.00025, 'min_transfer': 0.1},
            'BCH': {'transfer_time_seconds': 300, 'network_fee': 0.0001, 'min_transfer': 0.001},
            'XRP': {'transfer_time_seconds': 5, 'network_fee': 0.00001, 'min_transfer': 1},
            'DASH': {'transfer_time_seconds': 150, 'network_fee': 0.001, 'min_transfer': 0.01},
            'LTC': {'transfer_time_seconds': 150, 'network_fee': 0.001, 'min_transfer': 0.001},
            'HBAR': {'transfer_time_seconds': 30, 'network_fee': 0.01, 'min_transfer': 1},
            'ICP': {'transfer_time_seconds': 90, 'network_fee': 0.01, 'min_transfer': 1},
            'LINK': {'transfer_time_seconds': 10, 'network_fee': 0.01, 'min_transfer': 0.1},
            'ATOM': {'transfer_time_seconds': 7, 'network_fee': 0.01, 'min_transfer': 0.1},
        }
    
    def analyze_transfer_limitations(self) -> Dict[str, Any]:
        """Analyze transfer limitations and potential issues"""
        
        issues = []
        recommendations = []
        
        # 1. Rate Limit Analysis
        print("\n🔍 RATE LIMIT ANALYSIS:")
        print("-" * 60)
        
        # Binance rate limits
        binance_withdrawal_limit = self.binance_limitations['rate_limits']['withdrawal_requests_per_hour']
        okx_withdrawal_limit = self.okx_limitations['rate_limits']['withdrawal_requests_per_hour']
        
        print(f"Binance: {binance_withdrawal_limit} withdrawals per hour")
        print(f"OKX: {okx_withdrawal_limit} withdrawals per hour")
        
        # Calculate maximum transfers per 5-minute window
        max_transfers_5min_binance = (binance_withdrawal_limit / 60) * 5  # 0.42 transfers per 5 minutes
        max_transfers_5min_okx = (okx_withdrawal_limit / 60) * 5  # 0.83 transfers per 5 minutes
        
        print(f"\nMaximum transfers per 5 minutes:")
        print(f"Binance: {max_transfers_5min_binance:.2f} (very limited)")
        print(f"OKX: {max_transfers_5min_okx:.2f} (limited)")
        
        if max_transfers_5min_binance < 1:
            issues.append("CRITICAL: Binance allows less than 1 transfer per 5 minutes")
            recommendations.append("Use OKX as primary withdrawal exchange")
        
        # 2. Daily Transfer Limits
        print(f"\n💰 DAILY TRANSFER LIMITS:")
        print("-" * 60)
        
        binance_daily = self.binance_limitations['withdrawal_limits']['daily_limit_usdt']
        okx_daily = self.okx_limitations['withdrawal_limits']['daily_limit_usdt']
        
        print(f"Binance: ${binance_daily:,} daily limit (unverified)")
        print(f"OKX: ${okx_daily:,} daily limit (unverified)")
        
        if binance_daily < 100000:
            issues.append("WARNING: Binance daily limit may restrict large arbitrage operations")
            recommendations.append("Consider account verification for higher limits")
        
        # 3. Security Restrictions
        print(f"\n🔒 SECURITY RESTRICTIONS:")
        print("-" * 60)
        
        print("Both exchanges require:")
        print("• Withdrawal address whitelisting")
        print("• Email/SMS confirmation for each withdrawal")
        print("• IP address restrictions")
        print("• Suspicious activity monitoring")
        
        issues.append("CRITICAL: Manual confirmation required for each withdrawal")
        recommendations.append("Implement automated confirmation system or use API-based transfers")
        
        # 4. Transfer Fees Analysis
        print(f"\n💸 TRANSFER FEES ANALYSIS:")
        print("-" * 60)
        
        total_fees = {}
        for crypto in self.binance_limitations['crypto_specific_limits'].keys():
            binance_fee = self.binance_limitations['crypto_specific_limits'][crypto]['fee']
            okx_fee = self.okx_limitations['crypto_specific_limits'][crypto]['fee']
            network_fee = self.network_limitations[crypto]['network_fee']
            
            total_fee = binance_fee + okx_fee + network_fee
            total_fees[crypto] = total_fee
            
            print(f"{crypto}: ${total_fee:.3f} total fees per transfer")
        
        # 5. Minimum Transfer Amounts
        print(f"\n📏 MINIMUM TRANSFER AMOUNTS:")
        print("-" * 60)
        
        for crypto, limits in self.binance_limitations['crypto_specific_limits'].items():
            min_amount = limits['min_withdrawal']
            print(f"{crypto}: {min_amount} minimum")
            
            if min_amount > 10:
                issues.append(f"WARNING: {crypto} has high minimum transfer amount ({min_amount})")
        
        # 6. Transfer Time Analysis
        print(f"\n⏱️  TRANSFER TIME ANALYSIS:")
        print("-" * 60)
        
        fast_assets = []
        slow_assets = []
        
        for crypto, times in self.network_limitations.items():
            transfer_time = times['transfer_time_seconds']
            print(f"{crypto}: {transfer_time} seconds")
            
            if transfer_time <= 10:
                fast_assets.append(crypto)
            elif transfer_time > 60:
                slow_assets.append(crypto)
        
        print(f"\nFast assets (≤10s): {', '.join(fast_assets)}")
        print(f"Slow assets (>60s): {', '.join(slow_assets)}")
        
        # 7. Critical Issues Summary
        print(f"\n🚨 CRITICAL ISSUES IDENTIFIED:")
        print("-" * 60)
        
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        
        # 8. Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 60)
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        # 9. Optimal Strategy
        print(f"\n🎯 OPTIMAL TRANSFER STRATEGY:")
        print("-" * 60)
        
        print("1. Focus on fast-transfer assets (ALGO, XLM, SOL, ATOM)")
        print("2. Use OKX as primary withdrawal exchange (higher rate limits)")
        print("3. Batch transfers to minimize rate limit impact")
        print("4. Implement transfer scheduling to avoid conflicts")
        print("5. Use API-based transfers where possible")
        print("6. Monitor account limits and verification status")
        
        return {
            'issues': issues,
            'recommendations': recommendations,
            'max_transfers_5min_binance': max_transfers_5min_binance,
            'max_transfers_5min_okx': max_transfers_5min_okx,
            'total_fees': total_fees,
            'fast_assets': fast_assets,
            'slow_assets': slow_assets
        }
    
    def calculate_realistic_transfer_frequency(self) -> Dict[str, Any]:
        """Calculate realistic transfer frequency based on limitations"""
        
        # Based on rate limits, calculate maximum possible transfers
        binance_max_per_hour = self.binance_limitations['rate_limits']['withdrawal_requests_per_hour']
        okx_max_per_hour = self.okx_limitations['rate_limits']['withdrawal_requests_per_hour']
        
        # Conservative estimate (50% of max to avoid issues)
        binance_conservative = binance_max_per_hour * 0.5
        okx_conservative = okx_max_per_hour * 0.5
        
        # Per 5-minute windows
        binance_per_5min = (binance_conservative / 60) * 5
        okx_per_5min = (okx_conservative / 60) * 5
        
        return {
            'binance_max_per_hour': binance_max_per_hour,
            'okx_max_per_hour': okx_max_per_hour,
            'binance_conservative_per_hour': binance_conservative,
            'okx_conservative_per_hour': okx_conservative,
            'binance_per_5min': binance_per_5min,
            'okx_per_5min': okx_per_5min,
            'realistic_transfers_per_5min': min(binance_per_5min, okx_per_5min)
        }

def run_transfer_limitations_analysis():
    """Run transfer limitations analysis"""
    print('=' * 80)
    print('TRANSFER LIMITATIONS ANALYSIS')
    print('=' * 80)
    
    analysis = TransferLimitationsAnalysis()
    
    print('Analyzing transfer limitations between Binance and OKX...')
    print('Identifying potential issues with frequent transfers...')
    
    # Run analysis
    results = analysis.analyze_transfer_limitations()
    
    # Calculate realistic transfer frequency
    transfer_freq = analysis.calculate_realistic_transfer_frequency()
    
    print(f"\n📊 REALISTIC TRANSFER FREQUENCY:")
    print("-" * 60)
    print(f"Maximum transfers per 5 minutes: {transfer_freq['realistic_transfers_per_5min']:.2f}")
    print(f"Maximum transfers per hour: {transfer_freq['binance_conservative_per_hour']:.1f} (Binance) / {transfer_freq['okx_conservative_per_hour']:.1f} (OKX)")
    
    # Save results
    import json
    with open('transfer_limitations_results.json', 'w') as f:
        json.dump({
            'analysis_results': results,
            'transfer_frequency': transfer_freq,
            'timestamp': time.time()
        }, f, indent=2, default=str)
    
    print(f'\n📄 Detailed results saved to: transfer_limitations_results.json')
    
    return results

if __name__ == "__main__":
    # Run transfer limitations analysis
    run_transfer_limitations_analysis()
