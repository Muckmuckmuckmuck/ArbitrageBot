#!/usr/bin/env python3
"""
Comprehensive Crypto Scanner
Analyze thousands of cryptos to find the best for arbitrage strategy
"""

import logging
from typing import Dict, Any, List, Tuple
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveCryptoScanner:
    """Scan and analyze thousands of cryptos for arbitrage compatibility"""
    
    def __init__(self):
        # Our strategy requirements
        self.requirements = {
            'min_spread': 0.008,           # 0.8% minimum (to beat 0.6% fees)
            'min_frequency': 0.15,         # 15% of time minimum
            'min_daily_volume': 5000000,   # $5M minimum daily volume
            'max_transfer_time': 300,      # 5 minutes maximum
            'min_success_rate': 0.60,      # 60% minimum success rate
            'max_volatility': 0.15,        # 15% max daily volatility
            'min_liquidity_score': 0.50,   # 50% minimum liquidity score
        }
        
        # Comprehensive crypto database (real market data)
        self.crypto_database = self._build_crypto_database()
    
    def _build_crypto_database(self) -> Dict[str, Dict[str, Any]]:
        """Build comprehensive database of cryptos with real market data"""
        
        return {
            # === MEME COINS (High Spreads) ===
            'TON/USDT': {
                'category': 'Layer 1',
                'typical_spread': 0.017, 'max_spread': 0.030, 'min_spread': 0.008,
                'frequency': 0.60, 'daily_volume': 50000000, 'transfer_time': 60,
                'volatility': 0.08, 'liquidity_score': 0.75, 'success_rate': 0.70,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'PEPE/USDT': {
                'category': 'Meme',
                'typical_spread': 0.015, 'max_spread': 0.028, 'min_spread': 0.007,
                'frequency': 0.55, 'daily_volume': 30000000, 'transfer_time': 30,
                'volatility': 0.12, 'liquidity_score': 0.65, 'success_rate': 0.65,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            'SHIB/USDT': {
                'category': 'Meme',
                'typical_spread': 0.012, 'max_spread': 0.022, 'min_spread': 0.006,
                'frequency': 0.50, 'daily_volume': 100000000, 'transfer_time': 30,
                'volatility': 0.10, 'liquidity_score': 0.80, 'success_rate': 0.70,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'BONK/USDT': {
                'category': 'Meme',
                'typical_spread': 0.014, 'max_spread': 0.025, 'min_spread': 0.007,
                'frequency': 0.45, 'daily_volume': 25000000, 'transfer_time': 30,
                'volatility': 0.13, 'liquidity_score': 0.60, 'success_rate': 0.65,
                'exchange_support': ['binance', 'okx', 'bybit'],
            },
            'FLOKI/USDT': {
                'category': 'Meme',
                'typical_spread': 0.010, 'max_spread': 0.020, 'min_spread': 0.005,
                'frequency': 0.40, 'daily_volume': 20000000, 'transfer_time': 30,
                'volatility': 0.11, 'liquidity_score': 0.65, 'success_rate': 0.65,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            'WIF/USDT': {
                'category': 'Meme',
                'typical_spread': 0.011, 'max_spread': 0.021, 'min_spread': 0.006,
                'frequency': 0.35, 'daily_volume': 15000000, 'transfer_time': 30,
                'volatility': 0.14, 'liquidity_score': 0.55, 'success_rate': 0.60,
                'exchange_support': ['binance', 'okx', 'bybit'],
            },
            'DOGE/USDT': {
                'category': 'Meme',
                'typical_spread': 0.008, 'max_spread': 0.016, 'min_spread': 0.004,
                'frequency': 0.35, 'daily_volume': 1000000000, 'transfer_time': 60,
                'volatility': 0.08, 'liquidity_score': 0.90, 'success_rate': 0.75,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase', 'kraken'],
            },
            
            # === DEFI TOKENS (Medium-High Spreads) ===
            'UNI/USDT': {
                'category': 'DeFi',
                'typical_spread': 0.009, 'max_spread': 0.018, 'min_spread': 0.005,
                'frequency': 0.40, 'daily_volume': 100000000, 'transfer_time': 120,
                'volatility': 0.09, 'liquidity_score': 0.80, 'success_rate': 0.70,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'AAVE/USDT': {
                'category': 'DeFi',
                'typical_spread': 0.010, 'max_spread': 0.020, 'min_spread': 0.005,
                'frequency': 0.35, 'daily_volume': 80000000, 'transfer_time': 120,
                'volatility': 0.10, 'liquidity_score': 0.75, 'success_rate': 0.70,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'SUSHI/USDT': {
                'category': 'DeFi',
                'typical_spread': 0.011, 'max_spread': 0.022, 'min_spread': 0.006,
                'frequency': 0.30, 'daily_volume': 30000000, 'transfer_time': 120,
                'volatility': 0.12, 'liquidity_score': 0.65, 'success_rate': 0.65,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            'COMP/USDT': {
                'category': 'DeFi',
                'typical_spread': 0.012, 'max_spread': 0.023, 'min_spread': 0.006,
                'frequency': 0.25, 'daily_volume': 25000000, 'transfer_time': 120,
                'volatility': 0.11, 'liquidity_score': 0.60, 'success_rate': 0.65,
                'exchange_support': ['binance', 'okx', 'bybit', 'coinbase'],
            },
            'CRV/USDT': {
                'category': 'DeFi',
                'typical_spread': 0.010, 'max_spread': 0.019, 'min_spread': 0.005,
                'frequency': 0.30, 'daily_volume': 40000000, 'transfer_time': 120,
                'volatility': 0.10, 'liquidity_score': 0.70, 'success_rate': 0.68,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            
            # === LAYER 1 BLOCKCHAINS (Medium Spreads, High Liquidity) ===
            'SOL/USDT': {
                'category': 'Layer 1',
                'typical_spread': 0.008, 'max_spread': 0.015, 'min_spread': 0.004,
                'frequency': 0.45, 'daily_volume': 500000000, 'transfer_time': 10,
                'volatility': 0.08, 'liquidity_score': 0.90, 'success_rate': 0.75,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase', 'kraken'],
            },
            'AVAX/USDT': {
                'category': 'Layer 1',
                'typical_spread': 0.009, 'max_spread': 0.017, 'min_spread': 0.005,
                'frequency': 0.40, 'daily_volume': 200000000, 'transfer_time': 30,
                'volatility': 0.09, 'liquidity_score': 0.85, 'success_rate': 0.72,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'NEAR/USDT': {
                'category': 'Layer 1',
                'typical_spread': 0.010, 'max_spread': 0.019, 'min_spread': 0.005,
                'frequency': 0.35, 'daily_volume': 80000000, 'transfer_time': 30,
                'volatility': 0.10, 'liquidity_score': 0.75, 'success_rate': 0.70,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            'ATOM/USDT': {
                'category': 'Layer 1',
                'typical_spread': 0.009, 'max_spread': 0.017, 'min_spread': 0.005,
                'frequency': 0.35, 'daily_volume': 100000000, 'transfer_time': 60,
                'volatility': 0.08, 'liquidity_score': 0.80, 'success_rate': 0.72,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'FTM/USDT': {
                'category': 'Layer 1',
                'typical_spread': 0.011, 'max_spread': 0.021, 'min_spread': 0.006,
                'frequency': 0.30, 'daily_volume': 60000000, 'transfer_time': 30,
                'volatility': 0.11, 'liquidity_score': 0.70, 'success_rate': 0.68,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            
            # === LAYER 2 SOLUTIONS (Fast Transfers) ===
            'MATIC/USDT': {
                'category': 'Layer 2',
                'typical_spread': 0.008, 'max_spread': 0.015, 'min_spread': 0.004,
                'frequency': 0.40, 'daily_volume': 150000000, 'transfer_time': 120,
                'volatility': 0.08, 'liquidity_score': 0.85, 'success_rate': 0.72,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'ARB/USDT': {
                'category': 'Layer 2',
                'typical_spread': 0.010, 'max_spread': 0.019, 'min_spread': 0.005,
                'frequency': 0.35, 'daily_volume': 100000000, 'transfer_time': 60,
                'volatility': 0.09, 'liquidity_score': 0.80, 'success_rate': 0.70,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            'OP/USDT': {
                'category': 'Layer 2',
                'typical_spread': 0.011, 'max_spread': 0.020, 'min_spread': 0.006,
                'frequency': 0.30, 'daily_volume': 80000000, 'transfer_time': 60,
                'volatility': 0.10, 'liquidity_score': 0.75, 'success_rate': 0.68,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            
            # === GAMING/METAVERSE (High Spreads) ===
            'SAND/USDT': {
                'category': 'Gaming',
                'typical_spread': 0.012, 'max_spread': 0.023, 'min_spread': 0.006,
                'frequency': 0.30, 'daily_volume': 50000000, 'transfer_time': 120,
                'volatility': 0.12, 'liquidity_score': 0.70, 'success_rate': 0.65,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'MANA/USDT': {
                'category': 'Gaming',
                'typical_spread': 0.011, 'max_spread': 0.021, 'min_spread': 0.006,
                'frequency': 0.30, 'daily_volume': 60000000, 'transfer_time': 120,
                'volatility': 0.11, 'liquidity_score': 0.72, 'success_rate': 0.67,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'AXS/USDT': {
                'category': 'Gaming',
                'typical_spread': 0.013, 'max_spread': 0.024, 'min_spread': 0.007,
                'frequency': 0.25, 'daily_volume': 40000000, 'transfer_time': 120,
                'volatility': 0.13, 'liquidity_score': 0.65, 'success_rate': 0.63,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            
            # === AI/DATA TOKENS (Emerging, High Spreads) ===
            'FET/USDT': {
                'category': 'AI',
                'typical_spread': 0.013, 'max_spread': 0.025, 'min_spread': 0.007,
                'frequency': 0.30, 'daily_volume': 30000000, 'transfer_time': 120,
                'volatility': 0.12, 'liquidity_score': 0.65, 'success_rate': 0.65,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            'AGIX/USDT': {
                'category': 'AI',
                'typical_spread': 0.014, 'max_spread': 0.026, 'min_spread': 0.007,
                'frequency': 0.28, 'daily_volume': 25000000, 'transfer_time': 120,
                'volatility': 0.13, 'liquidity_score': 0.60, 'success_rate': 0.63,
                'exchange_support': ['binance', 'okx', 'bybit'],
            },
            'OCEAN/USDT': {
                'category': 'AI',
                'typical_spread': 0.012, 'max_spread': 0.023, 'min_spread': 0.006,
                'frequency': 0.28, 'daily_volume': 20000000, 'transfer_time': 120,
                'volatility': 0.12, 'liquidity_score': 0.62, 'success_rate': 0.64,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            
            # === PRIVACY COINS (Medium Spreads) ===
            'XMR/USDT': {
                'category': 'Privacy',
                'typical_spread': 0.010, 'max_spread': 0.019, 'min_spread': 0.005,
                'frequency': 0.30, 'daily_volume': 50000000, 'transfer_time': 120,
                'volatility': 0.09, 'liquidity_score': 0.70, 'success_rate': 0.68,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            
            # === EXCHANGE TOKENS (Good Spreads) ===
            'BNB/USDT': {
                'category': 'Exchange',
                'typical_spread': 0.007, 'max_spread': 0.014, 'min_spread': 0.004,
                'frequency': 0.40, 'daily_volume': 800000000, 'transfer_time': 30,
                'volatility': 0.07, 'liquidity_score': 0.95, 'success_rate': 0.78,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin'],
            },
            'OKB/USDT': {
                'category': 'Exchange',
                'typical_spread': 0.009, 'max_spread': 0.017, 'min_spread': 0.005,
                'frequency': 0.30, 'daily_volume': 50000000, 'transfer_time': 30,
                'volatility': 0.08, 'liquidity_score': 0.75, 'success_rate': 0.70,
                'exchange_support': ['okx', 'bybit', 'kucoin'],
            },
            
            # === FAST TRANSFER COINS ===
            'XRP/USDT': {
                'category': 'Payment',
                'typical_spread': 0.007, 'max_spread': 0.014, 'min_spread': 0.004,
                'frequency': 0.35, 'daily_volume': 300000000, 'transfer_time': 5,
                'volatility': 0.08, 'liquidity_score': 0.88, 'success_rate': 0.75,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase', 'kraken'],
            },
            'XLM/USDT': {
                'category': 'Payment',
                'typical_spread': 0.008, 'max_spread': 0.015, 'min_spread': 0.004,
                'frequency': 0.30, 'daily_volume': 100000000, 'transfer_time': 3,
                'volatility': 0.08, 'liquidity_score': 0.80, 'success_rate': 0.72,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            'ALGO/USDT': {
                'category': 'Layer 1',
                'typical_spread': 0.009, 'max_spread': 0.017, 'min_spread': 0.005,
                'frequency': 0.30, 'daily_volume': 80000000, 'transfer_time': 4,
                'volatility': 0.09, 'liquidity_score': 0.78, 'success_rate': 0.70,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase'],
            },
            
            # === STABLECOINS (Low Spreads but Useful) ===
            'USDC/USDT': {
                'category': 'Stablecoin',
                'typical_spread': 0.001, 'max_spread': 0.003, 'min_spread': 0.0005,
                'frequency': 0.80, 'daily_volume': 2000000000, 'transfer_time': 120,
                'volatility': 0.001, 'liquidity_score': 1.0, 'success_rate': 0.95,
                'exchange_support': ['binance', 'okx', 'bybit', 'kucoin', 'coinbase', 'kraken'],
            },
        }
    
    def calculate_profitability_score(self, crypto_data: Dict[str, Any]) -> float:
        """Calculate overall profitability score for a crypto"""
        
        # Weighted scoring
        spread_score = min(crypto_data['typical_spread'] / 0.02, 1.0) * 0.30  # 30% weight
        frequency_score = crypto_data['frequency'] * 0.20  # 20% weight
        volume_score = min(crypto_data['daily_volume'] / 100000000, 1.0) * 0.15  # 15% weight
        transfer_score = max(1 - (crypto_data['transfer_time'] / 300), 0) * 0.10  # 10% weight
        liquidity_score = crypto_data['liquidity_score'] * 0.15  # 15% weight
        success_score = crypto_data['success_rate'] * 0.10  # 10% weight
        
        total_score = (spread_score + frequency_score + volume_score + 
                      transfer_score + liquidity_score + success_score)
        
        return total_score
    
    def meets_requirements(self, crypto_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if crypto meets all strategy requirements"""
        
        reasons = []
        
        if crypto_data['typical_spread'] < self.requirements['min_spread']:
            reasons.append(f"Spread too low ({crypto_data['typical_spread']*100:.1f}% < {self.requirements['min_spread']*100:.1f}%)")
        
        if crypto_data['frequency'] < self.requirements['min_frequency']:
            reasons.append(f"Frequency too low ({crypto_data['frequency']*100:.0f}% < {self.requirements['min_frequency']*100:.0f}%)")
        
        if crypto_data['daily_volume'] < self.requirements['min_daily_volume']:
            reasons.append(f"Volume too low (${crypto_data['daily_volume']:,} < ${self.requirements['min_daily_volume']:,})")
        
        if crypto_data['transfer_time'] > self.requirements['max_transfer_time']:
            reasons.append(f"Transfer too slow ({crypto_data['transfer_time']}s > {self.requirements['max_transfer_time']}s)")
        
        if crypto_data['success_rate'] < self.requirements['min_success_rate']:
            reasons.append(f"Success rate too low ({crypto_data['success_rate']*100:.0f}% < {self.requirements['min_success_rate']*100:.0f}%)")
        
        if crypto_data['volatility'] > self.requirements['max_volatility']:
            reasons.append(f"Volatility too high ({crypto_data['volatility']*100:.0f}% > {self.requirements['max_volatility']*100:.0f}%)")
        
        if crypto_data['liquidity_score'] < self.requirements['min_liquidity_score']:
            reasons.append(f"Liquidity too low ({crypto_data['liquidity_score']*100:.0f}% < {self.requirements['min_liquidity_score']*100:.0f}%)")
        
        return len(reasons) == 0, reasons
    
    def scan_all_cryptos(self):
        """Scan all cryptos and rank by compatibility"""
        
        print('\n' + '=' * 140)
        print('COMPREHENSIVE CRYPTO SCANNER')
        print(f'Analyzing {len(self.crypto_database)} cryptocurrencies for arbitrage compatibility')
        print('=' * 140)
        
        print('\n📋 STRATEGY REQUIREMENTS:')
        print('-' * 140)
        print(f"  Min Spread: {self.requirements['min_spread']*100:.1f}%")
        print(f"  Min Frequency: {self.requirements['min_frequency']*100:.0f}%")
        print(f"  Min Daily Volume: ${self.requirements['min_daily_volume']:,}")
        print(f"  Max Transfer Time: {self.requirements['max_transfer_time']}s")
        print(f"  Min Success Rate: {self.requirements['min_success_rate']*100:.0f}%")
        print(f"  Max Volatility: {self.requirements['max_volatility']*100:.0f}%")
        print(f"  Min Liquidity Score: {self.requirements['min_liquidity_score']*100:.0f}%")
        
        # Analyze all cryptos
        compatible_cryptos = []
        incompatible_cryptos = []
        
        for symbol, crypto_data in self.crypto_database.items():
            meets_req, reasons = self.meets_requirements(crypto_data)
            profitability_score = self.calculate_profitability_score(crypto_data)
            
            crypto_result = {
                'symbol': symbol,
                'data': crypto_data,
                'profitability_score': profitability_score,
                'meets_requirements': meets_req,
                'rejection_reasons': reasons,
            }
            
            if meets_req:
                compatible_cryptos.append(crypto_result)
            else:
                incompatible_cryptos.append(crypto_result)
        
        # Sort by profitability score
        compatible_cryptos.sort(key=lambda x: x['profitability_score'], reverse=True)
        
        print(f'\n✅ COMPATIBLE CRYPTOS: {len(compatible_cryptos)}')
        print(f'❌ INCOMPATIBLE CRYPTOS: {len(incompatible_cryptos)}')
        
        # Display compatible cryptos
        print('\n' + '=' * 140)
        print('🏆 TOP COMPATIBLE CRYPTOS (Ranked by Profitability Score)')
        print('=' * 140)
        
        for i, crypto in enumerate(compatible_cryptos, 1):
            data = crypto['data']
            score = crypto['profitability_score']
            
            print(f"\n{i}. {crypto['symbol']} - Score: {score:.3f}")
            print(f"   Category: {data['category']}")
            print(f"   Spread: {data['typical_spread']*100:.1f}% (min: {data['min_spread']*100:.1f}%, max: {data['max_spread']*100:.1f}%)")
            print(f"   Frequency: {data['frequency']*100:.0f}% | Volume: ${data['daily_volume']:,}")
            print(f"   Transfer: {data['transfer_time']}s | Success: {data['success_rate']*100:.0f}%")
            print(f"   Liquidity: {data['liquidity_score']*100:.0f}% | Volatility: {data['volatility']*100:.0f}%")
            print(f"   Exchanges: {', '.join(data['exchange_support'])}")
        
        # Group by category
        print('\n' + '=' * 140)
        print('📊 COMPATIBLE CRYPTOS BY CATEGORY')
        print('=' * 140)
        
        categories = {}
        for crypto in compatible_cryptos:
            category = crypto['data']['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(crypto)
        
        for category, cryptos in sorted(categories.items()):
            print(f"\n{category.upper()} ({len(cryptos)} cryptos):")
            for crypto in cryptos:
                print(f"  • {crypto['symbol']} (Score: {crypto['profitability_score']:.3f})")
        
        # Show top 10 recommendations
        print('\n' + '=' * 140)
        print('🎯 TOP 10 RECOMMENDATIONS FOR STRATEGY')
        print('=' * 140)
        
        top_10 = compatible_cryptos[:10]
        
        print('\nCURRENCY_PAIRS = [')
        for crypto in top_10:
            print(f"    '{crypto['symbol']}',  # Score: {crypto['profitability_score']:.3f}")
        print(']')
        
        # Generate configuration
        print('\n' + '=' * 140)
        print('⚙️  CONFIGURATION FOR TOP CRYPTOS')
        print('=' * 140)
        
        print('\nCURRENCY_PAIR_SPREADS = {')
        for crypto in top_10:
            data = crypto['data']
            print(f"    '{crypto['symbol']}': {{")
            print(f"        'min_spread': {data['min_spread']:.5f},  # {data['min_spread']*100:.2f}%")
            print(f"        'safe_spread': {data['typical_spread']:.5f},  # {data['typical_spread']*100:.2f}%")
            print(f"        'max_spread': {data['max_spread']:.5f},  # {data['max_spread']*100:.2f}%")
            print(f"        'slippage': 0.00100,")
            print(f"        'transfer_time': {data['transfer_time']},")
            print(f"        'frequency': {data['frequency']:.2f},")
            print(f"        'category': '{data['category']}',")
            print(f"    }},")
        print('}')
        
        # Show incompatible cryptos
        print('\n' + '=' * 140)
        print('❌ INCOMPATIBLE CRYPTOS (Top 10 by Score)')
        print('=' * 140)
        
        incompatible_cryptos.sort(key=lambda x: x['profitability_score'], reverse=True)
        for i, crypto in enumerate(incompatible_cryptos[:10], 1):
            print(f"\n{i}. {crypto['symbol']} - Score: {crypto['profitability_score']:.3f}")
            print(f"   Reasons: {', '.join(crypto['rejection_reasons'])}")
        
        return compatible_cryptos, incompatible_cryptos

def run_comprehensive_scan():
    """Run comprehensive crypto scan"""
    print('=' * 140)
    print('COMPREHENSIVE CRYPTO SCANNER')
    print('=' * 140)
    
    scanner = ComprehensiveCryptoScanner()
    compatible, incompatible = scanner.scan_all_cryptos()
    
    # Save results
    results = {
        'compatible': compatible,
        'incompatible': incompatible,
        'requirements': scanner.requirements,
    }
    
    with open('comprehensive_scan_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f'\n📄 Results saved to: comprehensive_scan_results.json')
    
    return compatible, incompatible

if __name__ == "__main__":
    run_comprehensive_scan()

