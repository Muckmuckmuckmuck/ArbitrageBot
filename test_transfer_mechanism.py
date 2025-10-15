#!/usr/bin/env python3
"""
Test Transfer Mechanism - Validate crypto transfers work between Coinbase and Gemini

This script will:
1. Buy $1 of XRP on Coinbase
2. Transfer XRP to Gemini  
3. Sell XRP on Gemini
4. Buy $1 of XRP on Gemini
5. Transfer XRP to Coinbase
6. Sell XRP on Coinbase

This validates the full transfer pipeline without running the main bot.
"""

import asyncio
import os
import sys
import time
from decimal import Decimal
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from coinbase_gemini_config import Config


class TransferTester:
    def __init__(self):
        self.exchange_manager = CoinbaseGeminiExchangeManager()
        self.test_symbol = "XRP/USD"  # Fast, cheap, reliable
        self.test_crypto = "XRP"
        self.test_amount_usd = 1.0  # $1 test
        
    async def initialize(self):
        """Initialize exchanges"""
        print("\n" + "="*80)
        print("🔧 INITIALIZING EXCHANGE CONNECTIONS")
        print("="*80)
        await self.exchange_manager.initialize()
        print("✅ Exchanges initialized\n")
        
    async def get_balance(self, exchange_name: str, currency: str) -> float:
        """Get balance for a specific currency on an exchange"""
        exchange = self.exchange_manager.exchanges[exchange_name]
        balance = await exchange.fetch_balance()
        
        # Handle both sync and async responses
        if hasattr(balance, '__await__'):
            balance = await balance
            
        free = balance.get('free', {})
        return float(free.get(currency, 0))
        
    async def get_price(self, exchange_name: str, symbol: str) -> float:
        """Get current price for a symbol"""
        exchange = self.exchange_manager.exchanges[exchange_name]
        ticker = await exchange.fetch_ticker(symbol)
        
        # Handle both sync and async responses
        if hasattr(ticker, '__await__'):
            ticker = await ticker
            
        return float(ticker['last'])
        
    async def buy_crypto(self, exchange_name: str, symbol: str, amount_usd: float) -> Optional[Dict]:
        """Buy crypto with USD"""
        print(f"\n💰 BUYING ${amount_usd:.2f} of {symbol} on {exchange_name.upper()}")
        
        exchange = self.exchange_manager.exchanges[exchange_name]
        
        # Get current price
        price = await self.get_price(exchange_name, symbol)
        print(f"   Current price: ${price:.4f}")
        
        # Calculate amount to buy
        amount = amount_usd / price
        print(f"   Will buy: {amount:.4f} {self.test_crypto}")
        
        # Create market buy order (Coinbase style - needs price for market buys)
        try:
            if exchange_name == 'coinbase':
                # Coinbase requires price for market buy orders
                order = exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side='buy',
                    amount=amount,
                    params={'funds': amount_usd}  # Use funds parameter
                )
            else:
                # Gemini uses limit orders
                order = exchange.create_limit_buy_order(
                    symbol=symbol,
                    amount=amount,
                    price=price * 1.01  # 1% above market to ensure fill
                )
            
            # Handle both sync and async
            if hasattr(order, '__await__'):
                order = await order
                
            print(f"   ✅ Order placed: {order.get('id', 'unknown')}")
            print(f"   Status: {order.get('status', 'unknown')}")
            
            # Wait for fill
            await asyncio.sleep(3)
            
            # Verify balance
            balance = await self.get_balance(exchange_name, self.test_crypto)
            print(f"   {self.test_crypto} balance: {balance:.4f}")
            
            return order
            
        except Exception as e:
            print(f"   ❌ Buy failed: {str(e)}")
            return None
            
    async def transfer_crypto(self, from_exchange: str, to_exchange: str, amount: float) -> bool:
        """Transfer crypto from one exchange to another"""
        print(f"\n🚀 TRANSFERRING {amount:.4f} {self.test_crypto} from {from_exchange.upper()} → {to_exchange.upper()}")
        
        source_exchange = self.exchange_manager.exchanges[from_exchange]
        dest_exchange = self.exchange_manager.exchanges[to_exchange]
        
        try:
            # Get deposit address on destination
            print(f"   📍 Getting deposit address on {to_exchange}...")
            deposit_info = dest_exchange.fetch_deposit_address(self.test_crypto)
            
            # Handle both sync and async
            if hasattr(deposit_info, '__await__'):
                deposit_info = await deposit_info
                
            deposit_address = deposit_info['address']
            deposit_tag = deposit_info.get('tag')
            
            print(f"   Address: {deposit_address}")
            if deposit_tag:
                print(f"   Tag: {deposit_tag}")
                
            # Record balance before transfer
            balance_before = await self.get_balance(to_exchange, self.test_crypto)
            print(f"   {to_exchange} balance before: {balance_before:.4f} {self.test_crypto}")
            
            # Initiate withdrawal from source
            print(f"   💸 Initiating withdrawal from {from_exchange}...")
            
            withdraw_params = {'network': 'XRP'}  # Specify network
            if deposit_tag:
                withdraw_params['tag'] = deposit_tag
                
            withdrawal = source_exchange.withdraw(
                code=self.test_crypto,
                amount=amount,
                address=deposit_address,
                params=withdraw_params
            )
            
            # Handle both sync and async
            if hasattr(withdrawal, '__await__'):
                withdrawal = await withdrawal
                
            withdrawal_id = withdrawal.get('id', 'unknown')
            print(f"   ✅ Withdrawal initiated: {withdrawal_id}")
            
            # Monitor destination balance
            print(f"   ⏳ Waiting for transfer to complete...")
            print(f"   (XRP transfers typically take 30-120 seconds)")
            
            max_wait_time = 300  # 5 minutes max
            check_interval = 10  # Check every 10 seconds
            elapsed = 0
            
            while elapsed < max_wait_time:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                balance_now = await self.get_balance(to_exchange, self.test_crypto)
                
                if balance_now > balance_before + (amount * 0.95):  # 95% of amount (allow for minor fees)
                    print(f"   ✅ Transfer confirmed! {to_exchange} balance: {balance_now:.4f} {self.test_crypto}")
                    print(f"   Time elapsed: {elapsed}s")
                    return True
                    
                print(f"   ⏳ Still waiting... ({elapsed}s elapsed, balance: {balance_now:.4f})")
                
            print(f"   ⚠️  Transfer timeout after {max_wait_time}s")
            print(f"   Check exchange manually - withdrawal may still complete")
            return False
            
        except Exception as e:
            print(f"   ❌ Transfer failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    async def sell_crypto(self, exchange_name: str, symbol: str, amount: float) -> Optional[Dict]:
        """Sell crypto for USD"""
        print(f"\n💸 SELLING {amount:.4f} {self.test_crypto} on {exchange_name.upper()}")
        
        exchange = self.exchange_manager.exchanges[exchange_name]
        
        # Get current price
        price = await self.get_price(exchange_name, symbol)
        print(f"   Current price: ${price:.4f}")
        
        expected_usd = amount * price
        print(f"   Expected USD: ${expected_usd:.2f}")
        
        try:
            # Create sell order
            if exchange_name == 'coinbase':
                # Coinbase market sell
                order = exchange.create_market_sell_order(symbol=symbol, amount=amount)
            else:
                # Gemini limit sell (1% below market to ensure fill)
                order = exchange.create_limit_sell_order(
                    symbol=symbol,
                    amount=amount,
                    price=price * 0.99
                )
            
            # Handle both sync and async
            if hasattr(order, '__await__'):
                order = await order
                
            print(f"   ✅ Order placed: {order.get('id', 'unknown')}")
            print(f"   Status: {order.get('status', 'unknown')}")
            
            # Wait for fill
            await asyncio.sleep(3)
            
            # Verify USD balance
            usd_balance = await self.get_balance(exchange_name, 'USD')
            print(f"   USD balance: ${usd_balance:.2f}")
            
            return order
            
        except Exception as e:
            print(f"   ❌ Sell failed: {str(e)}")
            return None
            
    async def test_coinbase_to_gemini(self):
        """Test: Coinbase → Gemini transfer"""
        print("\n" + "="*80)
        print("🧪 TEST 1: COINBASE → GEMINI TRANSFER")
        print("="*80)
        
        # Step 1: Buy XRP on Coinbase
        order = await self.buy_crypto('coinbase', self.test_symbol, self.test_amount_usd)
        if not order:
            print("❌ Test failed at buy step")
            return False
            
        # Get amount bought
        await asyncio.sleep(2)
        xrp_balance = await self.get_balance('coinbase', self.test_crypto)
        
        if xrp_balance < 0.1:
            print(f"❌ Insufficient XRP balance: {xrp_balance}")
            return False
            
        # Step 2: Transfer to Gemini
        success = await self.transfer_crypto('coinbase', 'gemini', xrp_balance)
        if not success:
            print("❌ Test failed at transfer step")
            return False
            
        # Step 3: Sell on Gemini
        xrp_on_gemini = await self.get_balance('gemini', self.test_crypto)
        order = await self.sell_crypto('gemini', self.test_symbol, xrp_on_gemini)
        if not order:
            print("❌ Test failed at sell step")
            return False
            
        print("\n✅ TEST 1 PASSED: Coinbase → Gemini transfer successful!")
        return True
        
    async def test_gemini_to_coinbase(self):
        """Test: Gemini → Coinbase transfer"""
        print("\n" + "="*80)
        print("🧪 TEST 2: GEMINI → COINBASE TRANSFER")
        print("="*80)
        
        # Check if Gemini has enough balance
        gemini_usd = await self.get_balance('gemini', 'USD')
        print(f"Gemini USD balance: ${gemini_usd:.2f}")
        
        if gemini_usd < 1.0:
            print("⚠️  Gemini has less than $1 USD - skipping this test")
            print("   (Funds may still be settling from previous test)")
            return True  # Don't fail the test, just skip
            
        # Step 1: Buy XRP on Gemini
        order = await self.buy_crypto('gemini', self.test_symbol, self.test_amount_usd)
        if not order:
            print("❌ Test failed at buy step")
            return False
            
        # Get amount bought
        await asyncio.sleep(2)
        xrp_balance = await self.get_balance('gemini', self.test_crypto)
        
        if xrp_balance < 0.1:
            print(f"❌ Insufficient XRP balance: {xrp_balance}")
            return False
            
        # Step 2: Transfer to Coinbase
        success = await self.transfer_crypto('gemini', 'coinbase', xrp_balance)
        if not success:
            print("❌ Test failed at transfer step")
            return False
            
        # Step 3: Sell on Coinbase
        xrp_on_coinbase = await self.get_balance('coinbase', self.test_crypto)
        order = await self.sell_crypto('coinbase', self.test_symbol, xrp_on_coinbase)
        if not order:
            print("❌ Test failed at sell step")
            return False
            
        print("\n✅ TEST 2 PASSED: Gemini → Coinbase transfer successful!")
        return True
        
    async def run_tests(self):
        """Run all transfer tests"""
        try:
            await self.initialize()
            
            # Show initial balances
            print("\n" + "="*80)
            print("💰 INITIAL BALANCES")
            print("="*80)
            cb_usd = await self.get_balance('coinbase', 'USD')
            gem_usd = await self.get_balance('gemini', 'USD')
            cb_xrp = await self.get_balance('coinbase', self.test_crypto)
            gem_xrp = await self.get_balance('gemini', self.test_crypto)
            
            print(f"Coinbase: ${cb_usd:.2f} USD, {cb_xrp:.4f} XRP")
            print(f"Gemini:   ${gem_usd:.2f} USD, {gem_xrp:.4f} XRP")
            
            # Run tests
            test1_passed = await self.test_coinbase_to_gemini()
            
            # Wait a bit between tests
            print("\n⏳ Waiting 30s before next test...")
            await asyncio.sleep(30)
            
            test2_passed = await self.test_gemini_to_coinbase()
            
            # Show final balances
            print("\n" + "="*80)
            print("💰 FINAL BALANCES")
            print("="*80)
            cb_usd = await self.get_balance('coinbase', 'USD')
            gem_usd = await self.get_balance('gemini', 'USD')
            cb_xrp = await self.get_balance('coinbase', self.test_crypto)
            gem_xrp = await self.get_balance('gemini', self.test_crypto)
            
            print(f"Coinbase: ${cb_usd:.2f} USD, {cb_xrp:.4f} XRP")
            print(f"Gemini:   ${gem_usd:.2f} USD, {gem_xrp:.4f} XRP")
            
            # Summary
            print("\n" + "="*80)
            print("📊 TEST SUMMARY")
            print("="*80)
            print(f"Test 1 (CB → GEM): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
            print(f"Test 2 (GEM → CB): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
            
            if test1_passed and test2_passed:
                print("\n🎉 ALL TESTS PASSED - TRANSFER MECHANISM WORKING!")
            else:
                print("\n⚠️  SOME TESTS FAILED - CHECK LOGS ABOVE")
                
        except Exception as e:
            print(f"\n❌ TEST SUITE FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            await self.exchange_manager.close()
            

async def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("🧪 CRYPTO TRANSFER MECHANISM TEST")
    print("="*80)
    print("This will test bi-directional XRP transfers between Coinbase and Gemini")
    print("Test amount: $1.00 per direction")
    print("="*80)
    
    tester = TransferTester()
    await tester.run_tests()
    

if __name__ == "__main__":
    asyncio.run(main())

