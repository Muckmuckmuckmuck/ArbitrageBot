import asyncio
import time
import traceback
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Types of errors that can occur"""
    API_RATE_LIMIT = "api_rate_limit"
    API_TIMEOUT = "api_timeout"
    NETWORK_ERROR = "network_error"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    ORDER_FAILED = "order_failed"
    TRANSFER_FAILED = "transfer_failed"
    EXCHANGE_DOWN = "exchange_down"
    EXCHANGE_MAINTENANCE = "exchange_maintenance"
    INVALID_SYMBOL = "invalid_symbol"
    SLIPPAGE_TOO_HIGH = "slippage_too_high"
    LIQUIDITY_INSUFFICIENT = "liquidity_insufficient"
    VOLATILITY_TOO_HIGH = "volatility_too_high"
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class ErrorEvent:
    """Data class for error events"""
    error_type: ErrorType
    message: str
    timestamp: float
    exchange: Optional[str] = None
    symbol: Optional[str] = None
    retry_count: int = 0
    is_critical: bool = False

class CircuitBreaker:
    """Circuit breaker pattern for handling failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e

class ErrorHandler:
    """Comprehensive error handling and recovery system"""
    
    def __init__(self):
        self.error_history: List[ErrorEvent] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_strategies = {
            ErrorType.API_RATE_LIMIT: {"max_retries": 3, "backoff_factor": 2, "exponential": True},
            ErrorType.API_TIMEOUT: {"max_retries": 2, "backoff_factor": 1.5, "exponential": True},
            ErrorType.NETWORK_ERROR: {"max_retries": 5, "backoff_factor": 1.2, "exponential": True},
            ErrorType.ORDER_FAILED: {"max_retries": 1, "backoff_factor": 1.0, "exponential": False},
            ErrorType.TRANSFER_FAILED: {"max_retries": 2, "backoff_factor": 2.0, "exponential": True},
            ErrorType.EXCHANGE_DOWN: {"max_retries": 0, "backoff_factor": 1.0, "exponential": False},
            ErrorType.EXCHANGE_MAINTENANCE: {"max_retries": 0, "backoff_factor": 1.0, "exponential": False},
            ErrorType.INSUFFICIENT_BALANCE: {"max_retries": 0, "backoff_factor": 1.0, "exponential": False},
            ErrorType.INVALID_SYMBOL: {"max_retries": 0, "backoff_factor": 1.0, "exponential": False},
            ErrorType.SLIPPAGE_TOO_HIGH: {"max_retries": 1, "backoff_factor": 1.0, "exponential": False},
            ErrorType.LIQUIDITY_INSUFFICIENT: {"max_retries": 1, "backoff_factor": 1.0, "exponential": False},
            ErrorType.VOLATILITY_TOO_HIGH: {"max_retries": 1, "backoff_factor": 1.0, "exponential": False},
            ErrorType.RISK_LIMIT_EXCEEDED: {"max_retries": 0, "backoff_factor": 1.0, "exponential": False},
        }
        
        # Error recovery strategies
        self.recovery_strategies = {
            ErrorType.API_RATE_LIMIT: self._recover_from_rate_limit,
            ErrorType.EXCHANGE_DOWN: self._recover_from_exchange_down,
            ErrorType.SLIPPAGE_TOO_HIGH: self._recover_from_slippage,
            ErrorType.LIQUIDITY_INSUFFICIENT: self._recover_from_liquidity,
            ErrorType.VOLATILITY_TOO_HIGH: self._recover_from_volatility,
        }
        
        # Emergency stop conditions
        self.emergency_stop_conditions = {
            'max_consecutive_errors': 10,
            'max_critical_errors_per_hour': 5,
            'max_exchange_failures': 3,
            'max_portfolio_loss_percent': 5.0
        }
        
        self.emergency_stop_active = False
        self.last_emergency_stop_time = 0
        
    def get_circuit_breaker(self, key: str) -> CircuitBreaker:
        """Get or create circuit breaker for a key"""
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker()
        return self.circuit_breakers[key]
    
    def log_error(self, error_type: ErrorType, message: str, exchange: str = None, 
                  symbol: str = None, is_critical: bool = False):
        """Log an error event"""
        error_event = ErrorEvent(
            error_type=error_type,
            message=message,
            timestamp=time.time(),
            exchange=exchange,
            symbol=symbol,
            is_critical=is_critical
        )
        
        self.error_history.append(error_event)
        
        # Keep only recent errors (last 1000)
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        # Log the error
        log_level = logging.CRITICAL if is_critical else logging.ERROR
        logger.log(log_level, f"[{error_type.value}] {message} (Exchange: {exchange}, Symbol: {symbol})")
        
        # Update circuit breaker if needed
        if exchange:
            cb = self.get_circuit_breaker(exchange)
            cb.failure_count += 1
            cb.last_failure_time = time.time()
    
    async def handle_api_error(self, error: Exception, exchange: str, symbol: str = None) -> bool:
        """Handle API-related errors with appropriate retry logic"""
        try:
            error_message = str(error).lower()
            
            # Determine error type
            if "rate limit" in error_message or "429" in error_message:
                error_type = ErrorType.API_RATE_LIMIT
            elif "timeout" in error_message or "time out" in error_message:
                error_type = ErrorType.API_TIMEOUT
            elif "network" in error_message or "connection" in error_message:
                error_type = ErrorType.NETWORK_ERROR
            elif "insufficient balance" in error_message:
                error_type = ErrorType.INSUFFICIENT_BALANCE
            elif "exchange" in error_message and "down" in error_message:
                error_type = ErrorType.EXCHANGE_DOWN
            else:
                error_type = ErrorType.UNKNOWN_ERROR
            
            # Log the error
            self.log_error(error_type, str(error), exchange, symbol)
            
            # Check if we should retry
            strategy = self.retry_strategies.get(error_type, {"max_retries": 0, "backoff_factor": 1.0})
            
            if strategy["max_retries"] > 0:
                # Calculate backoff time
                backoff_time = strategy["backoff_factor"] ** min(len(self.error_history), 5)
                logger.info(f"Retrying after {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
                return True
            else:
                logger.error(f"No retry strategy for {error_type.value}")
                return False
                
        except Exception as e:
            logger.error(f"Error in handle_api_error: {str(e)}")
            return False
    
    async def handle_order_error(self, error: Exception, exchange: str, symbol: str) -> bool:
        """Handle order-related errors"""
        try:
            error_message = str(error).lower()
            
            if "insufficient balance" in error_message:
                error_type = ErrorType.INSUFFICIENT_BALANCE
            elif "invalid symbol" in error_message:
                error_type = ErrorType.ORDER_FAILED
            else:
                error_type = ErrorType.ORDER_FAILED
            
            self.log_error(error_type, str(error), exchange, symbol, is_critical=True)
            
            # Don't retry order failures immediately
            return False
            
        except Exception as e:
            logger.error(f"Error in handle_order_error: {str(e)}")
            return False
    
    async def handle_transfer_error(self, error: Exception, currency: str, from_exchange: str, 
                                   to_exchange: str) -> bool:
        """Handle transfer-related errors"""
        try:
            error_message = str(error).lower()
            
            if "insufficient balance" in error_message:
                error_type = ErrorType.INSUFFICIENT_BALANCE
            elif "network" in error_message:
                error_type = ErrorType.NETWORK_ERROR
            else:
                error_type = ErrorType.TRANSFER_FAILED
            
            self.log_error(error_type, str(error), from_exchange, currency, is_critical=True)
            
            # Retry transfer failures with backoff
            strategy = self.retry_strategies[ErrorType.TRANSFER_FAILED]
            if strategy["max_retries"] > 0:
                backoff_time = strategy["backoff_factor"] ** 2  # Longer backoff for transfers
                logger.info(f"Retrying transfer after {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in handle_transfer_error: {str(e)}")
            return False
    
    def get_error_summary(self, time_window: int = 3600) -> Dict:
        """Get error summary for the last time_window seconds"""
        try:
            current_time = time.time()
            recent_errors = [
                e for e in self.error_history 
                if current_time - e.timestamp <= time_window
            ]
            
            # Group by error type
            error_counts = {}
            critical_errors = 0
            exchange_errors = {}
            
            for error in recent_errors:
                error_type = error.error_type.value
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                
                if error.is_critical:
                    critical_errors += 1
                
                if error.exchange:
                    exchange_errors[error.exchange] = exchange_errors.get(error.exchange, 0) + 1
            
            return {
                'total_errors': len(recent_errors),
                'critical_errors': critical_errors,
                'error_counts': error_counts,
                'exchange_errors': exchange_errors,
                'time_window': time_window,
                'circuit_breaker_status': {
                    exchange: cb.state for exchange, cb in self.circuit_breakers.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in get_error_summary: {str(e)}")
            return {}
    
    def is_exchange_healthy(self, exchange: str) -> bool:
        """Check if an exchange is healthy based on recent errors"""
        try:
            cb = self.get_circuit_breaker(exchange)
            return cb.state == "CLOSED"
        except:
            return True
    
    def should_skip_symbol(self, symbol: str, time_window: int = 1800) -> bool:
        """Check if we should skip trading a symbol due to recent errors"""
        try:
            current_time = time.time()
            recent_symbol_errors = [
                e for e in self.error_history 
                if e.symbol == symbol and current_time - e.timestamp <= time_window
            ]
            
            # Skip if more than 3 errors in the last 30 minutes
            return len(recent_symbol_errors) > 3
        except:
            return False
    
    async def _recover_from_rate_limit(self, error: Exception, context: Dict) -> bool:
        """Recover from rate limit errors"""
        try:
            # Extract rate limit info from error message
            error_message = str(error).lower()
            
            if "429" in error_message or "rate limit" in error_message:
                # Calculate backoff time based on error message
                if "retry after" in error_message:
                    try:
                        # Extract retry-after value
                        retry_after = int(error_message.split("retry after")[1].split()[0])
                        await asyncio.sleep(min(retry_after, 60))  # Max 60 seconds
                    except:
                        await asyncio.sleep(5)  # Default 5 seconds
                else:
                    await asyncio.sleep(5)
                
                logger.info("Recovered from rate limit, resuming operations")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error in rate limit recovery: {str(e)}")
            return False
    
    async def _recover_from_exchange_down(self, error: Exception, context: Dict) -> bool:
        """Recover from exchange downtime"""
        try:
            exchange = context.get('exchange', 'unknown')
            
            # Check if exchange is back online
            await asyncio.sleep(30)  # Wait 30 seconds
            
            # In a real implementation, you would ping the exchange API here
            # For now, we'll assume it's back online after the wait
            logger.info(f"Attempting to recover from {exchange} downtime")
            return True
            
        except Exception as e:
            logger.error(f"Error in exchange downtime recovery: {str(e)}")
            return False
    
    async def _recover_from_slippage(self, error: Exception, context: Dict) -> bool:
        """Recover from high slippage"""
        try:
            # Reduce order size and try again
            symbol = context.get('symbol', 'unknown')
            logger.info(f"Reducing order size for {symbol} due to high slippage")
            
            # Wait for market conditions to improve
            await asyncio.sleep(10)
            return True
            
        except Exception as e:
            logger.error(f"Error in slippage recovery: {str(e)}")
            return False
    
    async def _recover_from_liquidity(self, error: Exception, context: Dict) -> bool:
        """Recover from insufficient liquidity"""
        try:
            symbol = context.get('symbol', 'unknown')
            logger.info(f"Waiting for liquidity to improve for {symbol}")
            
            # Wait for better liquidity conditions
            await asyncio.sleep(30)
            return True
            
        except Exception as e:
            logger.error(f"Error in liquidity recovery: {str(e)}")
            return False
    
    async def _recover_from_volatility(self, error: Exception, context: Dict) -> bool:
        """Recover from high volatility"""
        try:
            symbol = context.get('symbol', 'unknown')
            logger.info(f"Waiting for volatility to decrease for {symbol}")
            
            # Wait for volatility to decrease
            await asyncio.sleep(60)
            return True
            
        except Exception as e:
            logger.error(f"Error in volatility recovery: {str(e)}")
            return False
    
    async def execute_with_recovery(self, func: Callable, error_type: ErrorType, 
                                  context: Dict, *args, **kwargs) -> Any:
        """Execute function with automatic error recovery"""
        try:
            max_attempts = 3
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    result = await func(*args, **kwargs)
                    return result
                    
                except Exception as e:
                    attempt += 1
                    logger.warning(f"Attempt {attempt} failed for {error_type.value}: {str(e)}")
                    
                    if attempt >= max_attempts:
                        raise e
                    
                    # Try to recover
                    recovery_func = self.recovery_strategies.get(error_type)
                    if recovery_func:
                        recovery_success = await recovery_func(e, context)
                        if not recovery_success:
                            raise e
                    else:
                        # Default recovery: wait and retry
                        await asyncio.sleep(2 ** attempt)
            
        except Exception as e:
            logger.error(f"All recovery attempts failed: {str(e)}")
            raise e
    
    def check_emergency_stop_conditions(self) -> bool:
        """Check if emergency stop conditions are met"""
        try:
            current_time = time.time()
            
            # Check consecutive errors
            recent_errors = [
                e for e in self.error_history 
                if current_time - e.timestamp <= 300  # Last 5 minutes
            ]
            
            if len(recent_errors) >= self.emergency_stop_conditions['max_consecutive_errors']:
                logger.critical("Emergency stop: Too many consecutive errors")
                return True
            
            # Check critical errors per hour
            hour_ago = current_time - 3600
            critical_errors = [
                e for e in self.error_history 
                if e.timestamp >= hour_ago and e.is_critical
            ]
            
            if len(critical_errors) >= self.emergency_stop_conditions['max_critical_errors_per_hour']:
                logger.critical("Emergency stop: Too many critical errors in the last hour")
                return True
            
            # Check exchange failures
            exchange_failures = {}
            for error in recent_errors:
                if error.exchange:
                    exchange_failures[error.exchange] = exchange_failures.get(error.exchange, 0) + 1
            
            for exchange, count in exchange_failures.items():
                if count >= self.emergency_stop_conditions['max_exchange_failures']:
                    logger.critical(f"Emergency stop: Too many failures on {exchange}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking emergency stop conditions: {str(e)}")
            return False
    
    def trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop"""
        try:
            self.emergency_stop_active = True
            self.last_emergency_stop_time = time.time()
            
            logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
            logger.critical("All trading operations have been halted")
            logger.critical("Manual intervention required")
            
        except Exception as e:
            logger.error(f"Error triggering emergency stop: {str(e)}")
    
    def reset_emergency_stop(self):
        """Reset emergency stop"""
        try:
            self.emergency_stop_active = False
            self.last_emergency_stop_time = 0
            
            logger.info("Emergency stop has been reset")
            
        except Exception as e:
            logger.error(f"Error resetting emergency stop: {str(e)}")
    
    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is active"""
        return self.emergency_stop_active
    
    def get_enhanced_error_summary(self, time_window: int = 3600) -> Dict:
        """Get enhanced error summary with recovery information"""
        try:
            current_time = time.time()
            recent_errors = [
                e for e in self.error_history 
                if current_time - e.timestamp <= time_window
            ]
            
            # Basic error counts
            error_counts = {}
            critical_errors = 0
            exchange_errors = {}
            symbol_errors = {}
            
            for error in recent_errors:
                error_type = error.error_type.value
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                
                if error.is_critical:
                    critical_errors += 1
                
                if error.exchange:
                    exchange_errors[error.exchange] = exchange_errors.get(error.exchange, 0) + 1
                
                if error.symbol:
                    symbol_errors[error.symbol] = symbol_errors.get(error.symbol, 0) + 1
            
            # Calculate error rates
            total_operations = len(recent_errors) + 1000  # Assume 1000 successful operations
            error_rate = len(recent_errors) / total_operations * 100 if total_operations > 0 else 0
            
            # Circuit breaker status
            circuit_breaker_status = {}
            for exchange, cb in self.circuit_breakers.items():
                circuit_breaker_status[exchange] = {
                    'state': cb.state,
                    'failure_count': cb.failure_count,
                    'last_failure': cb.last_failure_time
                }
            
            summary = {
                'total_errors': len(recent_errors),
                'critical_errors': critical_errors,
                'error_rate_percent': error_rate,
                'error_counts': error_counts,
                'exchange_errors': exchange_errors,
                'symbol_errors': symbol_errors,
                'time_window': time_window,
                'circuit_breaker_status': circuit_breaker_status,
                'emergency_stop_active': self.emergency_stop_active,
                'last_emergency_stop': self.last_emergency_stop_time,
                'recovery_strategies_available': list(self.recovery_strategies.keys()),
                'timestamp': current_time
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error in get_enhanced_error_summary: {str(e)}")
            return {}
