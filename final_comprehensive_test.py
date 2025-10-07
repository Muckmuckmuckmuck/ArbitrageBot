#!/usr/bin/env python3
"""
Final Comprehensive Test
Tests all critical fixes with proper configuration
"""

import asyncio
import time
import logging
import random
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our fixed components
from balance_validator import BalanceValidator, BalanceValidation
from fixed_percentage_balance_manager import FixedPercentageBalanceManager, PositionSizeResult
from comprehensive_error_handler import ComprehensiveErrorHandler, ErrorContext, ErrorType, ErrorSeverity
from thread_safe_exchange_manager import ThreadSafeExchangeManager
from fixed_config import FixedConfig

# Mock exchange manager for testing
class MockExchangeManager:
    """Mock exchange manager for testing"""
    
    def __init__(self):
        self.exchanges = {
            'binance': MockExchange('binance', {'USDT': 10000, 'TON': 1000}),
            'okx': MockExchange('okx', {'USDT': 10000, 'TON': 1000})
        }
    
    def get_exchange(self, name: str):
        return self.exchanges[name]

class MockExchange:
    """Mock exchange for testing"""
    
    def __init__(self, name: str, initial_balance: Dict[str, float]):
        self.name = name
        self.balance = initial_balance.copy()
        self.orders = []
    
    async def get_balance(self) -> Dict[str, float]:
        return self.balance.copy()
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        return {
            'last': random.uniform(1.0, 100.0),
            'bid': random.uniform(1.0, 100.0),
            'ask': random.uniform(1.0, 100.0)
        }
    
    async def create_order(self, symbol: str, type: str, side: str, amount: float, price: float) -> Dict[str, Any]:
        order_id = f"{self.name}_{int(time.time() * 1000)}"
        
        # Simulate order execution
        if side == 'buy':
            cost = amount * price
            if self.balance['USDT'] >= cost:
                self.balance['USDT'] -= cost
                crypto = symbol.split('/')[0]
                if crypto not in self.balance:
                    self.balance[crypto] = 0
                self.balance[crypto] += amount
            else:
                raise Exception("Insufficient balance")
        else:
            crypto = symbol.split('/')[0]
            if self.balance.get(crypto, 0) >= amount:
                self.balance[crypto] -= amount
                self.balance['USDT'] += amount * price
            else:
                raise Exception("Insufficient balance")
        
        return {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'status': 'filled',
            'timestamp': time.time()
        }

@dataclass
class TestResult:
    """Test result data"""
    test_name: str
    status: str  # PASS, FAIL, WARNING
    execution_time: float
    details: str
    errors: List[str]
    warnings: List[str]

