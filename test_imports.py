#!/usr/bin/env python3
"""
Test that all imports work correctly
Run this before starting the bot
"""

import sys
import traceback

def test_import(module_name, description):
    """Test importing a module"""
    try:
        __import__(module_name)
        print(f"✅ {description:50} - OK")
        return True
    except ImportError as e:
        print(f"❌ {description:50} - FAILED: {e}")
        return False
    except Exception as e:
        print(f"⚠️  {description:50} - ERROR: {e}")
        return False

def main():
    print("=" * 80)
    print("TESTING ALL IMPORTS")
    print("=" * 80)
    print()
    
    tests = [
        # Core dependencies
        ("ccxt", "CCXT library (exchange connections)"),
        ("dotenv", "Python-dotenv (environment variables)"),
        ("numpy", "NumPy (numerical operations)"),
        ("asyncio", "AsyncIO (async operations)"),
        
        # Project modules
        ("aggressive_config", "Aggressive configuration"),
        ("auto_sizing_manager", "Auto-sizing manager"),
        ("dynamic_spread_manager", "Dynamic spread manager"),
        ("dynamic_slippage_detector", "Dynamic slippage detector"),
        ("smart_rate_limiter", "Smart rate limiter"),
        ("balance_validator", "Balance validator"),
        ("fixed_percentage_balance_manager", "Balance manager"),
        ("comprehensive_error_handler", "Error handler"),
        ("thread_safe_exchange_manager", "Thread-safe exchange manager"),
    ]
    
    passed = 0
    failed = 0
    
    for module_name, description in tests:
        if test_import(module_name, description):
            passed += 1
        else:
            failed += 1
    
    print()
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed > 0:
        print()
        print("❌ FAILED - Please install missing dependencies:")
        print("   pip install ccxt python-dotenv numpy")
        print()
        sys.exit(1)
    else:
        print()
        print("✅ SUCCESS - All imports working correctly!")
        print()
        print("Next steps:")
        print("1. Set up .env file with your API keys")
        print("2. Run: python aggressive_bot_fixed.py")
        print()
        sys.exit(0)

if __name__ == "__main__":
    main()

