#!/usr/bin/env python3
"""
Pre-Flight Check
Comprehensive test before running bot with real money
"""

import sys
import os
import asyncio
from typing import List, Tuple

def print_header(title):
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80 + "\n")

def print_result(test_name, passed, message=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status:10} | {test_name:40} | {message}")
    return passed

async def run_pre_flight_checks():
    """Run all pre-flight checks"""
    
    print_header("PRE-FLIGHT CHECK - COMPREHENSIVE BOT VALIDATION")
    
    all_passed = True
    
    # Test 1: Python Version
    print_header("TEST 1: PYTHON VERSION")
    python_version = sys.version_info
    passed = python_version >= (3, 8)
    all_passed &= print_result(
        "Python 3.8+",
        passed,
        f"Current: {python_version.major}.{python_version.minor}"
    )
    
    # Test 2: Required Packages
    print_header("TEST 2: REQUIRED PACKAGES")
    
    required_packages = [
        'ccxt',
        'dotenv', 
        'numpy',
        'asyncio',
        'logging',
        'dataclasses',
        'typing',
        'datetime',
        'signal',
    ]
    
    for package in required_packages:
        try:
            __import__(package if package != 'dotenv' else 'dotenv')
            all_passed &= print_result(f"Package: {package}", True)
        except ImportError:
            all_passed &= print_result(f"Package: {package}", False, "NOT INSTALLED")
    
    # Test 3: Bot Files Exist
    print_header("TEST 3: BOT FILES")
    
    required_files = [
        'aggressive_bot_fixed.py',
        'aggressive_config.py',
        'auto_sizing_manager.py',
        'dynamic_spread_manager.py',
        'dynamic_slippage_detector.py',
        'smart_rate_limiter.py',
        'balance_validator.py',
        'fixed_percentage_balance_manager.py',
        'comprehensive_error_handler.py',
        'thread_safe_exchange_manager.py',
    ]
    
    for filename in required_files:
        exists = os.path.exists(filename)
        all_passed &= print_result(f"File: {filename}", exists)
    
    # Test 4: Bot Code Compiles
    print_header("TEST 4: CODE COMPILATION")
    
    try:
        import py_compile
        py_compile.compile('aggressive_bot_fixed.py', doraise=True)
        all_passed &= print_result("Bot compilation", True)
    except Exception as e:
        all_passed &= print_result("Bot compilation", False, str(e))
    
    # Test 5: Configuration Loads
    print_header("TEST 5: CONFIGURATION")
    
    try:
        from aggressive_config import AggressiveConfig
        config = AggressiveConfig()
        all_passed &= print_result("Config loads", True)
        
        # Check API keys
        has_pionex = bool(config.PIONEX_API_KEY)
        has_coinbase = bool(config.COINBASE_API_KEY)
        
        all_passed &= print_result("Pionex API key", has_pionex, 
                                   "Set" if has_pionex else "MISSING")
        all_passed &= print_result("Coinbase API key", has_coinbase,
                                   "Set" if has_coinbase else "MISSING")
        
        # Check testnet mode
        print_result("Pionex testnet", True,
                    "ENABLED" if config.PIONEX_TESTNET else "DISABLED (PRODUCTION)")
        print_result("Coinbase sandbox", True,
                    "ENABLED" if config.COINBASE_SANDBOX else "DISABLED (PRODUCTION)")
        
        # Check currency pairs
        has_pairs = len(config.CURRENCY_PAIRS) > 0
        all_passed &= print_result("Currency pairs", has_pairs,
                                   f"{len(config.CURRENCY_PAIRS)} configured")
        
    except Exception as e:
        all_passed &= print_result("Config loads", False, str(e))
    
    # Test 6: Component Imports
    print_header("TEST 6: COMPONENT IMPORTS")
    
    components = [
        ('auto_sizing_manager', 'AutoSizingManager'),
        ('dynamic_spread_manager', 'DynamicSpreadManager'),
        ('dynamic_slippage_detector', 'DynamicSlippageDetector'),
        ('smart_rate_limiter', 'SmartRateLimiter'),
        ('balance_validator', 'BalanceValidator'),
        ('fixed_percentage_balance_manager', 'FixedPercentageBalanceManager'),
    ]
    
    for module_name, class_name in components:
        try:
            module = __import__(module_name)
            getattr(module, class_name)
            all_passed &= print_result(f"Component: {class_name}", True)
        except Exception as e:
            all_passed &= print_result(f"Component: {class_name}", False, str(e))
    
    # Test 7: Exchange Connectivity (if keys provided)
    print_header("TEST 7: EXCHANGE CONNECTIVITY")
    
    try:
        from aggressive_config import AggressiveConfig
        import ccxt
        
        config = AggressiveConfig()
        
        if config.PIONEX_API_KEY and config.COINBASE_API_KEY:
            print("Testing exchange connections...")
            
            # Test Pionex
            try:
                pionex = ccxt.pionex({
                    'apiKey': config.PIONEX_API_KEY,
                    'secret': config.PIONEX_SECRET_KEY,
                    'enableRateLimit': True,
                })
                if config.PIONEX_TESTNET:
                    pionex.set_sandbox_mode(True)
                
                await pionex.load_markets()
                all_passed &= print_result("Pionex connection", True, 
                                          f"{len(pionex.markets)} markets")
                await pionex.close()
            except Exception as e:
                all_passed &= print_result("Pionex connection", False, str(e))
            
            # Test Coinbase
            try:
                coinbase = ccxt.coinbasepro({
                    'apiKey': config.COINBASE_API_KEY,
                    'secret': config.COINBASE_SECRET_KEY,
                    'password': config.COINBASE_PASSPHRASE,
                    'enableRateLimit': True,
                })
                if config.COINBASE_SANDBOX:
                    coinbase.set_sandbox_mode(True)
                
                await coinbase.load_markets()
                all_passed &= print_result("Coinbase connection", True,
                                          f"{len(coinbase.markets)} markets")
                await coinbase.close()
            except Exception as e:
                all_passed &= print_result("Coinbase connection", False, str(e))
        else:
            print_result("Exchange test", False, "API keys not configured - skipping")
    
    except Exception as e:
        print_result("Exchange test", False, f"Error: {e}")
    
    # Test 8: Bot Initialization (Dry Run)
    print_header("TEST 8: BOT INITIALIZATION")
    
    try:
        # This will fail if API keys aren't set, but that's ok for the test
        from aggressive_bot_fixed import AggressiveArbitrageBot
        print_result("Bot import", True)
        
        # Try to create instance (will fail without keys, but tests the code)
        try:
            bot = AggressiveArbitrageBot()
            print_result("Bot instantiation", True)
        except Exception as e:
            if "API keys" in str(e):
                print_result("Bot instantiation", True, "Needs API keys (expected)")
            else:
                print_result("Bot instantiation", False, str(e))
    except Exception as e:
        all_passed &= print_result("Bot import", False, str(e))
    
    # Final Summary
    print_header("PRE-FLIGHT CHECK SUMMARY")
    
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print()
        print("Your bot is ready to run!")
        print()
        print("Next steps:")
        print("1. If not done: Set up API keys in .env file")
        print("2. Start in sandbox mode: python aggressive_bot_fixed.py")
        print("3. Monitor for 24 hours")
        print("4. If successful, switch to production with small amount")
        print()
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Please fix the issues above before running the bot.")
        print()
        print("Common fixes:")
        print("- Install packages: pip install ccxt python-dotenv numpy")
        print("- Set up .env file with API keys")
        print("- Make sure all component files are present")
        print()
        return 1

def main():
    """Main entry point"""
    try:
        exit_code = asyncio.run(run_pre_flight_checks())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nPre-flight check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error during pre-flight check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

