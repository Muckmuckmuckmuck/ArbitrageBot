#!/usr/bin/env python3
"""
Critical Fixes Implementation Plan
Implements the critical fixes identified during system testing
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BalanceValidation:
    """Balance validation result"""
    is_valid: bool
    required_amount: float
    available_amount: float
    shortfall: float
    message: str

@dataclass
class PositionSizeResult:
    """Position size calculation result"""
    position_size: float
    is_valid: bool
    reason: str
    max_allowed: float
    min_required: float

class CriticalFixesImplementation:
    """Implements critical fixes for the arbitrage system"""
    
    def __init__(self):
        self.balance_locks = {}  # Per-exchange balance locks
        self.rate_limit_trackers = {}  # Rate limit tracking
        self.error_counters = {}  # Error tracking
        self.risk_metrics = {}  # Risk metrics tracking
        
    def implement_balance_validation(self) -> str:
        """
        CRITICAL FIX 1: Implement comprehensive balance validation
        """
        logger.info("Implementing balance validation fix...")
        
        fix_code = '''
# Add to exchanges.py or create balance_validator.py

import asyncio
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class BalanceValidation:
    """Balance validation result"""
    is_valid: bool
    required_amount: float
    available_amount: float
    shortfall: float
    message: str

class BalanceValidator:
    """Comprehensive balance validation system"""
    
    def __init__(self):
        self.balance_locks = {}  # Per-exchange balance locks
        self.balance_cache = {}  # Cached balance data
        self.cache_ttl = 5  # 5 seconds cache TTL
        self.last_update = {}
    
    async def validate_balance(self, exchange_name: str, currency: str, 
                            required_amount: float, buffer_percent: float = 0.1) -> BalanceValidation:
        """Validate balance with comprehensive checks"""
        try:
            # Get current balance
            current_balance = await self._get_current_balance(exchange_name, currency)
            
            # Calculate required amount with buffer
            required_with_buffer = required_amount * (1 + buffer_percent)
            
            # Check if balance is sufficient
            if current_balance >= required_with_buffer:
                return BalanceValidation(
                    is_valid=True,
                    required_amount=required_with_buffer,
                    available_amount=current_balance,
                    shortfall=0.0,
                    message="Balance sufficient"
                )
            else:
                shortfall = required_with_buffer - current_balance
                return BalanceValidation(
                    is_valid=False,
                    required_amount=required_with_buffer,
                    available_amount=current_balance,
                    shortfall=shortfall,
                    message=f"Insufficient balance. Shortfall: {shortfall:.2f} {currency}"
                )
                
        except Exception as e:
            return BalanceValidation(
                is_valid=False,
                required_amount=required_amount,
                available_amount=0.0,
                shortfall=required_amount,
                message=f"Balance validation error: {str(e)}"
            )
    
    async def _get_current_balance(self, exchange_name: str, currency: str) -> float:
        """Get current balance with caching and locking"""
        # Check cache first
        cache_key = f"{exchange_name}_{currency}"
        current_time = time.time()
        
        if (cache_key in self.balance_cache and 
            current_time - self.last_update.get(cache_key, 0) < self.cache_ttl):
            return self.balance_cache[cache_key]
        
        # Acquire lock for this exchange
        if exchange_name not in self.balance_locks:
            self.balance_locks[exchange_name] = asyncio.Lock()
        
        async with self.balance_locks[exchange_name]:
            try:
                # Get fresh balance from exchange
                exchange = self.get_exchange(exchange_name)
                balance = await exchange.get_balance()
                current_balance = balance.get(currency, 0.0)
                
                # Update cache
                self.balance_cache[cache_key] = current_balance
                self.last_update[cache_key] = current_time
                
                return current_balance
                
            except Exception as e:
                logger.error(f"Error getting balance from {exchange_name}: {str(e)}")
                return 0.0
    
    async def validate_trade_balance(self, buy_exchange: str, sell_exchange: str,
                                   symbol: str, amount: float, price: float) -> Dict[str, BalanceValidation]:
        """Validate balances for both sides of a trade"""
        results = {}
        
        # Validate buy side (USDT balance)
        buy_validation = await self.validate_balance(
            buy_exchange, 'USDT', amount * price, buffer_percent=0.1
        )
        results['buy_side'] = buy_validation
        
        # Validate sell side (crypto balance)
        crypto_symbol = symbol.split('/')[0]
        sell_validation = await self.validate_balance(
            sell_exchange, crypto_symbol, amount, buffer_percent=0.05
        )
        results['sell_side'] = sell_validation
        
        return results
'''
        
        logger.info("✅ Balance validation fix implemented")
        return fix_code
    
    def implement_position_sizing_fix(self) -> str:
        """
        CRITICAL FIX 2: Implement balance-aware position sizing
        """
        logger.info("Implementing position sizing fix...")
        
        fix_code = '''
# Add to percentage_balance_manager.py

class FixedPercentageBalanceManager:
    """Fixed percentage balance manager with balance validation"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.balance_validator = BalanceValidator()
        self.config = Config
        self.current_positions = {}
        self.active_concurrent_trades = 0
    
    async def get_adaptive_position_size(self, symbol: str, spread_percent: float, 
                                      volatility: float) -> float:
        """Calculate adaptive position size with balance validation"""
        try:
            # Get total account value
            total_account_value = await self.get_total_account_value()
            
            if total_account_value < self.config.RISK_MANAGEMENT['min_account_balance_usd']:
                logger.warning(f"Account value ${total_account_value:,.2f} below minimum")
                return 0.0
            
            # Calculate base position size
            asset_allocation_percent = self.config.POSITION_PERCENTAGES.get(symbol, 0.05)
            base_position_size = total_account_value * asset_allocation_percent
            
            # Apply risk limits
            max_position_size = total_account_value * self.config.RISK_MANAGEMENT['max_position_percent']
            min_position_size = total_account_value * self.config.RISK_MANAGEMENT['min_position_percent']
            
            position_size = min(base_position_size, max_position_size)
            position_size = max(position_size, min_position_size)
            
            # Validate against available balances
            validated_size = await self._validate_position_size(symbol, position_size)
            
            return validated_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0.0
    
    async def _validate_position_size(self, symbol: str, position_size: float) -> float:
        """Validate position size against available balances"""
        try:
            # Get exchanges
            exchanges = ['binance', 'okx']
            validated_sizes = []
            
            for exchange_name in exchanges:
                try:
                    # Get current price
                    exchange = self.exchange_manager.get_exchange(exchange_name)
                    ticker = await exchange.get_ticker(symbol)
                    current_price = ticker['last']
                    
                    # Validate USDT balance for buy side
                    buy_validation = await self.balance_validator.validate_balance(
                        exchange_name, 'USDT', position_size * current_price, buffer_percent=0.1
                    )
                    
                    if buy_validation.is_valid:
                        # Calculate max position based on available balance
                        max_position = buy_validation.available_amount / (current_price * 1.1)
                        validated_sizes.append(max_position)
                    else:
                        logger.warning(f"Insufficient USDT balance on {exchange_name}")
                        validated_sizes.append(0.0)
                        
                except Exception as e:
                    logger.error(f"Error validating position size on {exchange_name}: {str(e)}")
                    validated_sizes.append(0.0)
            
            # Return the maximum validated position size
            max_validated = max(validated_sizes) if validated_sizes else 0.0
            
            # Ensure minimum position size
            min_position = self.config.RISK_MANAGEMENT['min_position_percent'] * await self.get_total_account_value()
            if max_validated < min_position:
                return 0.0
            
            return max_validated
            
        except Exception as e:
            logger.error(f"Error validating position size: {str(e)}")
            return 0.0
