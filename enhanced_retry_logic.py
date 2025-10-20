#!/usr/bin/env python3
"""
Enhanced Retry Logic System - Enterprise Grade
==============================================

This module provides comprehensive retry logic with:
- Operation-specific retry strategies
- Circuit breaker pattern
- Exchange-specific retry logic
- Exponential backoff with jitter
- Error classification and handling
- Performance monitoring

Key Features:
1. Circuit Breaker: Prevents cascading failures
2. Operation-specific Retries: Different strategies per operation
3. Exchange-specific Logic: Coinbase vs Gemini handling
4. Error Classification: Retryable vs non-retryable errors
5. Performance Monitoring: Track retry success rates
"""

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass
from enum import Enum
import functools

import ccxt

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Classification of error types"""
    RETRYABLE = "retryable"           # Can be retried
    NON_RETRYABLE = "non_retryable"   # Should not be retried
    RATE_LIMIT = "rate_limit"         # Rate limiting
    NETWORK = "network"               # Network issues
    EXCHANGE = "exchange"             # Exchange-specific errors
    AUTHENTICATION = "authentication" # Auth issues
    INSUFFICIENT_FUNDS = "insufficient_funds"  # Not enough funds
    INVALID_ORDER = "invalid_order"   # Invalid order parameters

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_multiplier: float = 1.0

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3

@dataclass
class RetryStats:
    """Statistics for retry operations"""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    retry_count: int = 0
    total_delay: float = 0.0
    last_error: Optional[str] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None

class CircuitBreaker:
    """Circuit breaker implementation"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False
    
    def on_success(self):
        """Handle successful operation"""
        self.success_count += 1
        self.last_success_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("🔄 Circuit breaker: CLOSED (recovered)")
    
    def on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"🚨 Circuit breaker: OPEN (failures: {self.failure_count})")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("🚨 Circuit breaker: OPEN (half-open test failed)")
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.recovery_timeout

