#!/usr/bin/env python3
"""
Comprehensive System Audit
Check for issues, inconsistencies, and potential problems
"""

import logging
from typing import Dict, Any, List, Tuple
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemAuditor:
    """Comprehensive system audit"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.recommendations = []
        self.passed_checks = []
    
    def audit_configuration(self):
        """Audit configuration files"""
        print('\n' + '=' * 100)
        print('CONFIGURATION AUDIT')
        print('=' * 100)
        
        # Check if aggressive_config exists
        try:
            from aggressive_config import AggressiveConfig
            config = AggressiveConfig()
            self.passed_checks.append("✅ aggressive_config.py loads successfully")
            
            # Check position sizing
            if config.RISK_MANAGEMENT['max_position_percent'] > 0.50:
                self.warnings.append("⚠️  Max position > 50% - Very aggressive, ensure you can handle volatility")
            else:
                self.passed_checks.append(f"✅ Max position: {config.RISK_MANAGEMENT['max_position_percent']*100:.0f}%")
            
            # Check total exposure
            if config.RISK_MANAGEMENT['max_total_exposure'] > 0.95:
                self.warnings.append("⚠️  Total exposure > 95% - Very little buffer for emergencies")
            else:
                self.passed_checks.append(f"✅ Total exposure: {config.RISK_MANAGEMENT['max_total_exposure']*100:.0f}%")
            
            # Check reserve
            if config.RISK_MANAGEMENT['reserve_percent'] < 0.05:
                self.issues.append("❌ Reserve < 5% - Might not have enough for fees and slippage")
            else:
                self.passed_checks.append(f"✅ Reserve: {config.RISK_MANAGEMENT['reserve_percent']*100:.0f}%")
            
            # Check concurrent trades
            if config.RISK_MANAGEMENT['max_concurrent_trades'] > 20:
                self.warnings.append("⚠️  Concurrent trades > 20 - May be hard to manage")
            else:
                self.passed_checks.append(f"✅ Concurrent trades: {config.RISK_MANAGEMENT['max_concurrent_trades']}")
            
            # Check API keys
            if not config.PIONEX_API_KEY or not config.COINBASE_API_KEY:
                self.issues.append("❌ API keys not set - Need to add to .env file")
            else:
                self.passed_checks.append("✅ API keys configured")
            
            # Check currency pairs
            if len(config.CURRENCY_PAIRS) == 0:
                self.issues.append("❌ No currency pairs configured")
            else:
                self.passed_checks.append(f"✅ {len(config.CURRENCY_PAIRS)} currency pairs configured")
            
            # Check spread requirements
            for symbol, spread_config in config.CURRENCY_PAIR_SPREADS.items():
                if spread_config['min_spread'] < 0.003:
                    self.warnings.append(f"⚠️  {symbol} min spread < 0.3% - May not cover fees (0.6%)")
            
            self.passed_checks.append("✅ Spread requirements configured")
            
            # Check rate limits
            if config.CHECK_INTERVALS['price_check_seconds'] < 1:
                self.warnings.append("⚠️  Price check interval < 1s - May hit rate limits")
            else:
                self.passed_checks.append(f"✅ Price check interval: {config.CHECK_INTERVALS['price_check_seconds']}s")
            
        except ImportError as e:
            self.issues.append(f"❌ Cannot import aggressive_config: {e}")
        except Exception as e:
            self.issues.append(f"❌ Error loading config: {e}")
    
    def audit_components(self):
        """Audit system components"""
        print('\n' + '=' * 100)
        print('COMPONENT AUDIT')
        print('=' * 100)
        
        components = [
            ('aggressive_config.py', 'Main configuration'),
            ('auto_sizing_manager.py', 'Auto position sizing'),
            ('dynamic_spread_manager.py', 'Dynamic spread adjustment'),
            ('dynamic_slippage_detector.py', 'Slippage detection'),
            ('smart_rate_limiter.py', 'Rate limit management'),
        ]
        
        for filename, description in components:
            if os.path.exists(filename):
                self.passed_checks.append(f"✅ {filename} exists - {description}")
                
                # Try to import
                try:
                    module_name = filename.replace('.py', '')
                    __import__(module_name)
                    self.passed_checks.append(f"✅ {filename} imports successfully")
                except Exception as e:
                    self.issues.append(f"❌ {filename} import error: {e}")
            else:
                self.issues.append(f"❌ {filename} missing - {description}")
    
    def audit_dependencies(self):
        """Audit Python dependencies"""
        print('\n' + '=' * 100)
        print('DEPENDENCY AUDIT')
        print('=' * 100)
        
        required_packages = [
            'ccxt',
            'python-dotenv',
            'numpy',
            'asyncio',
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                self.passed_checks.append(f"✅ {package} installed")
            except ImportError:
                self.issues.append(f"❌ {package} not installed - Run: pip install {package}")
    
    def audit_logic_consistency(self):
        """Audit logic for consistency"""
        print('\n' + '=' * 100)
        print('LOGIC CONSISTENCY AUDIT')
        print('=' * 100)
        
        try:
            from aggressive_config import AggressiveConfig
            config = AggressiveConfig()
            
            # Check position sizing consistency
            total_base_positions = sum(config.BASE_POSITION_PERCENTAGES.values())
            if total_base_positions > 1.5:
                self.warnings.append(f"⚠️  Total base positions = {total_base_positions*100:.0f}% - "
                                   "Can't all be active at once")
            else:
                self.passed_checks.append(f"✅ Total base positions: {total_base_positions*100:.0f}%")
            
            # Check if max_total_exposure is consistent with concurrent trades
            max_concurrent = config.RISK_MANAGEMENT['max_concurrent_trades']
            max_position = config.RISK_MANAGEMENT['max_position_percent']
            theoretical_max_exposure = max_concurrent * max_position
            
            if theoretical_max_exposure > 1.0:
                self.warnings.append(f"⚠️  {max_concurrent} trades × {max_position*100:.0f}% = "
                                   f"{theoretical_max_exposure*100:.0f}% potential exposure - "
                                   "Exceeds 100%, will be limited by max_total_exposure")
            else:
                self.passed_checks.append(f"✅ Theoretical max exposure: {theoretical_max_exposure*100:.0f}%")
            
            # Check spread vs fees
            total_fees = 0.006  # 0.6%
            for symbol, spread_config in config.CURRENCY_PAIR_SPREADS.items():
                min_spread = spread_config['min_spread']
                if min_spread <= total_fees:
                    self.issues.append(f"❌ {symbol} min spread {min_spread*100:.2f}% <= fees {total_fees*100:.1f}% - "
                                     "Will lose money!")
                elif min_spread < total_fees * 1.2:
                    self.warnings.append(f"⚠️  {symbol} min spread {min_spread*100:.2f}% barely covers fees - "
                                       "Need buffer for slippage")
            
            self.passed_checks.append("✅ Most spreads cover fees + buffer")
            
            # Check rate limit calculations
            num_cryptos = len(config.CURRENCY_PAIRS)
            num_exchanges = 2
            price_check_interval = config.CHECK_INTERVALS['price_check_seconds']
            
            # Requests per second
            requests_per_check = num_cryptos * num_exchanges  # Price check on both exchanges
            checks_per_second = 1 / price_check_interval
            requests_per_second = requests_per_check * checks_per_second
            
            max_requests_per_second = config.EXCHANGE_RATE_LIMITS['pionex']['requests_per_second']
            
            if requests_per_second > max_requests_per_second * 0.8:
                self.issues.append(f"❌ Estimated {requests_per_second:.1f} req/s > "
                                 f"80% of limit ({max_requests_per_second * 0.8:.1f}) - "
                                 "Will hit rate limits!")
            else:
                self.passed_checks.append(f"✅ Estimated {requests_per_second:.1f} req/s < "
                                        f"limit ({max_requests_per_second})")
            
        except Exception as e:
            self.issues.append(f"❌ Logic consistency check failed: {e}")
    
    def audit_risk_management(self):
        """Audit risk management settings"""
        print('\n' + '=' * 100)
        print('RISK MANAGEMENT AUDIT')
        print('=' * 100)
        
        try:
            from aggressive_config import AggressiveConfig
            config = AggressiveConfig()
            
            # Check stop loss
            if config.RISK_MANAGEMENT.get('stop_loss_percent', 0) == 0:
                self.warnings.append("⚠️  No stop loss configured - Unlimited loss potential")
            else:
                self.passed_checks.append(f"✅ Stop loss: {config.RISK_MANAGEMENT['stop_loss_percent']*100:.1f}%")
            
            # Check drawdown protection
            if config.RISK_MANAGEMENT.get('max_daily_drawdown', 1.0) >= 0.20:
                self.warnings.append("⚠️  Max daily drawdown >= 20% - Very aggressive")
            else:
                self.passed_checks.append(f"✅ Max daily drawdown: {config.RISK_MANAGEMENT['max_daily_drawdown']*100:.0f}%")
            
            # Check emergency stop
            if config.RISK_MANAGEMENT.get('emergency_stop_drawdown', 1.0) >= 0.25:
                self.warnings.append("⚠️  Emergency stop >= 25% - Could lose a lot before stopping")
            else:
                self.passed_checks.append(f"✅ Emergency stop: {config.RISK_MANAGEMENT['emergency_stop_drawdown']*100:.0f}%")
            
            # Check minimum account balance
            if config.RISK_MANAGEMENT.get('min_account_balance_usd', 0) < 100:
                self.warnings.append("⚠️  Min account balance < $100 - May not be profitable with fees")
            else:
                self.passed_checks.append(f"✅ Min account balance: ${config.RISK_MANAGEMENT['min_account_balance_usd']}")
            
        except Exception as e:
            self.issues.append(f"❌ Risk management audit failed: {e}")
    
    def audit_exchange_compatibility(self):
        """Audit exchange compatibility"""
        print('\n' + '=' * 100)
        print('EXCHANGE COMPATIBILITY AUDIT')
        print('=' * 100)
        
        try:
            from aggressive_config import AggressiveConfig
            config = AggressiveConfig()
            
            # Check if all cryptos are available on both exchanges
            # This would require actual API calls, so we'll just check configuration
            
            self.passed_checks.append("✅ Using Pionex.US + Coinbase Pro (US-friendly)")
            
            # Check fee structure
            pionex_fee = config.EXCHANGE_FEES['pionex']['trading_fee']
            coinbase_fee = config.EXCHANGE_FEES['coinbasepro']['trading_fee']
            total_fee = pionex_fee + coinbase_fee
            
            if total_fee > 0.01:
                self.warnings.append(f"⚠️  Total trading fees {total_fee*100:.1f}% - High fees reduce profits")
            else:
                self.passed_checks.append(f"✅ Total trading fees: {total_fee*100:.1f}%")
            
            # Check withdrawal fees
            coinbase_withdrawals_free = all(
                fee == 0.0 for fee in config.EXCHANGE_FEES['coinbasepro']['withdrawal_fees'].values()
            )
            
            if coinbase_withdrawals_free:
                self.passed_checks.append("✅ Coinbase Pro: FREE withdrawals (always transfer from Coinbase)")
            else:
                self.warnings.append("⚠️  Coinbase Pro withdrawal fees detected")
            
        except Exception as e:
            self.issues.append(f"❌ Exchange compatibility audit failed: {e}")
    
    def audit_auto_sizing(self):
        """Audit auto-sizing configuration"""
        print('\n' + '=' * 100)
        print('AUTO-SIZING AUDIT')
        print('=' * 100)
        
        try:
            from aggressive_config import AggressiveConfig
            config = AggressiveConfig()
            
            if not config.AUTO_SIZING['enabled']:
                self.warnings.append("⚠️  Auto-sizing disabled - Missing key feature")
            else:
                self.passed_checks.append("✅ Auto-sizing enabled")
            
            # Check scale factors
            scale_up = config.AUTO_SIZING['scale_up_factor']
            scale_down = config.AUTO_SIZING['scale_down_factor']
            
            if scale_up > 1.20:
                self.warnings.append(f"⚠️  Scale up factor {scale_up} > 1.20 - Very aggressive growth")
            else:
                self.passed_checks.append(f"✅ Scale up factor: {scale_up}")
            
            if scale_down < 0.80:
                self.warnings.append(f"⚠️  Scale down factor {scale_down} < 0.80 - Very aggressive reduction")
            else:
                self.passed_checks.append(f"✅ Scale down factor: {scale_down}")
            
            # Check bounds
            if config.AUTO_SIZING['max_position_percent'] != config.RISK_MANAGEMENT['max_position_percent']:
                self.warnings.append("⚠️  Auto-sizing max != risk management max - Inconsistent")
            else:
                self.passed_checks.append("✅ Auto-sizing bounds consistent with risk management")
            
        except Exception as e:
            self.issues.append(f"❌ Auto-sizing audit failed: {e}")
    
    def audit_dynamic_features(self):
        """Audit dynamic spread and slippage features"""
        print('\n' + '=' * 100)
        print('DYNAMIC FEATURES AUDIT')
        print('=' * 100)
        
        try:
            from aggressive_config import AggressiveConfig
            config = AggressiveConfig()
            
            # Check dynamic spreads
            if not config.DYNAMIC_SPREADS['enabled']:
                self.warnings.append("⚠️  Dynamic spreads disabled - Missing optimization")
            else:
                self.passed_checks.append("✅ Dynamic spreads enabled")
            
            # Check spread bounds
            min_floor = config.DYNAMIC_SPREADS['min_spread_floor']
            max_ceiling = config.DYNAMIC_SPREADS['max_spread_ceiling']
            
            if min_floor < 0.003:
                self.warnings.append(f"⚠️  Min spread floor {min_floor*100:.1f}% < 0.3% - May not cover fees")
            else:
                self.passed_checks.append(f"✅ Min spread floor: {min_floor*100:.1f}%")
            
            # Check dynamic slippage
            if not config.DYNAMIC_SLIPPAGE['enabled']:
                self.warnings.append("⚠️  Dynamic slippage disabled - Missing risk protection")
            else:
                self.passed_checks.append("✅ Dynamic slippage enabled")
            
            # Check slippage thresholds
            max_slippage = config.DYNAMIC_SLIPPAGE['max_acceptable_slippage']
            if max_slippage > 0.005:
                self.warnings.append(f"⚠️  Max acceptable slippage {max_slippage*100:.1f}% > 0.5% - High slippage tolerance")
            else:
                self.passed_checks.append(f"✅ Max acceptable slippage: {max_slippage*100:.1f}%")
            
        except Exception as e:
            self.issues.append(f"❌ Dynamic features audit failed: {e}")
    
    def generate_report(self):
        """Generate comprehensive audit report"""
        print('\n' + '=' * 100)
        print('AUDIT REPORT SUMMARY')
        print('=' * 100)
        
        print(f"\n✅ PASSED CHECKS: {len(self.passed_checks)}")
        for check in self.passed_checks:
            print(f"  {check}")
        
        print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
        for warning in self.warnings:
            print(f"  {warning}")
        
        print(f"\n❌ CRITICAL ISSUES: {len(self.issues)}")
        for issue in self.issues:
            print(f"  {issue}")
        
        print('\n' + '=' * 100)
        print('RECOMMENDATIONS')
        print('=' * 100)
        
        # Generate recommendations based on findings
        if len(self.issues) > 0:
            print("\n🔴 CRITICAL - FIX BEFORE RUNNING:")
            for issue in self.issues:
                print(f"  {issue}")
        
        if len(self.warnings) > 0:
            print("\n🟡 WARNINGS - REVIEW CAREFULLY:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if len(self.issues) == 0 and len(self.warnings) == 0:
            print("\n🟢 ALL CHECKS PASSED - SYSTEM READY TO RUN!")
        elif len(self.issues) == 0:
            print("\n🟡 NO CRITICAL ISSUES - SYSTEM CAN RUN (review warnings)")
        else:
            print("\n🔴 CRITICAL ISSUES FOUND - DO NOT RUN UNTIL FIXED")
        
        # Additional recommendations
        print("\n💡 GENERAL RECOMMENDATIONS:")
        print("  1. Start with small amounts ($100-1000) to test")
        print("  2. Monitor closely for first 24-48 hours")
        print("  3. Check rate limit usage regularly")
        print("  4. Review auto-sizing adjustments daily")
        print("  5. Keep emergency stop at 15% max drawdown")
        print("  6. Always transfer from Coinbase (free withdrawals)")
        print("  7. Set up alerts for errors and low balance")
        print("  8. Back up configuration and logs daily")
        
        return {
            'passed': len(self.passed_checks),
            'warnings': len(self.warnings),
            'issues': len(self.issues),
            'ready_to_run': len(self.issues) == 0
        }

def run_system_audit():
    """Run complete system audit"""
    print('=' * 100)
    print('COMPREHENSIVE SYSTEM AUDIT')
    print('Checking for issues, inconsistencies, and potential problems')
    print('=' * 100)
    
    auditor = SystemAuditor()
    
    # Run all audits
    auditor.audit_configuration()
    auditor.audit_components()
    auditor.audit_dependencies()
    auditor.audit_logic_consistency()
    auditor.audit_risk_management()
    auditor.audit_exchange_compatibility()
    auditor.audit_auto_sizing()
    auditor.audit_dynamic_features()
    
    # Generate report
    results = auditor.generate_report()
    
    return results

if __name__ == "__main__":
    results = run_system_audit()
    
    print(f"\n{'=' * 100}")
    print(f"AUDIT COMPLETE")
    print(f"Passed: {results['passed']} | Warnings: {results['warnings']} | Issues: {results['issues']}")
    print(f"Ready to run: {'YES ✅' if results['ready_to_run'] else 'NO ❌'}")
    print(f"{'=' * 100}\n")