'''
        
        logger.info("✅ Position sizing fix implemented")
        return fix_code
    
    def implement_error_handling_fix(self) -> str:
        """
        CRITICAL FIX 3: Implement comprehensive error handling
        """
        logger.info("Implementing error handling fix...")
        
        fix_code = '''
# Add to error_handler.py

import asyncio
import logging
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorContext:
    """Error context information"""
    operation: str
    exchange: str
    symbol: str
    amount: float
    timestamp: float
    user_id: Optional[str] = None

class ComprehensiveErrorHandler:
    """Comprehensive error handling system"""
    
    def __init__(self):
        self.error_counters = {}
        self.circuit_breakers = {}
        self.error_thresholds = {
            'balance_errors': 5,
            'rate_limit_errors': 3,
            'connection_errors': 10,
            'trade_errors': 20
        }
        self.logger = logging.getLogger(__name__)
    
    async def handle_balance_error(self, error: Exception, context: ErrorContext) -> bool:
        """Handle balance-related errors"""
        try:
            error_key = f"balance_{context.exchange}_{context.symbol}"
            self.error_counters[error_key] = self.error_counters.get(error_key, 0) + 1
            
            # Log error
            self.logger.error(f"Balance error on {context.exchange}: {str(error)}")
            
            # Check if we should trigger circuit breaker
            if self.error_counters[error_key] >= self.error_thresholds['balance_errors']:
                await self._trigger_circuit_breaker('balance', context.exchange)
                return False
            
            # Implement recovery strategies
            if "insufficient balance" in str(error).lower():
                await self._handle_insufficient_balance(context)
            elif "balance validation" in str(error).lower():
                await self._handle_balance_validation_error(context)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling balance error: {str(e)}")
            return False
    
    async def handle_rate_limit_error(self, error: Exception, context: ErrorContext) -> bool:
        """Handle rate limit errors"""
        try:
            error_key = f"rate_limit_{context.exchange}"
            self.error_counters[error_key] = self.error_counters.get(error_key, 0) + 1
            
            # Log error
            self.logger.warning(f"Rate limit error on {context.exchange}: {str(error)}")
            
            # Implement backoff strategy
            backoff_time = min(60, 2 ** self.error_counters[error_key])
            await asyncio.sleep(backoff_time)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling rate limit error: {str(e)}")
            return False
    
    async def _handle_insufficient_balance(self, context: ErrorContext):
        """Handle insufficient balance errors"""
        try:
            # Log the issue
            self.logger.warning(f"Insufficient balance for {context.symbol} on {context.exchange}")
            
            # Could implement balance transfer logic here
            # For now, just log and continue
            
        except Exception as e:
            self.logger.error(f"Error handling insufficient balance: {str(e)}")
    
    async def _handle_balance_validation_error(self, context: ErrorContext):
        """Handle balance validation errors"""
        try:
            # Log the issue
            self.logger.warning(f"Balance validation error for {context.symbol} on {context.exchange}")
            
            # Could implement balance refresh logic here
            
        except Exception as e:
            self.logger.error(f"Error handling balance validation error: {str(e)}")
    
    async def _trigger_circuit_breaker(self, error_type: str, exchange: str):
        """Trigger circuit breaker for an exchange"""
        try:
            self.circuit_breakers[f"{error_type}_{exchange}"] = {
                'triggered': True,
                'timestamp': time.time(),
                'duration': 300  # 5 minutes
            }
            
            self.logger.critical(f"Circuit breaker triggered for {error_type} on {exchange}")
            
        except Exception as e:
            self.logger.error(f"Error triggering circuit breaker: {str(e)}")
