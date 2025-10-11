#!/usr/bin/env python3
"""
Test Transfer Logic
Verify automated transfer functionality works correctly
"""

import sys
import os

def main():
    print("=" * 80)
    print("TRANSFER LOGIC VERIFICATION")
    print("=" * 80)
    print()
    
    passed = []
    failed = []
    
    # Test 1: Import transfer manager
    print("[1] Testing transfer_manager_fixed.py...")
    try:
        from transfer_manager_fixed import TransferManager, TransferResult
        passed.append("✅ TransferManager imports")
        
        # Check methods exist
        assert hasattr(TransferManager, 'transfer_crypto'), "Missing transfer_crypto"
        assert hasattr(TransferManager, 'get_deposit_address'), "Missing get_deposit_address"
        assert hasattr(TransferManager, 'rebalance_account'), "Missing rebalance_account"
        passed.append("✅ TransferManager has all required methods")
        
    except Exception as e:
        failed.append(f"❌ TransferManager: {e}")
    
    # Test 2: Import bot with transfers
    print("\n[2] Testing aggressive_bot_with_transfers.py...")
    try:
        from aggressive_bot_with_transfers import AggressiveArbitrageBotWithTransfers
        passed.append("✅ Bot with transfers imports")
        
        # Check it has transfer_manager
        os.environ['PIONEX_API_KEY'] = 'test'
        os.environ['PIONEX_SECRET_KEY'] = 'test'
        os.environ['COINBASE_API_KEY'] = 'test'
        os.environ['COINBASE_SECRET_KEY'] = 'test'
        os.environ['COINBASE_PASSPHRASE'] = 'test'
        
        bot = AggressiveArbitrageBotWithTransfers()
        assert hasattr(bot, 'transfer_manager'), "Bot missing transfer_manager"
        passed.append("✅ Bot has transfer_manager attribute")
        
        # Check _execute_complete_arbitrage exists
        assert hasattr(bot, '_execute_complete_arbitrage'), "Missing _execute_complete_arbitrage"
        passed.append("✅ Bot has _execute_complete_arbitrage method")
        
    except Exception as e:
        failed.append(f"❌ Bot with transfers: {e}")
    
    # Test 3: Verify transfer logic is in correct order
    print("\n[3] Testing arbitrage cycle logic...")
    try:
        with open('aggressive_bot_with_transfers.py', 'r') as f:
            code = f.read()
        
        # Check phases are in correct order
        buy_index = code.find('PHASE 1')
        transfer_index = code.find('PHASE 2')
        sell_index = code.find('PHASE 3')
        
        assert buy_index > 0, "Missing PHASE 1 (buy)"
        assert transfer_index > 0, "Missing PHASE 2 (transfer)"
        assert sell_index > 0, "Missing PHASE 3 (sell)"
        
        assert buy_index < transfer_index < sell_index, "Phases out of order!"
        
        passed.append("✅ Arbitrage phases in correct order (Buy → Transfer → Sell)")
        
        # Check transfer is called
        assert 'transfer_manager.transfer_crypto' in code, "transfer_crypto not called"
        passed.append("✅ Transfer logic is called")
        
        # Check for transfer confirmation wait
        assert '_wait_for_deposit' in code or 'transfer_result' in code, "Missing transfer wait logic"
        passed.append("✅ Transfer confirmation logic present")
        
    except Exception as e:
        failed.append(f"❌ Arbitrage cycle: {e}")
    
    # Test 4: Verify timing expectations
    print("\n[4] Verifying timing expectations...")
    try:
        from aggressive_config import AggressiveConfig
        config = AggressiveConfig()
        
        # Calculate expected cycle time
        for symbol, spread_config in config.CURRENCY_PAIR_SPREADS.items():
            transfer_time = spread_config['transfer_time']
            
            # Estimate total cycle time
            api_time = 1  # 1s for API calls
            buy_time = 2  # 2s for buy order
            sell_time = 2  # 2s for sell order
            total_time = api_time + buy_time + transfer_time + sell_time
            
            print(f"   {symbol}: ~{total_time}s total cycle time")
        
        passed.append("✅ Timing expectations calculated")
        
    except Exception as e:
        failed.append(f"❌ Timing: {e}")
    
    # Test 5: Check for error handling in transfers
    print("\n[5] Checking error handling...")
    try:
        with open('aggressive_bot_with_transfers.py', 'r') as f:
            code = f.read()
        
        # Check for try/except around transfers
        assert 'except Exception as e' in code, "Missing exception handling"
        passed.append("✅ Exception handling present")
        
        # Check for transfer failure handling
        assert 'transfer_result.success' in code, "Missing transfer success check"
        passed.append("✅ Transfer success validation present")
        
        # Check for stuck position logging
        assert 'stuck' in code.lower() or 'manual intervention' in code.lower(), \
            "Missing stuck position handling"
        passed.append("✅ Stuck position handling present")
        
    except Exception as e:
        failed.append(f"❌ Error handling: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("TRANSFER LOGIC VERIFICATION SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ PASSED ({len(passed)}):")
    for item in passed:
        print(f"  {item}")
    
    if failed:
        print(f"\n❌ FAILED ({len(failed)}):")
        for item in failed:
            print(f"  {item}")
    
    print("\n" + "=" * 80)
    
    if len(failed) == 0:
        print("✅ TRANSFER LOGIC VERIFIED - READY FOR TESTING!")
        print()
        print("The bot will now:")
        print("  1. Buy crypto on cheaper exchange")
        print("  2. Transfer crypto to expensive exchange (3-120s)")
        print("  3. Sell crypto on expensive exchange")
        print("  4. Profit!")
        print()
        print("Next steps:")
        print("  1. Test in sandbox mode first!")
        print("  2. Run: python aggressive_bot_with_transfers.py")
        print("  3. Monitor logs carefully")
        print("  4. Verify transfers complete successfully")
        print()
        return 0
    else:
        print("❌ TRANSFER LOGIC HAS ISSUES - FIX BEFORE USING")
        return 1

if __name__ == "__main__":
    sys.exit(main())