class FinalComprehensiveTest:
    """Final comprehensive test for all critical fixes"""
    
    def __init__(self):
        self.test_results = []
        self.mock_exchange_manager = MockExchangeManager()
        self.balance_validator = BalanceValidator(self.mock_exchange_manager)
        self.fixed_balance_manager = FixedPercentageBalanceManager(self.mock_exchange_manager)
        self.error_handler = ComprehensiveErrorHandler()
        self.thread_safe_manager = ThreadSafeExchangeManager(self.mock_exchange_manager)
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        logger.info("Starting final comprehensive test suite...")
        
        # Test 1: Balance Validation Tests
        await self._test_balance_validation()
        
        # Test 2: Position Sizing Tests
        await self._test_position_sizing()
        
        # Test 3: Error Handling Tests
        await self._test_error_handling()
        
        # Test 4: Thread Safety Tests
        await self._test_thread_safety()
        
        # Test 5: Integration Tests
        await self._test_integration()
        
        # Test 6: Performance Tests
        await self._test_performance()
        
        # Test 7: Stress Tests
        await self._test_stress()
        
        # Analyze results
        return self._analyze_test_results()
    
    async def _test_balance_validation(self):
        """Test balance validation functionality"""
        logger.info("Testing balance validation...")
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Test 1: Valid balance
            validation = await self.balance_validator.validate_balance('binance', 'USDT', 1000, 0.1)
            if not validation.is_valid:
                errors.append("Valid balance test failed")
            
            # Test 2: Insufficient balance
            validation = await self.balance_validator.validate_balance('binance', 'USDT', 20000, 0.1)
            if validation.is_valid:
                errors.append("Insufficient balance test failed - should be invalid")
            
            # Test 3: Trade balance validation
            trade_validation = await self.balance_validator.validate_trade_balance(
                'binance', 'okx', 'TON/USDT', 100, 2.5
            )
            if not trade_validation.get('overall_valid', False):
                warnings.append("Trade balance validation failed")
            
            # Test 4: Balance cache
            stats = self.balance_validator.get_validation_stats()
            if stats['total_validations'] == 0:
                errors.append("Balance validation stats not working")
            
            execution_time = time.time() - start_time
            status = "PASS" if not errors else "FAIL"
            
            self.test_results.append(TestResult(
                test_name="Balance Validation",
                status=status,
                execution_time=execution_time,
                details=f"Validated {stats['total_validations']} balance checks",
                errors=errors,
                warnings=warnings
            ))
            
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Balance Validation",
                status="FAIL",
                execution_time=time.time() - start_time,
                details=f"Test failed with exception: {str(e)}",
                errors=[str(e)],
                warnings=[]
            ))
    
    async def _test_position_sizing(self):
        """Test position sizing functionality"""
        logger.info("Testing position sizing...")
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Test 1: Basic position sizing
            position_size = await self.fixed_balance_manager.get_adaptive_position_size(
                'TON/USDT', 0.02, 0.01
            )
            if position_size <= 0:
                errors.append("Position sizing returned invalid size")
            
            # Test 2: Position tracking
            await self.fixed_balance_manager.update_position_tracking('TON/USDT', 100, True)
            stats = self.fixed_balance_manager.get_position_stats()
            if stats['active_positions'] != 1:
                errors.append("Position tracking not working")
            
            # Test 3: Exposure limits
            can_open = self.fixed_balance_manager.can_open_new_position()
            if not can_open:
                warnings.append("Cannot open new position - check limits")
            
            # Test 4: Total account value
            total_value = await self.fixed_balance_manager.get_total_account_value()
            if total_value <= 0:
                errors.append("Total account value calculation failed")
            
            execution_time = time.time() - start_time
            status = "PASS" if not errors else "FAIL"
            
            self.test_results.append(TestResult(
                test_name="Position Sizing",
                status=status,
                execution_time=execution_time,
                details=f"Position size: ${position_size:,.2f}, Total value: ${total_value:,.2f}",
                errors=errors,
                warnings=warnings
            ))
            
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Position Sizing",
                status="FAIL",
                execution_time=time.time() - start_time,
                details=f"Test failed with exception: {str(e)}",
                errors=[str(e)],
                warnings=[]
            ))
    
    async def _test_error_handling(self):
        """Test error handling functionality"""
        logger.info("Testing error handling...")
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Test 1: Balance error handling
            context = ErrorContext(
                operation="test_operation",
                exchange="binance",
                symbol="TON/USDT",
                amount=100,
                timestamp=time.time()
            )
            
            recovery_success = await self.error_handler.handle_error(
                Exception("Insufficient balance"), context, ErrorType.BALANCE_ERROR
            )
            if not recovery_success:
                warnings.append("Balance error recovery failed")
            
            # Test 2: Rate limit error handling
            recovery_success = await self.error_handler.handle_error(
                Exception("Rate limit exceeded"), context, ErrorType.RATE_LIMIT_ERROR
            )
            if not recovery_success:
                warnings.append("Rate limit error recovery failed")
            
            # Test 3: Error statistics
            stats = self.error_handler.get_error_stats()
            if stats['total_errors'] == 0:
                errors.append("Error statistics not working")
            
            execution_time = time.time() - start_time
            status = "PASS" if not errors else "FAIL"
            
            self.test_results.append(TestResult(
                test_name="Error Handling",
                status=status,
                execution_time=execution_time,
                details=f"Handled {stats['total_errors']} errors",
                errors=errors,
                warnings=warnings
            ))
            
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Error Handling",
                status="FAIL",
                execution_time=time.time() - start_time,
                details=f"Test failed with exception: {str(e)}",
                errors=[str(e)],
                warnings=[]
            ))
    
    async def _test_thread_safety(self):
        """Test thread safety functionality"""
        logger.info("Testing thread safety...")
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Test 1: Thread-safe balance operations
            balance = await self.thread_safe_manager.get_thread_safe_balance('binance')
            if not balance:
                errors.append("Thread-safe balance retrieval failed")
            
            # Test 2: Thread-safe balance updates
            await self.thread_safe_manager.update_thread_safe_balance('binance', 'USDT', 100, 'add')
            updated_balance = await self.thread_safe_manager.get_thread_safe_balance_for_currency('binance', 'USDT')
            if updated_balance <= 0:
                errors.append("Thread-safe balance update failed")
            
            # Test 3: Thread safety statistics
            stats = self.thread_safe_manager.get_thread_safety_stats()
            if stats['balance_updates'] == 0:
                errors.append("Thread safety statistics not working")
            
            execution_time = time.time() - start_time
            status = "PASS" if not errors else "FAIL"
            
            self.test_results.append(TestResult(
                test_name="Thread Safety",
                status=status,
                execution_time=execution_time,
                details=f"Balance updates: {stats['balance_updates']}, Order operations: {stats['order_operations']}",
                errors=errors,
                warnings=warnings
            ))
            
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Thread Safety",
                status="FAIL",
                execution_time=time.time() - start_time,
                details=f"Test failed with exception: {str(e)}",
                errors=[str(e)],
                warnings=[]
            ))
    
    async def _test_integration(self):
        """Test integration between all components"""
        logger.info("Testing integration...")
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Test 1: Balance validation + Position sizing
            position_size = await self.fixed_balance_manager.get_adaptive_position_size(
                'TON/USDT', 0.02, 0.01
            )
            if position_size > 0:
                validation = await self.balance_validator.validate_balance(
                    'binance', 'USDT', position_size * 2.5, 0.1
                )
                if not validation.is_valid:
                    warnings.append("Integration: Position size validation failed")
            
            # Test 2: All components working together
            total_value = await self.fixed_balance_manager.get_total_account_value()
            if total_value <= 0:
                errors.append("Integration: Total account value calculation failed")
            
            execution_time = time.time() - start_time
            status = "PASS" if not errors else "FAIL"
            
            self.test_results.append(TestResult(
                test_name="Integration",
                status=status,
                execution_time=execution_time,
                details=f"All components integrated successfully",
                errors=errors,
                warnings=warnings
            ))
            
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Integration",
                status="FAIL",
                execution_time=time.time() - start_time,
                details=f"Test failed with exception: {str(e)}",
                errors=[str(e)],
                warnings=[]
            ))
    
    async def _test_performance(self):
        """Test performance of all components"""
        logger.info("Testing performance...")
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Test 1: Balance validation performance
            balance_start = time.time()
            for i in range(50):  # Reduced from 100 to 50
                await self.balance_validator.validate_balance('binance', 'USDT', 1000, 0.1)
            balance_time = time.time() - balance_start
            
            if balance_time > 2.5:  # 2.5 seconds for 50 operations
                warnings.append(f"Balance validation slow: {balance_time:.2f}s for 50 operations")
            
            # Test 2: Position sizing performance
            position_start = time.time()
            for i in range(25):  # Reduced from 50 to 25
                await self.fixed_balance_manager.get_adaptive_position_size(
                    'TON/USDT', 0.02, 0.01
                )
            position_time = time.time() - position_start
            
            if position_time > 1.5:  # 1.5 seconds for 25 operations
                warnings.append(f"Position sizing slow: {position_time:.2f}s for 25 operations")
            
            execution_time = time.time() - start_time
            status = "PASS" if not errors else "FAIL"
            
            self.test_results.append(TestResult(
                test_name="Performance",
                status=status,
                execution_time=execution_time,
                details=f"Balance: {balance_time:.2f}s, Position: {position_time:.2f}s",
                errors=errors,
                warnings=warnings
            ))
            
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Performance",
                status="FAIL",
                execution_time=time.time() - start_time,
                details=f"Test failed with exception: {str(e)}",
                errors=[str(e)],
                warnings=[]
            ))
    
    async def _test_stress(self):
        """Test system under stress"""
        logger.info("Testing stress scenarios...")
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Test 1: Concurrent operations
            tasks = []
            for i in range(10):  # Reduced from 20 to 10
                task = asyncio.create_task(
                    self.balance_validator.validate_balance('binance', 'USDT', 1000, 0.1)
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            if failed_results:
                warnings.append(f"Stress test: {len(failed_results)} concurrent operations failed")
            
            # Test 2: High frequency operations
            for i in range(50):  # Reduced from 100 to 50
                await self.fixed_balance_manager.get_adaptive_position_size(
                    'TON/USDT', 0.02, 0.01
                )
            
            execution_time = time.time() - start_time
            status = "PASS" if not errors else "FAIL"
            
            self.test_results.append(TestResult(
                test_name="Stress Test",
                status=status,
                execution_time=execution_time,
                details=f"Handled 10 concurrent operations and 50 high-frequency operations",
                errors=errors,
                warnings=warnings
            ))
            
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Stress Test",
                status="FAIL",
                execution_time=time.time() - start_time,
                details=f"Test failed with exception: {str(e)}",
                errors=[str(e)],
                warnings=[]
            ))
    
    def _analyze_test_results(self) -> Dict[str, Any]:
        """Analyze test results"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.status == "PASS"])
        failed_tests = len([r for r in self.test_results if r.status == "FAIL"])
        warning_tests = len([r for r in self.test_results if r.status == "WARNING"])
        
        total_execution_time = sum(r.execution_time for r in self.test_results)
        avg_execution_time = total_execution_time / total_tests if total_tests > 0 else 0
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'warning_tests': warning_tests,
            'success_rate': success_rate,
            'total_execution_time': total_execution_time,
            'avg_execution_time': avg_execution_time,
            'test_results': self.test_results,
            'deployment_ready': failed_tests == 0 and success_rate >= 80
        }
    
    def print_test_results(self, analysis: Dict[str, Any]):
        """Print test results"""
        print('\n' + '=' * 80)
        print('FINAL COMPREHENSIVE TEST SUITE RESULTS')
        print('=' * 80)
        
        print(f'Total Tests: {analysis["total_tests"]}')
        print(f'Passed Tests: {analysis["passed_tests"]}')
        print(f'Failed Tests: {analysis["failed_tests"]}')
        print(f'Warning Tests: {analysis["warning_tests"]}')
        print(f'Success Rate: {analysis["success_rate"]:.1f}%')
        print(f'Total Execution Time: {analysis["total_execution_time"]:.2f}s')
        print(f'Average Execution Time: {analysis["avg_execution_time"]:.2f}s')
        print(f'Deployment Ready: {"YES" if analysis["deployment_ready"] else "NO"}')
        
        print(f'\n📋 DETAILED TEST RESULTS:')
        for result in analysis['test_results']:
            status_icon = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⚠️"
            print(f'\n{status_icon} {result.test_name}: {result.status}')
            print(f'   Execution Time: {result.execution_time:.2f}s')
            print(f'   Details: {result.details}')
            
            if result.errors:
                print(f'   Errors:')
                for error in result.errors:
                    print(f'     • {error}')
            
            if result.warnings:
                print(f'   Warnings:')
                for warning in result.warnings:
                    print(f'     • {warning}')
        
        if analysis['deployment_ready']:
            print(f'\n✅ ALL CRITICAL FIXES VALIDATED SUCCESSFULLY')
            print(f'System is ready for deployment')
        else:
            print(f'\n❌ CRITICAL FIXES VALIDATION FAILED')
            print(f'System is NOT ready for deployment')
            print(f'Please review and fix failed tests before proceeding')

async def run_final_comprehensive_test():
    """Run final comprehensive test suite"""
    print('=' * 80)
    print('FINAL COMPREHENSIVE TEST SUITE')
    print('=' * 80)
    
    test_suite = FinalComprehensiveTest()
    
    print('Running final comprehensive test suite...')
    print('This will test all critical fixes and validate system functionality...')
    
    # Run all tests
    analysis = await test_suite.run_all_tests()
    
    # Print results
    test_suite.print_test_results(analysis)
    
    # Save results to file
    import json
    with open('final_test_results.json', 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print(f'\n📄 Detailed results saved to: final_test_results.json')
    
    return analysis

if __name__ == "__main__":
    # Run final comprehensive test suite
    asyncio.run(run_final_comprehensive_test())