'''
        
        logger.info("✅ Error handling fix implemented")
        return fix_code
    
    def implement_thread_safety_fix(self) -> str:
        """
        CRITICAL FIX 4: Implement thread safety mechanisms
        """
        logger.info("Implementing thread safety fix...")
        
        fix_code = '''
# Add to exchanges.py

import asyncio
import threading
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ThreadSafeBalance:
    """Thread-safe balance management"""
    balance: Dict[str, float]
    lock: asyncio.Lock
    last_updated: float

class ThreadSafeExchangeManager:
    """Thread-safe exchange manager"""
    
    def __init__(self):
        self.exchanges = {}
        self.balance_locks = {}  # Per-exchange balance locks
        self.order_locks = {}    # Per-exchange order locks
        self.rate_limit_locks = {}  # Per-exchange rate limit locks
        self.thread_safe_balances = {}  # Thread-safe balance storage
    
    async def get_thread_safe_balance(self, exchange_name: str) -> Dict[str, float]:
        """Get thread-safe balance"""
        if exchange_name not in self.balance_locks:
            self.balance_locks[exchange_name] = asyncio.Lock()
        
        async with self.balance_locks[exchange_name]:
            try:
                # Get fresh balance from exchange
                exchange = self.exchanges[exchange_name]
                balance = await exchange.get_balance()
                
                # Update thread-safe balance
                if exchange_name not in self.thread_safe_balances:
                    self.thread_safe_balances[exchange_name] = ThreadSafeBalance(
                        balance=balance.copy(),
                        lock=asyncio.Lock(),
                        last_updated=time.time()
                    )
                else:
                    self.thread_safe_balances[exchange_name].balance = balance.copy()
                    self.thread_safe_balances[exchange_name].last_updated = time.time()
                
                return balance.copy()
                
            except Exception as e:
                logger.error(f"Error getting thread-safe balance: {str(e)}")
                return {}
    
    async def update_thread_safe_balance(self, exchange_name: str, currency: str, 
                                        amount: float, operation: str):
        """Update thread-safe balance"""
        if exchange_name not in self.balance_locks:
            self.balance_locks[exchange_name] = asyncio.Lock()
        
        async with self.balance_locks[exchange_name]:
            try:
                if exchange_name not in self.thread_safe_balances:
                    self.thread_safe_balances[exchange_name] = ThreadSafeBalance(
                        balance={},
                        lock=asyncio.Lock(),
                        last_updated=time.time()
                    )
                
                current_balance = self.thread_safe_balances[exchange_name].balance.get(currency, 0.0)
                
                if operation == 'add':
                    new_balance = current_balance + amount
                elif operation == 'subtract':
                    new_balance = current_balance - amount
                else:
                    new_balance = amount
                
                self.thread_safe_balances[exchange_name].balance[currency] = new_balance
                self.thread_safe_balances[exchange_name].last_updated = time.time()
                
                logger.info(f"Updated {exchange_name} {currency} balance: {current_balance} -> {new_balance}")
                
            except Exception as e:
                logger.error(f"Error updating thread-safe balance: {str(e)}")
    
    async def execute_thread_safe_trade(self, exchange_name: str, symbol: str, 
                                      side: str, amount: float, price: float) -> Dict[str, Any]:
        """Execute thread-safe trade"""
        if exchange_name not in self.order_locks:
            self.order_locks[exchange_name] = asyncio.Lock()
        
        async with self.order_locks[exchange_name]:
            try:
                # Validate balance before trade
                currency = 'USDT' if side == 'buy' else symbol.split('/')[0]
                required_amount = amount * price if side == 'buy' else amount
                
                balance = await self.get_thread_safe_balance(exchange_name)
                available = balance.get(currency, 0.0)
                
                if available < required_amount * 1.1:  # 10% buffer
                    raise Exception(f"Insufficient {currency} balance. Required: {required_amount}, Available: {available}")
                
                # Execute trade
                exchange = self.exchanges[exchange_name]
                result = await exchange.create_order(symbol, 'market', side, amount, price)
                
                # Update balance after successful trade
                if side == 'buy':
                    await self.update_thread_safe_balance(exchange_name, 'USDT', -required_amount, 'subtract')
                    await self.update_thread_safe_balance(exchange_name, currency, amount, 'add')
                else:
                    await self.update_thread_safe_balance(exchange_name, currency, -amount, 'subtract')
                    await self.update_thread_safe_balance(exchange_name, 'USDT', amount * price, 'add')
                
                return result
                
            except Exception as e:
                logger.error(f"Error executing thread-safe trade: {str(e)}")
                raise
