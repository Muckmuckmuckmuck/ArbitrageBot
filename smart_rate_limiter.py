#!/usr/bin/env python3
"""
Smart Rate Limiter
Intelligent rate limiting to maximize API usage without hitting limits
"""

import logging
import time
from typing import Dict, Any, List, Optional
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class RateLimitWindow:
    """Track rate limit usage in a time window"""
    window_seconds: int
    max_requests: int
    requests: deque
    
    def add_request(self):
        """Add a request to the window"""
        now = time.time()
        self.requests.append(now)
        self._cleanup_old_requests()
    
    def _cleanup_old_requests(self):
        """Remove requests outside the window"""
        now = time.time()
        cutoff = now - self.window_seconds
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
    
    def get_current_usage(self) -> int:
        """Get current number of requests in window"""
        self._cleanup_old_requests()
        return len(self.requests)
    
    def get_usage_percent(self) -> float:
        """Get current usage as percentage"""
        return self.get_current_usage() / self.max_requests
    
    def can_make_request(self, safety_margin: float = 0.80) -> bool:
        """Check if we can make a request within safety margin"""
        return self.get_usage_percent() < safety_margin
    
    def time_until_available(self) -> float:
        """Get time in seconds until a request slot is available"""
        if self.can_make_request():
            return 0.0
        
        if not self.requests:
            return 0.0
        
        oldest_request = self.requests[0]
        time_until_expire = (oldest_request + self.window_seconds) - time.time()
        return max(0.0, time_until_expire)