class EnhancedRetryLogic:
    """
    Enhanced retry logic with circuit breaker and operation-specific strategies
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_stats: Dict[str, RetryStats] = {}
        self.operation_configs: Dict[str, RetryConfig] = {}
        self.exchange_configs: Dict[str, RetryConfig] = {}
        
        # Initialize default configurations
        self._initialize_default_configs()
        
        logger.info("🚀 Enhanced Retry Logic initialized")
    
    def _initialize_default_configs(self):
        """Initialize default retry configurations"""
        
        # Operation-specific configurations
        self.operation_configs = {
            'fetch_balance': RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0),
            'fetch_ticker': RetryConfig(max_retries=5, base_delay=0.5, max_delay=5.0),
            'create_order': RetryConfig(max_retries=2, base_delay=2.0, max_delay=20.0),
            'fetch_order': RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0),
            'cancel_order': RetryConfig(max_retries=2, base_delay=1.0, max_delay=10.0),
            'withdraw': RetryConfig(max_retries=1, base_delay=5.0, max_delay=30.0),
            'fetch_deposit_address': RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0),
            'fetch_my_trades': RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0),
        }
        
        # Exchange-specific configurations
        self.exchange_configs = {
            'coinbase': RetryConfig(max_retries=3, base_delay=1.0, max_delay=15.0),
            'gemini': RetryConfig(max_retries=3, base_delay=1.0, max_delay=15.0),
        }
        
        # Circuit breaker configurations
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=3
        )
        
        # Initialize circuit breakers for each exchange
        for exchange in ['coinbase', 'gemini']:
            self.circuit_breakers[exchange] = CircuitBreaker(circuit_config)
            self.retry_stats[exchange] = RetryStats()
    
    def classify_error(self, error: Exception, exchange: str) -> ErrorType:
        """Classify an error to determine retry strategy"""
        error_str = str(error).lower()
        
        # Rate limiting
        if any(phrase in error_str for phrase in ['rate limit', 'too many requests', '429']):
            return ErrorType.RATE_LIMIT
        
        # Network issues
        if any(phrase in error_str for phrase in ['network', 'timeout', 'connection', 'dns']):
            return ErrorType.NETWORK
        
        # Authentication issues
        if any(phrase in error_str for phrase in ['unauthorized', 'authentication', 'api key', 'signature']):
            return ErrorType.AUTHENTICATION
        
        # Insufficient funds
        if any(phrase in error_str for phrase in ['insufficient', 'balance', 'funds']):
            return ErrorType.INSUFFICIENT_FUNDS
        
        # Invalid order
        if any(phrase in error_str for phrase in ['invalid', 'order', 'parameters', 'size']):
            return ErrorType.INVALID_ORDER
        
        # Exchange-specific errors
        if exchange == 'coinbase':
            if any(phrase in error_str for phrase in ['internal_server_error', 'service unavailable']):
                return ErrorType.EXCHANGE
        elif exchange == 'gemini':
            if any(phrase in error_str for phrase in ['maintenance', 'system error']):
                return ErrorType.EXCHANGE
        
        # Default to retryable for unknown errors
        return ErrorType.RETRYABLE
    
    def get_retry_config(self, operation: str, exchange: str) -> RetryConfig:
        """Get retry configuration for operation and exchange"""
        # Use operation-specific config if available
        if operation in self.operation_configs:
            return self.operation_configs[operation]
        
        # Fall back to exchange-specific config
        if exchange in self.exchange_configs:
            return self.exchange_configs[exchange]
        
        # Default config
        return RetryConfig()
    
    def calculate_delay(self, attempt: int, config: RetryConfig, error_type: ErrorType) -> float:
        """Calculate delay for retry attempt"""
        if error_type == ErrorType.RATE_LIMIT:
            # Longer delay for rate limiting
            base_delay = config.base_delay * 2
        else:
            base_delay = config.base_delay
        
        # Exponential backoff
        delay = base_delay * (config.exponential_base ** attempt)
        
        # Apply backoff multiplier
        delay *= config.backoff_multiplier
        
        # Cap at max delay
        delay = min(delay, config.max_delay)
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        return delay
    
    async def execute_with_retry(self, 
                                operation: Callable,
                                operation_name: str,
                                exchange: str,
                                *args,
                                **kwargs) -> Any:
        """
        Execute an operation with enhanced retry logic
        
        Args:
            operation: The function to execute
            operation_name: Name of the operation (for config lookup)
            exchange: Exchange name (for circuit breaker)
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
        
        Returns:
            Result of the operation
        
        Raises:
            Exception: If all retries fail
        """
        circuit_breaker = self.circuit_breakers[exchange]
        retry_config = self.get_retry_config(operation_name, exchange)
        stats = self.retry_stats[exchange]
        
        # Check circuit breaker
        if not circuit_breaker.can_execute():
            error_msg = f"Circuit breaker OPEN for {exchange} - operation {operation_name} blocked"
            logger.warning(f"🚨 {error_msg}")
            raise Exception(error_msg)
        
        last_error = None
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                stats.total_attempts += 1
                
                # Execute the operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                # Handle async results from CCXT
                if hasattr(result, '__await__'):
                    result = await result
                
                # Success!
                circuit_breaker.on_success()
                stats.successful_attempts += 1
                stats.last_success = datetime.now()
                
                if attempt > 0:
                    logger.info(f"✅ {operation_name} succeeded on attempt {attempt + 1} for {exchange}")
                
                return result
                
            except Exception as e:
                last_error = e
                stats.failed_attempts += 1
                stats.last_failure = datetime.now()
                stats.last_error = str(e)
                
                # Classify the error
                error_type = self.classify_error(e, exchange)
                
                # Check if we should retry
                if attempt >= retry_config.max_retries:
                    circuit_breaker.on_failure()
                    logger.error(f"❌ {operation_name} failed after {retry_config.max_retries + 1} attempts for {exchange}: {str(e)}")
                    raise e
                
                if error_type == ErrorType.NON_RETRYABLE:
                    circuit_breaker.on_failure()
                    logger.error(f"❌ {operation_name} failed with non-retryable error for {exchange}: {str(e)}")
                    raise e
                
                # Calculate delay
                delay = self.calculate_delay(attempt, retry_config, error_type)
                stats.total_delay += delay
                stats.retry_count += 1
                
                logger.warning(f"⚠️ {operation_name} failed (attempt {attempt + 1}/{retry_config.max_retries + 1}) for {exchange}: {str(e)}")
                logger.info(f"🔄 Retrying {operation_name} in {delay:.2f}s (error type: {error_type.value})")
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        circuit_breaker.on_failure()
        raise last_error
    
    def get_stats(self, exchange: str) -> RetryStats:
        """Get retry statistics for an exchange"""
        return self.retry_stats.get(exchange, RetryStats())
    
    def get_circuit_breaker_state(self, exchange: str) -> CircuitState:
        """Get circuit breaker state for an exchange"""
        return self.circuit_breakers[exchange].state
    
    def reset_circuit_breaker(self, exchange: str):
        """Manually reset circuit breaker for an exchange"""
        circuit_breaker = self.circuit_breakers[exchange]
        circuit_breaker.state = CircuitState.CLOSED
        circuit_breaker.failure_count = 0
        circuit_breaker.success_count = 0
        logger.info(f"🔄 Circuit breaker manually reset for {exchange}")
    
    def get_all_stats(self) -> Dict[str, RetryStats]:
        """Get statistics for all exchanges"""
        return self.retry_stats.copy()
    
    def get_all_circuit_breaker_states(self) -> Dict[str, CircuitState]:
        """Get circuit breaker states for all exchanges"""
        return {exchange: cb.state for exchange, cb in self.circuit_breakers.items()}

# Global instance
enhanced_retry_logic = EnhancedRetryLogic()

# Decorator for easy use
def with_retry(operation_name: str, exchange: str):
    """Decorator to add retry logic to functions"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await enhanced_retry_logic.execute_with_retry(
                func, operation_name, exchange, *args, **kwargs
            )
        return wrapper
    return decorator

# Example usage
async def example_usage():
    """Example of how to use the enhanced retry logic"""
    
    # Method 1: Direct usage
    async def fetch_balance_with_retry(exchange, exchange_name):
        return await enhanced_retry_logic.execute_with_retry(
            exchange.fetch_balance,
            'fetch_balance',
            exchange_name
        )
    
    # Method 2: Using decorator
    @with_retry('fetch_ticker', 'coinbase')
    async def fetch_ticker_with_retry(exchange, symbol):
        return await exchange.fetch_ticker(symbol)
    
    # Get statistics
    stats = enhanced_retry_logic.get_stats('coinbase')
    print(f"Coinbase retry stats: {stats}")
    
    # Check circuit breaker state
    state = enhanced_retry_logic.get_circuit_breaker_state('coinbase')
    print(f"Coinbase circuit breaker: {state}")

if __name__ == "__main__":
    asyncio.run(example_usage())