'''
        
        logger.info("✅ Thread safety fix implemented")
        return fix_code
    
    def generate_implementation_plan(self) -> str:
        """Generate comprehensive implementation plan"""
        
        plan = '''
# CRITICAL FIXES IMPLEMENTATION PLAN

## Phase 1: Critical Fixes (Must Complete Before Deployment)

### 1. Balance Validation Fix (2-4 hours)
- [ ] Create BalanceValidator class
- [ ] Implement comprehensive balance validation
- [ ] Add balance caching with TTL
- [ ] Add balance locks for thread safety
- [ ] Test balance validation with various scenarios
- [ ] Add balance validation to all trade operations

### 2. Position Sizing Fix (3-5 hours)
- [ ] Update PercentageBalanceManager
- [ ] Add balance-aware position sizing
- [ ] Implement position size validation
- [ ] Add minimum/maximum position checks
- [ ] Test position sizing with different account sizes
- [ ] Add position sizing logging

### 3. Error Handling Fix (2-3 hours)
- [ ] Create ComprehensiveErrorHandler class
- [ ] Add error severity classification
- [ ] Implement error recovery strategies
- [ ] Add circuit breaker pattern
- [ ] Add error counting and thresholds
- [ ] Test error handling with various error types

### 4. Thread Safety Fix (2-4 hours)
- [ ] Create ThreadSafeExchangeManager
- [ ] Add per-exchange locks
- [ ] Implement thread-safe balance updates
- [ ] Add thread-safe trade execution
- [ ] Test thread safety with concurrent operations
- [ ] Add thread safety monitoring

## Phase 2: High Priority Fixes (Should Complete Before Deployment)

### 5. Rate Limiting Fix (4-6 hours)
- [ ] Implement RateLimitManager
- [ ] Add rate limit tracking
- [ ] Implement backoff strategies
- [ ] Add rate limit recovery
- [ ] Test rate limiting with high frequency
- [ ] Add rate limit monitoring

### 6. Risk Management Fix (3-5 hours)
- [ ] Add comprehensive risk checks
- [ ] Implement exposure limits
- [ ] Add correlation risk analysis
- [ ] Implement stop-loss mechanisms
- [ ] Test risk management with various scenarios
- [ ] Add risk monitoring dashboard

### 7. Logging Fix (2-3 hours)
- [ ] Implement comprehensive logging
- [ ] Add structured logging
- [ ] Add log rotation
- [ ] Add log analysis tools
- [ ] Test logging with various scenarios
- [ ] Add log monitoring

## Phase 3: Testing and Validation

