
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
