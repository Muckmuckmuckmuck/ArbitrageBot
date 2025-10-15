#!/usr/bin/env python3
"""
Debug Coinbase withdrawal to understand the exact error
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager


async def main():
    print("\n🔍 DEBUGGING COINBASE WITHDRAWAL...")
    print("="*60)
    
    mgr = CoinbaseGeminiExchangeManager()
    
    try:
        await mgr.initialize()
        cb = mgr.exchanges['coinbase']
        gem = mgr.exchanges['gemini']
        
        # Get Gemini deposit address
        print("1. Getting Gemini XRP deposit address...")
        deposit_info = gem.fetch_deposit_address('XRP', {'network': 'XRP'})
        if hasattr(deposit_info, '__await__'):
            deposit_info = await deposit_info
        
        address = deposit_info['address']
        tag = deposit_info.get('tag')
        
        print(f"   Address: {address}")
        print(f"   Tag: {tag}")
        
        # Get small amount of XRP to test with
        bal = cb.fetch_balance()
        if hasattr(bal, '__await__'):
            bal = await bal
        
        xrp_balance = float(bal['free'].get('XRP', 0))
        print(f"\n2. Coinbase XRP balance: {xrp_balance:.6f}")
        
        if xrp_balance < 0.1:
            print("❌ Not enough XRP to test withdrawal")
            return
        
        # Test with small amount
        test_amount = 0.1  # Small test amount
        print(f"\n3. Testing withdrawal of {test_amount} XRP...")
        
        # Try different parameter combinations
        test_cases = [
            {"network": "XRP"},
            {"network": "XRP", "destination_tag": tag} if tag else None,
            {"network": "XRP", "destination_tag": "0"} if tag else None,
            {"network": "XRP", "destination_tag": ""} if tag else None,
        ]
        
        for i, params in enumerate(test_cases):
            if params is None:
                continue
                
            print(f"\n   Test {i+1}: {params}")
            
            try:
                withdrawal = cb.withdraw(
                    code='XRP',
                    amount=test_amount,
                    address=address,
                    params=params
                )
                if hasattr(withdrawal, '__await__'):
                    withdrawal = await withdrawal
                
                print(f"   ✅ SUCCESS! Withdrawal ID: {withdrawal.get('id', 'unknown')}")
                print(f"   Status: {withdrawal.get('status', 'unknown')}")
                break
                
            except Exception as e:
                error_msg = str(e)
                print(f"   ❌ FAILED: {error_msg}")
                
                # Try to extract more details
                if "internal_server_error" in error_msg:
                    print(f"      → This is a generic Coinbase error")
                    print(f"      → Could be: missing tag, invalid address, or account restriction")
                elif "destination_tag" in error_msg:
                    print(f"      → Destination tag issue")
                elif "address" in error_msg:
                    print(f"      → Address format issue")
                else:
                    print(f"      → Unknown error type")
        
        print(f"\n4. Summary:")
        print(f"   - Gemini address: {address}")
        print(f"   - Gemini tag: {tag}")
        print(f"   - Test amount: {test_amount} XRP")
        print(f"   - If all tests failed, the issue is likely:")
        print(f"     * Account-level withdrawal restriction")
        print(f"     * Address format incompatibility")
        print(f"     * Missing required parameters")
        
    except Exception as e:
        print(f"\n❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        await mgr.close()


if __name__ == "__main__":
    asyncio.run(main())