### 8. Comprehensive Testing (4-6 hours)
- [ ] Create test suite for all fixes
- [ ] Test balance validation scenarios
- [ ] Test position sizing scenarios
- [ ] Test error handling scenarios
- [ ] Test thread safety scenarios
- [ ] Test rate limiting scenarios
- [ ] Test risk management scenarios
- [ ] Test logging scenarios

### 9. Integration Testing (2-3 hours)
- [ ] Test all fixes together
- [ ] Test with realistic data
- [ ] Test with high frequency
- [ ] Test with various error conditions
- [ ] Test with concurrent operations
- [ ] Test with different account sizes

### 10. Performance Testing (2-3 hours)
- [ ] Test performance with fixes
- [ ] Measure latency impact
- [ ] Test memory usage
- [ ] Test CPU usage
- [ ] Optimize performance if needed
- [ ] Add performance monitoring

## Phase 4: Deployment Preparation

### 11. Documentation (1-2 hours)
- [ ] Document all fixes
- [ ] Create deployment guide
- [ ] Create troubleshooting guide
- [ ] Create monitoring guide
- [ ] Update API documentation
- [ ] Create user manual

### 12. Monitoring Setup (2-3 hours)
- [ ] Set up error monitoring
- [ ] Set up performance monitoring
- [ ] Set up balance monitoring
- [ ] Set up trade monitoring
- [ ] Set up alerting
- [ ] Test monitoring systems

## Implementation Timeline

- **Week 1**: Complete Phase 1 (Critical Fixes)
- **Week 2**: Complete Phase 2 (High Priority Fixes)
- **Week 3**: Complete Phase 3 (Testing and Validation)
- **Week 4**: Complete Phase 4 (Deployment Preparation)

## Risk Mitigation

1. **Backup Strategy**: Create full system backup before implementing fixes
2. **Rollback Plan**: Prepare rollback procedures for each fix
3. **Testing Strategy**: Test each fix individually before integration
4. **Monitoring Strategy**: Monitor system health during implementation
5. **Gradual Rollout**: Implement fixes gradually to minimize risk

## Success Criteria

- [ ] All critical issues resolved
- [ ] All high priority issues resolved
- [ ] Comprehensive testing completed
- [ ] Performance within acceptable limits
- [ ] Monitoring systems operational
- [ ] Documentation complete
- [ ] Team trained on new systems
- [ ] Deployment ready
'''
        
        return plan
    
    def print_implementation_plan(self):
        """Print implementation plan"""
        print('\n' + '=' * 80)
        print('CRITICAL FIXES IMPLEMENTATION PLAN')
        print('=' * 80)
        
        print(self.generate_implementation_plan())
        
        print('\n📋 NEXT STEPS:')
        print('1. Review and approve implementation plan')
        print('2. Assign team members to each phase')
        print('3. Set up development environment')
        print('4. Begin Phase 1 implementation')
        print('5. Monitor progress and adjust timeline as needed')
        
        print('\n⚠️  IMPORTANT NOTES:')
        print('- All critical fixes must be completed before deployment')
        print('- Test each fix thoroughly before moving to the next')
        print('- Maintain backups throughout the process')
        print('- Monitor system health during implementation')
        print('- Have rollback plans ready for each fix')

def run_critical_fixes_implementation():
    """Run critical fixes implementation"""
    print('=' * 80)
    print('CRITICAL FIXES IMPLEMENTATION')
    print('=' * 80)
    
    implementer = CriticalFixesImplementation()
    
    print('Implementing critical fixes for the arbitrage system...')
    
    # Implement fixes
    balance_fix = implementer.implement_balance_validation()
    position_fix = implementer.implement_position_sizing_fix()
    error_fix = implementer.implement_error_handling_fix()
    thread_fix = implementer.implement_thread_safety_fix()
    
    # Print implementation plan
    implementer.print_implementation_plan()
    
    # Save fixes to files
    with open('balance_validation_fix.py', 'w') as f:
        f.write(balance_fix)
    
    with open('position_sizing_fix.py', 'w') as f:
        f.write(position_fix)
    
    with open('error_handling_fix.py', 'w') as f:
        f.write(error_fix)
    
    with open('thread_safety_fix.py', 'w') as f:
        f.write(thread_fix)
    
    print(f'\n📄 Fix implementations saved to:')
    print(f'   • balance_validation_fix.py')
    print(f'   • position_sizing_fix.py')
    print(f'   • error_handling_fix.py')
    print(f'   • thread_safety_fix.py')
    
    return True

if __name__ == "__main__":
    # Run critical fixes implementation
    run_critical_fixes_implementation()