class SmartRateLimiter:
    """Smart rate limiter with adaptive throttling and priority queue"""
    
    def __init__(self, config):
        self.config = config
        self.enabled = config.SMART_RATE_LIMITING['enabled']
        self.safety_margin = config.SMART_RATE_LIMITING['safety_margin']
        
        # Initialize rate limit windows for each exchange
        self.rate_limits: Dict[str, Dict[str, RateLimitWindow]] = {}
        
        for exchange, limits in config.EXCHANGE_RATE_LIMITS.items():
            self.rate_limits[exchange] = {
                'per_second': RateLimitWindow(
                    window_seconds=1,
                    max_requests=limits['requests_per_second'],
                    requests=deque()
                ),
                'per_minute': RateLimitWindow(
                    window_seconds=60,
                    max_requests=limits['requests_per_minute'],
                    requests=deque()
                ),
                'per_hour': RateLimitWindow(
                    window_seconds=3600,
                    max_requests=limits['requests_per_hour'],
                    requests=deque()
                ),
            }
        
        # Request cache
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.cache_ttl = config.SMART_RATE_LIMITING.get('cache_ttl_seconds', 2)
        
        # Priority queue
        self.priority_queue: List[Dict[str, Any]] = []
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'cached_requests': 0,
            'throttled_requests': 0,
            'rejected_requests': 0,
        }
        
        logger.info("Smart Rate Limiter initialized")
    
    async def execute_request(self, exchange: str, request_func, 
                             cache_key: Optional[str] = None,
                             priority: int = 5) -> Any:
        """Execute a request with rate limiting and caching"""
        
        if not self.enabled:
            return await request_func()
        
        # Check cache first
        if cache_key and self.config.SMART_RATE_LIMITING['cache_enabled']:
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                self.stats['cached_requests'] += 1
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
        
        # Check if we can make request
        can_request = self._can_make_request(exchange)
        
        if not can_request:
            # Need to wait or throttle
            wait_time = self._get_wait_time(exchange)
            
            if wait_time > 5.0:  # More than 5 seconds wait
                logger.warning(f"⚠️  Rate limit approaching for {exchange}, "
                             f"need to wait {wait_time:.1f}s")
                self.stats['throttled_requests'] += 1
            
            if wait_time > 0:
                logger.debug(f"Waiting {wait_time:.2f}s for rate limit on {exchange}")
                await asyncio.sleep(wait_time)
        
        # Record request
        self._record_request(exchange)
        self.stats['total_requests'] += 1
        
        # Execute request
        try:
            result = await request_func()
            
            # Cache result if applicable
            if cache_key and self.config.SMART_RATE_LIMITING['cache_enabled']:
                self._add_to_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing request on {exchange}: {e}")
            raise
    
    async def can_make_request(self, exchange: str) -> bool:
        """Check if we can make a request (public interface)"""
        return self._can_make_request(exchange)
    
    async def record_request(self, exchange: str):
        """Record a request (public interface)"""
        self._record_request(exchange)
    
    def _can_make_request(self, exchange: str) -> bool:
        """Check if we can make a request"""
        if exchange not in self.rate_limits:
            return True
        
        windows = self.rate_limits[exchange]
        
        # Check all windows
        for window_name, window in windows.items():
            if not window.can_make_request(self.safety_margin):
                logger.debug(f"{exchange} {window_name} at {window.get_usage_percent()*100:.1f}% capacity")
                return False
        
        return True
    
    def _get_wait_time(self, exchange: str) -> float:
        """Get time to wait before making request"""
        if exchange not in self.rate_limits:
            return 0.0
        
        windows = self.rate_limits[exchange]
        
        # Get max wait time across all windows
        max_wait = 0.0
        for window in windows.values():
            if not window.can_make_request(self.safety_margin):
                wait_time = window.time_until_available()
                max_wait = max(max_wait, wait_time)
        
        return max_wait
    
    def _record_request(self, exchange: str):
        """Record a request in all windows"""
        if exchange not in self.rate_limits:
            return
        
        for window in self.rate_limits[exchange].values():
            window.add_request()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get result from cache if not expired"""
        if cache_key not in self.cache:
            return None
        
        timestamp = self.cache_timestamps.get(cache_key, 0)
        if time.time() - timestamp > self.cache_ttl:
            # Cache expired
            del self.cache[cache_key]
            del self.cache_timestamps[cache_key]
            return None
        
        return self.cache[cache_key]
    
    def _add_to_cache(self, cache_key: str, result: Any):
        """Add result to cache"""
        self.cache[cache_key] = result
        self.cache_timestamps[cache_key] = time.time()
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get rate limit usage statistics"""
        stats = {
            'exchanges': {},
            'overall': self.stats.copy()
        }
        
        for exchange, windows in self.rate_limits.items():
            stats['exchanges'][exchange] = {}
            for window_name, window in windows.items():
                stats['exchanges'][exchange][window_name] = {
                    'current_usage': window.get_current_usage(),
                    'max_requests': window.max_requests,
                    'usage_percent': window.get_usage_percent() * 100,
                    'can_make_request': window.can_make_request(self.safety_margin),
                    'time_until_available': window.time_until_available(),
                }
        
        # Calculate cache hit rate
        total_requests = self.stats['total_requests'] + self.stats['cached_requests']
        if total_requests > 0:
            stats['overall']['cache_hit_rate'] = self.stats['cached_requests'] / total_requests
        else:
            stats['overall']['cache_hit_rate'] = 0.0
        
        return stats
    
    def log_usage_statistics(self):
        """Log current usage statistics"""
        stats = self.get_usage_statistics()
        
        logger.info("=" * 80)
        logger.info("RATE LIMIT USAGE STATISTICS")
        logger.info("=" * 80)
        
        for exchange, windows in stats['exchanges'].items():
            logger.info(f"\n{exchange.upper()}:")
            for window_name, window_stats in windows.items():
                logger.info(f"  {window_name}: "
                          f"{window_stats['current_usage']}/{window_stats['max_requests']} "
                          f"({window_stats['usage_percent']:.1f}%)")
        
        logger.info(f"\nOverall Statistics:")
        logger.info(f"  Total Requests: {stats['overall']['total_requests']}")
        logger.info(f"  Cached Requests: {stats['overall']['cached_requests']}")
        logger.info(f"  Cache Hit Rate: {stats['overall']['cache_hit_rate']*100:.1f}%")
        logger.info(f"  Throttled Requests: {stats['overall']['throttled_requests']}")
        logger.info("=" * 80)
    
    def clear_cache(self):
        """Clear all cached results"""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Cache cleared")
    
    def reset_statistics(self):
        """Reset usage statistics"""
        self.stats = {
            'total_requests': 0,
            'cached_requests': 0,
            'throttled_requests': 0,
            'rejected_requests': 0,
        }
        logger.info("Statistics reset")

