#!/usr/bin/env python3
"""
Test that configuration is set up correctly
"""

import sys
import os

def main():
    print("=" * 80)
    print("TESTING CONFIGURATION")
    print("=" * 80)
    print()
    
    # Test 1: Check .env file exists
    print("Test 1: Checking .env file...")
    if not os.path.exists('.env'):
        print("❌ FAILED - .env file not found")
        print()
        print("Please create .env file with:")
        print("  PIONEX_API_KEY=your_key")
        print("  PIONEX_SECRET_KEY=your_secret")
        print("  PIONEX_TESTNET=true")
        print("  COINBASE_API_KEY=your_key")
        print("  COINBASE_SECRET_KEY=your_secret")
        print("  COINBASE_PASSPHRASE=your_passphrase")
        print("  COINBASE_SANDBOX=true")
        print()
        sys.exit(1)
    else:
        print("✅ .env file found")
    
    # Test 2: Load configuration
    print("\nTest 2: Loading configuration...")
    try:
        from aggressive_config import AggressiveConfig
        config = AggressiveConfig()
        print("✅ Configuration loaded successfully")
    except Exception as e:
        print(f"❌ FAILED - Could not load configuration: {e}")
        sys.exit(1)
    
    # Test 3: Check API keys
    print("\nTest 3: Checking API keys...")
    issues = []
    
    if not config.PIONEX_API_KEY:
        issues.append("PIONEX_API_KEY not set")
    if not config.PIONEX_SECRET_KEY:
        issues.append("PIONEX_SECRET_KEY not set")
    if not config.COINBASE_API_KEY:
        issues.append("COINBASE_API_KEY not set")
    if not config.COINBASE_SECRET_KEY:
        issues.append("COINBASE_SECRET_KEY not set")
    if not config.COINBASE_PASSPHRASE:
        issues.append("COINBASE_PASSPHRASE not set")
    
    if issues:
        print("❌ FAILED - Missing API keys:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("Please add these to your .env file")
        sys.exit(1)
    else:
        print("✅ All API keys configured")
    
    # Test 4: Check testnet mode
    print("\nTest 4: Checking testnet mode...")
    if config.PIONEX_TESTNET:
        print("✅ Pionex testnet mode: ENABLED")
    else:
        print("⚠️  Pionex testnet mode: DISABLED (production mode)")
    
    if config.COINBASE_SANDBOX:
        print("✅ Coinbase sandbox mode: ENABLED")
    else:
        print("⚠️  Coinbase sandbox mode: DISABLED (production mode)")
    
    # Test 5: Check currency pairs
    print(f"\nTest 5: Checking currency pairs...")
    print(f"✅ {len(config.CURRENCY_PAIRS)} currency pairs configured:")
    for pair in config.CURRENCY_PAIRS:
        print(f"  - {pair}")
    
    # Test 6: Check risk management
    print(f"\nTest 6: Checking risk management...")
    print(f"✅ Risk management settings:")
    print(f"  - Max position: {config.RISK_MANAGEMENT['max_position_percent']*100:.0f}%")
    print(f"  - Max total exposure: {config.RISK_MANAGEMENT['max_total_exposure']*100:.0f}%")
    print(f"  - Reserve: {config.RISK_MANAGEMENT['reserve_percent']*100:.0f}%")
    print(f"  - Max concurrent trades: {config.RISK_MANAGEMENT['max_concurrent_trades']}")
    print(f"  - Emergency stop drawdown: {config.RISK_MANAGEMENT['emergency_stop_drawdown']*100:.0f}%")
    
    # Summary
    print()
    print("=" * 80)
    print("CONFIGURATION TEST RESULTS")
    print("=" * 80)
    
    if config.PIONEX_TESTNET and config.COINBASE_SANDBOX:
        print()
        print("✅ ALL TESTS PASSED - TESTNET MODE")
        print()
        print("Configuration is correct for sandbox testing.")
        print()
        print("Next steps:")
        print("1. Make sure you have test funds in sandbox accounts")
        print("2. Run: python aggressive_bot_fixed.py")
        print()
    elif not config.PIONEX_TESTNET and not config.COINBASE_SANDBOX:
        print()
        print("⚠️  ALL TESTS PASSED - PRODUCTION MODE")
        print()
        print("WARNING: You are in PRODUCTION mode!")
        print("This will use REAL MONEY.")
        print()
        print("Make sure:")
        print("1. You have tested in sandbox first")
        print("2. You are ready to use real money")
        print("3. You start with a small amount ($100-500)")
        print()
        response = input("Type 'YES' to confirm you want to run in production mode: ")
        if response != 'YES':
            print("\nAborting. Switch to testnet mode first.")
            print("Set PIONEX_TESTNET=true and COINBASE_SANDBOX=true in .env")
            sys.exit(1)
        print()
    else:
        print()
        print("⚠️  MIXED MODE DETECTED")
        print()
        print("You have one exchange in testnet and one in production.")
        print("This is not recommended. Both should be the same.")
        print()
        print("For testing: Set both to testnet")
        print("For production: Set both to production")
        print()
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()

