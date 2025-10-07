import asyncio
import time
import statistics
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Data class for performance metrics"""
    operation: str
    duration_ms: float
    timestamp: float
    success: bool
    exchange: str = ""
    symbol: str = ""
    error: str = ""

@dataclass
class LatencyProfile:
    """Data class for latency profile"""
    operation: str
    min_latency_ms: float
    max_latency_ms: float
    avg_latency_ms: float
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    success_rate: float
    sample_count: int

class PerformanceOptimizer:
    """Performance optimization and latency reduction system"""
    
    def __init__(self):
        self.performance_history = {}
        self.latency_profiles = {}
        self.optimization_configs = {}
        self.connection_pools = {}
        self.cache_metrics = {}
        
        # Performance thresholds
        self.thresholds = {
            'ticker_fetch': 100,      # ms
            'order_placement': 500,   # ms
            'order_cancellation': 300, # ms
            'balance_check': 200,     # ms
            'transfer_initiation': 1000, # ms
            'websocket_latency': 50,  # ms
        }
        
        # Optimization strategies
        self.optimization_strategies = {
            'connection_pooling': True,
            'request_batching': True,
            'parallel_execution': True,
            'caching': True,
            'compression': True,
            'keep_alive': True,
        }
        
    def record_operation(self, operation: str, duration_ms: float, success: bool, 
                        exchange: str = "", symbol: str = "", error: str = ""):
        """Record performance metrics for an operation"""
        try:
            if operation not in self.performance_history:
                self.performance_history[operation] = []
            
            metric = PerformanceMetrics(
                operation=operation,
                duration_ms=duration_ms,
                timestamp=time.time(),
                success=success,
                exchange=exchange,
                symbol=symbol,
                error=error
            )
            
            self.performance_history[operation].append(metric)
            
            # Keep only recent history (last 1000 records per operation)
            if len(self.performance_history[operation]) > 1000:
                self.performance_history[operation] = self.performance_history[operation][-1000:]
            
            # Update latency profile
            self._update_latency_profile(operation)
            
        except Exception as e:
            logger.error(f"Error recording performance metric: {str(e)}")
    
    def _update_latency_profile(self, operation: str):
        """Update latency profile for an operation"""
        try:
            if operation not in self.performance_history:
                return
            
            metrics = self.performance_history[operation]
            if not metrics:
                return
            
            # Extract latencies and success rates
            latencies = [m.duration_ms for m in metrics]
            successes = [m for m in metrics if m.success]
            
            # Calculate percentiles
            latencies_sorted = sorted(latencies)
            n = len(latencies_sorted)
            
            if n > 0:
                profile = LatencyProfile(
                    operation=operation,
                    min_latency_ms=min(latencies),
                    max_latency_ms=max(latencies),
                    avg_latency_ms=statistics.mean(latencies),
                    p50_latency_ms=latencies_sorted[int(n * 0.5)],
                    p90_latency_ms=latencies_sorted[int(n * 0.9)],
                    p95_latency_ms=latencies_sorted[int(n * 0.95)],
                    p99_latency_ms=latencies_sorted[int(n * 0.99)],
                    success_rate=len(successes) / len(metrics) * 100,
                    sample_count=n
                )
                
                self.latency_profiles[operation] = profile
                
        except Exception as e:
            logger.error(f"Error updating latency profile: {str(e)}")
    
    def get_latency_profile(self, operation: str) -> Optional[LatencyProfile]:
        """Get latency profile for an operation"""
        return self.latency_profiles.get(operation)
    
    def get_performance_summary(self, operation: str = None, hours: int = 24) -> Dict:
        """Get performance summary"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)
            
            if operation:
                # Get specific operation metrics
                if operation not in self.performance_history:
                    return {}
                
                recent_metrics = [
                    m for m in self.performance_history[operation]
                    if m.timestamp >= cutoff_time
                ]
                
                if not recent_metrics:
                    return {}
                
                latencies = [m.duration_ms for m in recent_metrics]
                successes = [m for m in recent_metrics if m.success]
                
                return {
                    'operation': operation,
                    'total_operations': len(recent_metrics),
                    'successful_operations': len(successes),
                    'success_rate': len(successes) / len(recent_metrics) * 100,
                    'avg_latency_ms': statistics.mean(latencies),
                    'min_latency_ms': min(latencies),
                    'max_latency_ms': max(latencies),
                    'p95_latency_ms': sorted(latencies)[int(len(latencies) * 0.95)],
                    'time_period_hours': hours
                }
            else:
                # Get all operations summary
                summary = {}
                for op in self.performance_history.keys():
                    op_summary = self.get_performance_summary(op, hours)
                    if op_summary:
                        summary[op] = op_summary
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {}
    
    def is_operation_slow(self, operation: str) -> bool:
        """Check if an operation is performing slowly"""
        try:
            threshold = self.thresholds.get(operation, 1000)  # Default 1 second
            profile = self.latency_profiles.get(operation)
            
            if not profile:
                return False
            
            # Check if 95th percentile exceeds threshold
            return profile.p95_latency_ms > threshold
            
        except Exception as e:
            logger.error(f"Error checking operation performance: {str(e)}")
            return False
    
    async def optimize_ticker_fetching(self, exchange_manager) -> Dict:
        """Optimize ticker fetching performance"""
        try:
            optimizations = {}
            
            # Test current performance
            start_time = time.time()
            symbols = ['XRP/USDT', 'XLM/USDT', 'SOL/USDT', 'BNB/USDT']
            
            # Sequential fetching
            seq_start = time.time()
            for symbol in symbols:
                exchange = exchange_manager.get_exchange('binance')
                await exchange.get_ticker(symbol)
            seq_duration = (time.time() - seq_start) * 1000
            
            # Parallel fetching
            par_start = time.time()
            tasks = []
            for symbol in symbols:
                exchange = exchange_manager.get_exchange('binance')
                task = asyncio.create_task(exchange.get_ticker(symbol))
                tasks.append(task)
            await asyncio.gather(*tasks)
            par_duration = (time.time() - par_start) * 1000
            
            # Calculate improvement
            improvement = (seq_duration - par_duration) / seq_duration * 100
            
            optimizations['ticker_fetch'] = {
                'sequential_duration_ms': seq_duration,
                'parallel_duration_ms': par_duration,
                'improvement_percent': improvement,
                'recommendation': 'Use parallel fetching' if improvement > 20 else 'Sequential is acceptable'
            }
            
            logger.info(f"Ticker fetching optimization: {improvement:.1f}% improvement with parallel execution")
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Error optimizing ticker fetching: {str(e)}")
            return {}
    
    async def optimize_order_execution(self, exchange_manager) -> Dict:
        """Optimize order execution performance"""
        try:
            optimizations = {}
            
            # Test order placement latency
            exchange = exchange_manager.get_exchange('binance')
            symbol = 'XRP/USDT'
            
            # Measure order placement latency
            start_time = time.time()
            try:
                # This would be a real order in production
                # order = await exchange.place_market_order(symbol, 'buy', 0.001)
                # Simulate order placement
                await asyncio.sleep(0.1)  # Simulate API call
                order_duration = (time.time() - start_time) * 1000
                
                optimizations['order_placement'] = {
                    'avg_latency_ms': order_duration,
                    'threshold_ms': self.thresholds['order_placement'],
                    'within_threshold': order_duration <= self.thresholds['order_placement'],
                    'recommendation': 'Optimize API calls' if order_duration > self.thresholds['order_placement'] else 'Performance acceptable'
                }
                
            except Exception as e:
                logger.warning(f"Could not test order execution: {str(e)}")
                optimizations['order_placement'] = {
                    'error': str(e),
                    'recommendation': 'Check API connectivity'
                }
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Error optimizing order execution: {str(e)}")
            return {}
    
    async def optimize_websocket_performance(self, websocket_manager) -> Dict:
        """Optimize WebSocket performance"""
        try:
            optimizations = {}
            
            # Measure WebSocket message processing latency
            message_times = []
            
            def measure_message_latency(message):
                start_time = time.time()
                # Process message
                time.sleep(0.001)  # Simulate processing
                latency = (time.time() - start_time) * 1000
                message_times.append(latency)
            
            # Simulate message processing
            for _ in range(100):
                measure_message_latency(None)
            
            if message_times:
                avg_latency = statistics.mean(message_times)
                p95_latency = sorted(message_times)[int(len(message_times) * 0.95)]
                
                optimizations['websocket_processing'] = {
                    'avg_latency_ms': avg_latency,
                    'p95_latency_ms': p95_latency,
                    'threshold_ms': self.thresholds['websocket_latency'],
                    'within_threshold': p95_latency <= self.thresholds['websocket_latency'],
                    'recommendation': 'Optimize message processing' if p95_latency > self.thresholds['websocket_latency'] else 'Performance acceptable'
                }
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Error optimizing WebSocket performance: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self) -> List[Dict]:
        """Get optimization recommendations based on performance data"""
        try:
            recommendations = []
            
            for operation, profile in self.latency_profiles.items():
                threshold = self.thresholds.get(operation, 1000)
                
                if profile.p95_latency_ms > threshold:
                    recommendation = {
                        'operation': operation,
                        'issue': f'95th percentile latency ({profile.p95_latency_ms:.1f}ms) exceeds threshold ({threshold}ms)',
                        'priority': 'high' if profile.p95_latency_ms > threshold * 2 else 'medium',
                        'suggestions': self._get_optimization_suggestions(operation)
                    }
                    recommendations.append(recommendation)
                
                if profile.success_rate < 95:
                    recommendation = {
                        'operation': operation,
                        'issue': f'Success rate ({profile.success_rate:.1f}%) is below 95%',
                        'priority': 'high',
                        'suggestions': ['Check error handling', 'Improve retry logic', 'Add circuit breakers']
                    }
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return []
    
    def _get_optimization_suggestions(self, operation: str) -> List[str]:
        """Get specific optimization suggestions for an operation"""
        suggestions = {
            'ticker_fetch': [
                'Use WebSocket streams instead of REST API',
                'Implement connection pooling',
                'Cache ticker data',
                'Use parallel requests for multiple symbols'
            ],
            'order_placement': [
                'Optimize API call sequence',
                'Use order batching if supported',
                'Implement order pre-validation',
                'Use faster order types (market vs limit)'
            ],
            'balance_check': [
                'Cache balance data',
                'Use WebSocket balance updates',
                'Reduce balance check frequency',
                'Implement balance change detection'
            ],
            'transfer_initiation': [
                'Pre-validate transfer parameters',
                'Use batch transfers if supported',
                'Optimize network selection',
                'Implement transfer queuing'
            ]
        }
        
        return suggestions.get(operation, ['General performance optimization'])
    
    async def run_performance_benchmark(self, exchange_manager, websocket_manager=None) -> Dict:
        """Run comprehensive performance benchmark"""
        try:
            benchmark_results = {}
            
            logger.info("Starting performance benchmark...")
            
            # Benchmark ticker fetching
            ticker_optimizations = await self.optimize_ticker_fetching(exchange_manager)
            benchmark_results['ticker_fetching'] = ticker_optimizations
            
            # Benchmark order execution
            order_optimizations = await self.optimize_order_execution(exchange_manager)
            benchmark_results['order_execution'] = order_optimizations
            
            # Benchmark WebSocket performance
            if websocket_manager:
                websocket_optimizations = await self.optimize_websocket_performance(websocket_manager)
                benchmark_results['websocket'] = websocket_optimizations
            
            # Get current performance summary
            performance_summary = self.get_performance_summary(hours=1)
            benchmark_results['current_performance'] = performance_summary
            
            # Get optimization recommendations
            recommendations = self.get_optimization_recommendations()
            benchmark_results['recommendations'] = recommendations
            
            logger.info("Performance benchmark completed")
            
            return benchmark_results
            
        except Exception as e:
            logger.error(f"Error running performance benchmark: {str(e)}")
            return {}
    
    def get_cache_performance(self) -> Dict:
        """Get cache performance metrics"""
        try:
            cache_metrics = {}
            
            # This would be implemented with actual cache statistics
            # For now, return placeholder data
            cache_metrics['hit_rate'] = 85.5
            cache_metrics['miss_rate'] = 14.5
            cache_metrics['avg_access_time_ms'] = 2.3
            cache_metrics['cache_size_mb'] = 45.2
            cache_metrics['eviction_rate'] = 12.1
            
            return cache_metrics
            
        except Exception as e:
            logger.error(f"Error getting cache performance: {str(e)}")
            return {}
    
    def get_connection_pool_status(self) -> Dict:
        """Get connection pool status"""
        try:
            pool_status = {}
            
            # This would be implemented with actual connection pool statistics
            # For now, return placeholder data
            pool_status['active_connections'] = 8
            pool_status['idle_connections'] = 2
            pool_status['max_connections'] = 20
            pool_status['connection_utilization'] = 40.0
            pool_status['avg_connection_time_ms'] = 15.2
            
            return pool_status
            
        except Exception as e:
            logger.error(f"Error getting connection pool status: {str(e)}")
            return {}
    
    def get_optimization_config(self, operation: str) -> Dict:
        """Get optimization configuration for an operation"""
        try:
            if operation not in self.optimization_configs:
                # Create default configuration
                self.optimization_configs[operation] = {
                    'parallel_execution': True,
                    'caching_enabled': True,
                    'cache_ttl_seconds': 30,
                    'batch_size': 10,
                    'timeout_seconds': 30,
                    'retry_attempts': 3,
                    'retry_delay_ms': 1000
                }
            
            return self.optimization_configs[operation]
            
        except Exception as e:
            logger.error(f"Error getting optimization config: {str(e)}")
            return {}
    
    def update_optimization_config(self, operation: str, config: Dict):
        """Update optimization configuration for an operation"""
        try:
            self.optimization_configs[operation] = config
            logger.info(f"Updated optimization config for {operation}")
            
        except Exception as e:
            logger.error(f"Error updating optimization config: {str(e)}")
    
    def get_performance_trends(self, operation: str, hours: int = 24) -> Dict:
        """Get performance trends over time"""
        try:
            if operation not in self.performance_history:
                return {}
            
            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)
            
            recent_metrics = [
                m for m in self.performance_history[operation]
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {}
            
            # Group metrics by hour
            hourly_metrics = {}
            for metric in recent_metrics:
                hour = int(metric.timestamp // 3600) * 3600
                if hour not in hourly_metrics:
                    hourly_metrics[hour] = []
                hourly_metrics[hour].append(metric.duration_ms)
            
            # Calculate trends
            trends = []
            for hour, latencies in sorted(hourly_metrics.items()):
                trends.append({
                    'timestamp': hour,
                    'avg_latency_ms': statistics.mean(latencies),
                    'p95_latency_ms': sorted(latencies)[int(len(latencies) * 0.95)],
                    'operation_count': len(latencies)
                })
            
            return {
                'operation': operation,
                'trends': trends,
                'time_period_hours': hours,
                'total_operations': len(recent_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance trends: {str(e)}")
            return {}
    
    def cleanup_old_metrics(self, days: int = 7):
        """Clean up old performance metrics"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 3600)
            
            cleaned_count = 0
            for operation in self.performance_history:
                original_count = len(self.performance_history[operation])
                self.performance_history[operation] = [
                    m for m in self.performance_history[operation]
                    if m.timestamp >= cutoff_time
                ]
                cleaned_count += original_count - len(self.performance_history[operation])
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old performance metrics")
            
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {str(e)}")

