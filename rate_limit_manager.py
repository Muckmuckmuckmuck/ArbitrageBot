#!/usr/bin/env python3
"""
Rate Limit Manager
Comprehensive rate limit monitoring and management for high-frequency trading
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
from high_frequency_config import HighFrequencyConfig

logger = logging.getLogger(__name__)

@dataclass
class RateLimitStatus:
    """Rate limit status for an exchange"""
    exchange: str
    orders_per_minute: int
    requests_per_minute: int
    weight_per_minute: int
    orders_per_second: int
    requests_per_second: int
    weight_per_second: int
    current_orders_minute: int
    current_requests_minute: int
    current_weight_minute: int
    current_orders_second: int
    current_requests_second: int
    current_weight_second: int
    last_reset_minute: float
    last_reset_second: float
    is_limited: bool
    estimated_reset_time: float

class RateLimitManager:
    """Manages rate limits for all exchanges to prevent lockouts"""
    
    def __init__(self):
        self.config = HighFrequencyConfig()
        self.rate_limits = self.config.EXCHANGE_RATE_LIMITS
        self.rate_limit_status: Dict[str, RateLimitStatus] = {}
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1200))  # 20 minutes of history
        self.order_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1200))
        self.weight_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1200))
        
        # Initialize rate limit status for each exchange
        for exchange in self.rate_limits.keys():
            self.rate_limit_status[exchange] = RateLimitStatus(
                exchange=exchange,
                orders_per_minute=self.rate_limits[exchange]['orders_per_minute'],
                requests_per_minute=self.rate_limits[exchange]['requests_per_minute'],
                weight_per_minute=self.rate_limits[exchange]['weight_per_minute'],
                orders_per_second=self.rate_limits[exchange]['orders_per_second'],
                requests_per_second=self.rate_limits[exchange]['requests_per_second'],
                weight_per_second=self.rate_limits[exchange]['weight_per_second'],
                current_orders_minute=0,
                current_requests_minute=0,
                current_weight_minute=0,
                current_orders_second=0,
                current_requests_second=0,
                current_weight_second=0,
                last_reset_minute=time.time(),
                last_reset_second=time.time(),
                is_limited=False,
                estimated_reset_time=0.0
            )
        
        logger.info("Rate limit manager initialized")
    
    async def check_rate_limit(self, exchange: str, request_type: str = 'request', weight: int = 1) -> Tuple[bool, float]:
        """
        Check if a request can be made without hitting rate limits
        
        Args:
            exchange: Exchange name ('binance' or 'okx')
            request_type: Type of request ('request', 'order', 'weight')
            weight: Weight of the request (default 1)
            
        Returns:
            Tuple of (can_proceed, wait_time_seconds)
        """
        try:
            if exchange not in self.rate_limit_status:
                logger.error(f"Unknown exchange: {exchange}")
                return False, 0.0
            
            status = self.rate_limit_status[exchange]
            current_time = time.time()
            
            # Update counters based on time elapsed
            await self._update_counters(exchange, current_time)
            
            # Check if currently rate limited
            if status.is_limited:
                wait_time = status.estimated_reset_time - current_time
                if wait_time > 0:
                    logger.warning(f"Rate limited on {exchange}, waiting {wait_time:.2f} seconds")
                    return False, wait_time
                else:
                    # Reset rate limit status
                    status.is_limited = False
                    status.estimated_reset_time = 0.0
            
            # Check rate limits based on request type
            can_proceed = True
            wait_time = 0.0
            
            if request_type == 'order':
                # Check order limits
                if status.current_orders_second >= status.orders_per_second:
                    wait_time = max(wait_time, 1.0)  # Wait 1 second
                    can_proceed = False
                
                if status.current_orders_minute >= status.orders_per_minute:
                    wait_time = max(wait_time, 60.0)  # Wait 1 minute
                    can_proceed = False
            
            if request_type == 'request':
                # Check request limits
                if status.current_requests_second >= status.requests_per_second:
                    wait_time = max(wait_time, 1.0)  # Wait 1 second
                    can_proceed = False
                
                if status.current_requests_minute >= status.requests_per_minute:
                    wait_time = max(wait_time, 60.0)  # Wait 1 minute
                    can_proceed = False
            
            if request_type == 'weight':
                # Check weight limits
                if status.current_weight_second >= status.weight_per_second:
                    wait_time = max(wait_time, 1.0)  # Wait 1 second
                    can_proceed = False
                
                if status.current_weight_minute >= status.weight_per_minute:
                    wait_time = max(wait_time, 60.0)  # Wait 1 minute
                    can_proceed = False
            
            # If we can't proceed, set rate limit status
            if not can_proceed:
                status.is_limited = True
                status.estimated_reset_time = current_time + wait_time
                
                # Log rate limit warning
                rate_logger = logging.getLogger('rate_limit_monitoring')
                rate_logger.warning(
                    f"Rate limit exceeded on {exchange} for {request_type}: "
                    f"current={getattr(status, f'current_{request_type}s_second')}, "
                    f"limit={getattr(status, f'{request_type}s_per_second')}, "
                    f"wait_time={wait_time:.2f}s"
                )
            
            return can_proceed, wait_time
            
        except Exception as e:
            logger.error(f"Error checking rate limit for {exchange}: {str(e)}")
            return False, 5.0  # Conservative wait time on error
    
    async def record_request(self, exchange: str, request_type: str = 'request', weight: int = 1):
        """Record a request to update rate limit counters"""
        try:
            if exchange not in self.rate_limit_status:
                return
            
            status = self.rate_limit_status[exchange]
            current_time = time.time()
            
            # Update counters
            if request_type == 'order':
                status.current_orders_second += 1
                status.current_orders_minute += 1
                self.order_history[exchange].append(current_time)
            
            if request_type == 'request':
                status.current_requests_second += 1
                status.current_requests_minute += 1
                self.request_history[exchange].append(current_time)
            
            if request_type == 'weight':
                status.current_weight_second += weight
                status.current_weight_minute += weight
                self.weight_history[exchange].append((current_time, weight))
            
            # Log request
            logger.debug(f"Recorded {request_type} on {exchange}, weight: {weight}")
            
        except Exception as e:
            logger.error(f"Error recording request for {exchange}: {str(e)}")
    
    async def _update_counters(self, exchange: str, current_time: float):
        """Update rate limit counters based on elapsed time"""
        try:
            status = self.rate_limit_status[exchange]
            
            # Update second-based counters
            if current_time - status.last_reset_second >= 1.0:
                status.current_orders_second = 0
                status.current_requests_second = 0
                status.current_weight_second = 0
                status.last_reset_second = current_time
            
            # Update minute-based counters
            if current_time - status.last_reset_minute >= 60.0:
                status.current_orders_minute = 0
                status.current_requests_minute = 0
                status.current_weight_minute = 0
                status.last_reset_minute = current_time
            
            # Clean up old history
            cutoff_time = current_time - 1200  # 20 minutes ago
            self._cleanup_history(exchange, cutoff_time)
            
        except Exception as e:
            logger.error(f"Error updating counters for {exchange}: {str(e)}")
    
    def _cleanup_history(self, exchange: str, cutoff_time: float):
        """Clean up old request history"""
        try:
            # Clean up order history
            while self.order_history[exchange] and self.order_history[exchange][0] < cutoff_time:
                self.order_history[exchange].popleft()
            
            # Clean up request history
            while self.request_history[exchange] and self.request_history[exchange][0] < cutoff_time:
                self.request_history[exchange].popleft()
            
            # Clean up weight history
            while self.weight_history[exchange] and self.weight_history[exchange][0][0] < cutoff_time:
                self.weight_history[exchange].popleft()
                
        except Exception as e:
            logger.error(f"Error cleaning up history for {exchange}: {str(e)}")
    
    async def get_rate_limit_status(self, exchange: str) -> Optional[RateLimitStatus]:
        """Get current rate limit status for an exchange"""
        try:
            if exchange not in self.rate_limit_status:
                return None
            
            status = self.rate_limit_status[exchange]
            current_time = time.time()
            
            # Update counters
            await self._update_counters(exchange, current_time)
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting rate limit status for {exchange}: {str(e)}")
            return None
    
    async def get_all_rate_limit_status(self) -> Dict[str, RateLimitStatus]:
        """Get rate limit status for all exchanges"""
        try:
            current_time = time.time()
            
            for exchange in self.rate_limit_status.keys():
                await self._update_counters(exchange, current_time)
            
            return self.rate_limit_status.copy()
            
        except Exception as e:
            logger.error(f"Error getting all rate limit status: {str(e)}")
            return {}
    
    async def wait_for_rate_limit_reset(self, exchange: str) -> float:
        """Wait for rate limit to reset and return actual wait time"""
        try:
            status = self.rate_limit_status[exchange]
            
            if not status.is_limited:
                return 0.0
            
            wait_time = status.estimated_reset_time - time.time()
            
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.2f} seconds for rate limit reset on {exchange}")
                await asyncio.sleep(wait_time)
            
            # Reset rate limit status
            status.is_limited = False
            status.estimated_reset_time = 0.0
            
            return wait_time
            
        except Exception as e:
            logger.error(f"Error waiting for rate limit reset on {exchange}: {str(e)}")
            return 0.0
    
    async def get_rate_limit_usage(self, exchange: str) -> Dict[str, float]:
        """Get current rate limit usage as percentages"""
        try:
            status = await self.get_rate_limit_status(exchange)
            
            if not status:
                return {}
            
            usage = {
                'orders_per_second': (status.current_orders_second / status.orders_per_second) * 100,
                'requests_per_second': (status.current_requests_second / status.requests_per_second) * 100,
                'weight_per_second': (status.current_weight_second / status.weight_per_second) * 100,
                'orders_per_minute': (status.current_orders_minute / status.orders_per_minute) * 100,
                'requests_per_minute': (status.current_requests_minute / status.requests_per_minute) * 100,
                'weight_per_minute': (status.current_weight_minute / status.weight_per_minute) * 100,
            }
            
            return usage
            
        except Exception as e:
            logger.error(f"Error getting rate limit usage for {exchange}: {str(e)}")
            return {}
    
    async def is_rate_limited(self, exchange: str) -> bool:
        """Check if an exchange is currently rate limited"""
        try:
            status = await self.get_rate_limit_status(exchange)
            
            if not status:
                return True  # Conservative approach
            
            return status.is_limited
            
        except Exception as e:
            logger.error(f"Error checking if rate limited for {exchange}: {str(e)}")
            return True  # Conservative approach
    
    async def get_optimal_request_timing(self, exchange: str, request_type: str = 'request') -> float:
        """Get optimal timing for next request to avoid rate limits"""
        try:
            status = await self.get_rate_limit_status(exchange)
            
            if not status:
                return 1.0  # Conservative wait time
            
            # Calculate time until next available slot
            if request_type == 'order':
                if status.current_orders_second >= status.orders_per_second:
                    return 1.0  # Wait 1 second
                if status.current_orders_minute >= status.orders_per_minute:
                    return 60.0  # Wait 1 minute
            
            if request_type == 'request':
                if status.current_requests_second >= status.requests_per_second:
                    return 1.0  # Wait 1 second
                if status.current_requests_minute >= status.requests_per_minute:
                    return 60.0  # Wait 1 minute
            
            return 0.0  # Can proceed immediately
            
        except Exception as e:
            logger.error(f"Error getting optimal request timing for {exchange}: {str(e)}")
            return 1.0  # Conservative wait time
    
    def get_rate_limit_summary(self) -> Dict[str, Dict[str, any]]:
        """Get summary of rate limit status for all exchanges"""
        try:
            summary = {}
            
            for exchange, status in self.rate_limit_status.items():
                summary[exchange] = {
                    'is_limited': status.is_limited,
                    'orders_usage': {
                        'second': f"{status.current_orders_second}/{status.orders_per_second}",
                        'minute': f"{status.current_orders_minute}/{status.orders_per_minute}",
                    },
                    'requests_usage': {
                        'second': f"{status.current_requests_second}/{status.requests_per_second}",
                        'minute': f"{status.current_requests_minute}/{status.requests_per_minute}",
                    },
                    'weight_usage': {
                        'second': f"{status.current_weight_second}/{status.weight_per_second}",
                        'minute': f"{status.current_weight_minute}/{status.weight_per_minute}",
                    },
                    'estimated_reset_time': status.estimated_reset_time,
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting rate limit summary: {str(e)}")
            return {}

if __name__ == "__main__":
    # Test rate limit manager
    async def test_rate_limit_manager():
        manager = RateLimitManager()
        
        # Test rate limit checking
        can_proceed, wait_time = await manager.check_rate_limit('binance', 'request')
        print(f"Binance request: can_proceed={can_proceed}, wait_time={wait_time}")
        
        # Record a request
        await manager.record_request('binance', 'request')
        
        # Get status
        status = await manager.get_rate_limit_status('binance')
        print(f"Binance status: {status}")
        
        # Get summary
        summary = manager.get_rate_limit_summary()
        print(f"Rate limit summary: {summary}")
    
    # Run test
    asyncio.run(test_rate_limit_manager())
