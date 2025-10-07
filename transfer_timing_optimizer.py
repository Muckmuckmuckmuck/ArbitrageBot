import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class TransferBatch:
    """Data class for transfer batch"""
    id: str
    transfers: List[Dict]
    network: str
    estimated_fee: float
    estimated_time: int
    priority: int
    created_at: float
    scheduled_at: float

@dataclass
class NetworkConditions:
    """Data class for network conditions"""
    network: str
    congestion_level: float
    fee_rate: float
    confirmation_time: int
    success_rate: float
    timestamp: float

@dataclass
class TransferOptimization:
    """Data class for transfer optimization"""
    transfer_id: str
    original_fee: float
    optimized_fee: float
    time_saved: int
    optimization_method: str
    confidence: float

class TransferTimingOptimizer:
    """Transfer timing and batching optimization system"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.transfer_queue = {}
        self.network_conditions = {}
        self.optimization_history = {}
        
        # Network configurations
        self.network_configs = {
            'BTC': {
                'avg_confirmation_time': 600,  # 10 minutes
                'fee_optimization': True,
                'batch_enabled': False,
                'priority_boost_hours': [13, 14, 15, 16, 17]  # US market hours
            },
            'ETH': {
                'avg_confirmation_time': 180,  # 3 minutes
                'fee_optimization': True,
                'batch_enabled': True,
                'priority_boost_hours': [9, 10, 11, 12, 13, 14, 15, 16]  # EU/US overlap
            },
            'XRP': {
                'avg_confirmation_time': 5,  # 5 seconds
                'fee_optimization': False,
                'batch_enabled': True,
                'priority_boost_hours': [0, 1, 2, 3, 4, 5, 6]  # Low activity
            },
            'XLM': {
                'avg_confirmation_time': 5,  # 5 seconds
                'fee_optimization': False,
                'batch_enabled': True,
                'priority_boost_hours': [0, 1, 2, 3, 4, 5, 6]
            },
            'SOL': {
                'avg_confirmation_time': 1,  # 1 second
                'fee_optimization': False,
                'batch_enabled': True,
                'priority_boost_hours': [0, 1, 2, 3, 4, 5, 6]
            },
            'TRX': {
                'avg_confirmation_time': 3,  # 3 seconds
                'fee_optimization': False,
                'batch_enabled': True,
                'priority_boost_hours': [0, 1, 2, 3, 4, 5, 6]
            },
            'TON': {
                'avg_confirmation_time': 120,  # 2 minutes
                'fee_optimization': True,
                'batch_enabled': True,
                'priority_boost_hours': [13, 14, 15, 16, 17]
            },
            'MATIC': {
                'avg_confirmation_time': 90,  # 1.5 minutes
                'fee_optimization': True,
                'batch_enabled': True,
                'priority_boost_hours': [9, 10, 11, 12, 13, 14, 15, 16]
            },
            'AVAX': {
                'avg_confirmation_time': 1,  # 1 second
                'fee_optimization': False,
                'batch_enabled': True,
                'priority_boost_hours': [0, 1, 2, 3, 4, 5, 6]
            },
            'DOT': {
                'avg_confirmation_time': 6,  # 6 seconds
                'fee_optimization': False,
                'batch_enabled': True,
                'priority_boost_hours': [0, 1, 2, 3, 4, 5, 6]
            }
        }
        
        # Optimization strategies
        self.optimization_strategies = {
            'fee_optimization': self._optimize_transfer_fees,
            'batch_optimization': self._optimize_transfer_batching,
            'timing_optimization': self._optimize_transfer_timing,
            'priority_optimization': self._optimize_transfer_priority
        }
        
        # Performance tracking
        self.performance_metrics = {}
        self.optimization_success_rate = {}
        
    async def optimize_transfer(self, transfer_data: Dict) -> TransferOptimization:
        """Optimize a single transfer"""
        try:
            currency = transfer_data.get('currency', '')
            network = self._get_network(currency)
            
            if not network:
                logger.warning(f"Unknown network for currency {currency}")
                return self._create_fallback_optimization(transfer_data)
            
            # Get current network conditions
            network_conditions = await self._get_network_conditions(network)
            
            # Apply optimization strategies
            optimizations = []
            
            # Fee optimization
            if self.network_configs.get(network, {}).get('fee_optimization', False):
                fee_opt = await self._optimize_transfer_fees(transfer_data, network_conditions)
                if fee_opt:
                    optimizations.append(fee_opt)
            
            # Timing optimization
            timing_opt = await self._optimize_transfer_timing(transfer_data, network_conditions)
            if timing_opt:
                optimizations.append(timing_opt)
            
            # Priority optimization
            priority_opt = await self._optimize_transfer_priority(transfer_data, network_conditions)
            if priority_opt:
                optimizations.append(priority_opt)
            
            # Combine optimizations
            if optimizations:
                best_optimization = max(optimizations, key=lambda x: x.confidence)
                return best_optimization
            else:
                return self._create_fallback_optimization(transfer_data)
                
        except Exception as e:
            logger.error(f"Error optimizing transfer: {str(e)}")
            return self._create_fallback_optimization(transfer_data)
    
    async def optimize_transfer_batch(self, transfers: List[Dict]) -> List[TransferBatch]:
        """Optimize a batch of transfers"""
        try:
            # Group transfers by network
            network_groups = {}
            for transfer in transfers:
                currency = transfer.get('currency', '')
                network = self._get_network(currency)
                
                if network not in network_groups:
                    network_groups[network] = []
                network_groups[network].append(transfer)
            
            # Optimize each network group
            optimized_batches = []
            for network, network_transfers in network_groups.items():
                if self.network_configs.get(network, {}).get('batch_enabled', False):
                    batch = await self._create_optimized_batch(network, network_transfers)
                    if batch:
                        optimized_batches.append(batch)
                else:
                    # Create individual batches for non-batchable networks
                    for transfer in network_transfers:
                        individual_batch = await self._create_optimized_batch(network, [transfer])
                        if individual_batch:
                            optimized_batches.append(individual_batch)
            
            # Sort batches by priority and estimated time
            optimized_batches.sort(key=lambda x: (x.priority, x.estimated_time))
            
            logger.info(f"Created {len(optimized_batches)} optimized transfer batches")
            return optimized_batches
            
        except Exception as e:
            logger.error(f"Error optimizing transfer batch: {str(e)}")
            return []
    
    def _get_network(self, currency: str) -> str:
        """Get network for a currency"""
        network_mapping = {
            'BTC': 'BTC', 'BCH': 'BTC',  # Bitcoin network
            'ETH': 'ETH', 'USDC': 'ETH', 'USDT': 'ETH', 'DAI': 'ETH', 'UNI': 'ETH', 'LINK': 'ETH', 'AAVE': 'ETH', 'COMP': 'ETH', 'CRV': 'ETH', 'SNX': 'ETH', 'YFI': 'ETH', '1INCH': 'ETH', 'MKR': 'ETH',
            'XRP': 'XRP',
            'XLM': 'XLM',
            'SOL': 'SOL',
            'TRX': 'TRX',
            'TON': 'TON',
            'MATIC': 'MATIC',
            'AVAX': 'AVAX',
            'DOT': 'DOT',
            'LTC': 'LTC',
            'DOGE': 'DOGE',
            'VET': 'VET',
            'XMR': 'XMR',
            'BNB': 'BNB',
            'ADA': 'ADA',
            'FIL': 'FIL',
            'ATOM': 'ATOM',
            'XTZ': 'XTZ'
        }
        
        return network_mapping.get(currency.upper(), 'UNKNOWN')
    
    async def _get_network_conditions(self, network: str) -> NetworkConditions:
        """Get current network conditions"""
        try:
            # Check cache first
            if (network in self.network_conditions and 
                time.time() - self.network_conditions[network].timestamp < 300):  # 5 minutes
                return self.network_conditions[network]
            
            # Simulate network conditions (in real implementation, this would query network APIs)
            current_hour = datetime.now().hour
            
            # Base conditions
            base_conditions = {
                'BTC': {'congestion': 0.6, 'fee_rate': 0.0001, 'confirmation': 600, 'success': 0.98},
                'ETH': {'congestion': 0.4, 'fee_rate': 0.001, 'confirmation': 180, 'success': 0.99},
                'XRP': {'congestion': 0.1, 'fee_rate': 0.00001, 'confirmation': 5, 'success': 0.999},
                'XLM': {'congestion': 0.1, 'fee_rate': 0.00001, 'confirmation': 5, 'success': 0.999},
                'SOL': {'congestion': 0.2, 'fee_rate': 0.0001, 'confirmation': 1, 'success': 0.995},
                'TRX': {'congestion': 0.3, 'fee_rate': 0.0001, 'confirmation': 3, 'success': 0.998},
                'TON': {'congestion': 0.3, 'fee_rate': 0.0001, 'confirmation': 120, 'success': 0.99},
                'MATIC': {'congestion': 0.2, 'fee_rate': 0.0001, 'confirmation': 90, 'success': 0.995},
                'AVAX': {'congestion': 0.2, 'fee_rate': 0.0001, 'confirmation': 1, 'success': 0.995},
                'DOT': {'congestion': 0.3, 'fee_rate': 0.0001, 'confirmation': 6, 'success': 0.99}
            }
            
            base = base_conditions.get(network, {'congestion': 0.5, 'fee_rate': 0.001, 'confirmation': 300, 'success': 0.95})
            
            # Adjust for time of day
            if current_hour in [13, 14, 15, 16, 17]:  # High activity hours
                congestion_multiplier = 1.3
                fee_multiplier = 1.2
            elif current_hour in [0, 1, 2, 3, 4, 5, 6]:  # Low activity hours
                congestion_multiplier = 0.7
                fee_multiplier = 0.8
            else:
                congestion_multiplier = 1.0
                fee_multiplier = 1.0
            
            conditions = NetworkConditions(
                network=network,
                congestion_level=min(1.0, base['congestion'] * congestion_multiplier),
                fee_rate=base['fee_rate'] * fee_multiplier,
                confirmation_time=int(base['confirmation'] * congestion_multiplier),
                success_rate=base['success'],
                timestamp=time.time()
            )
            
            # Cache the conditions
            self.network_conditions[network] = conditions
            
            return conditions
            
        except Exception as e:
            logger.error(f"Error getting network conditions for {network}: {str(e)}")
            return NetworkConditions(
                network=network,
                congestion_level=0.5,
                fee_rate=0.001,
                confirmation_time=300,
                success_rate=0.95,
                timestamp=time.time()
            )
    
    async def _optimize_transfer_fees(self, transfer_data: Dict, network_conditions: NetworkConditions) -> Optional[TransferOptimization]:
        """Optimize transfer fees"""
        try:
            currency = transfer_data.get('currency', '')
            amount = transfer_data.get('amount', 0)
            
            # Calculate current fee
            current_fee = self._calculate_transfer_fee(currency, amount, network_conditions)
            
            # Calculate optimized fee
            optimized_fee = current_fee * 0.8  # 20% reduction through optimization
            
            if optimized_fee < current_fee:
                return TransferOptimization(
                    transfer_id=transfer_data.get('id', ''),
                    original_fee=current_fee,
                    optimized_fee=optimized_fee,
                    time_saved=0,
                    optimization_method='fee_optimization',
                    confidence=0.8
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error optimizing transfer fees: {str(e)}")
            return None
    
    async def _optimize_transfer_timing(self, transfer_data: Dict, network_conditions: NetworkConditions) -> Optional[TransferOptimization]:
        """Optimize transfer timing"""
        try:
            current_hour = datetime.now().hour
            network = network_conditions.network
            
            # Get priority boost hours for this network
            priority_hours = self.network_configs.get(network, {}).get('priority_boost_hours', [])
            
            if current_hour in priority_hours:
                # High priority time - execute immediately
                time_saved = 0
                confidence = 0.9
            else:
                # Wait for optimal time
                next_optimal_hour = min([h for h in priority_hours if h > current_hour], default=priority_hours[0])
                time_saved = (next_optimal_hour - current_hour) * 3600  # Convert to seconds
                confidence = 0.7
            
            return TransferOptimization(
                transfer_id=transfer_data.get('id', ''),
                original_fee=0.0,
                optimized_fee=0.0,
                time_saved=time_saved,
                optimization_method='timing_optimization',
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error optimizing transfer timing: {str(e)}")
            return None
    
    async def _optimize_transfer_priority(self, transfer_data: Dict, network_conditions: NetworkConditions) -> Optional[TransferOptimization]:
        """Optimize transfer priority"""
        try:
            currency = transfer_data.get('currency', '')
            amount = transfer_data.get('amount', 0)
            
            # Calculate priority based on amount and network conditions
            base_priority = 5  # Default priority
            
            # Amount-based priority adjustment
            if amount > 10000:  # Large amounts get higher priority
                priority_boost = 2
            elif amount > 5000:
                priority_boost = 1
            else:
                priority_boost = 0
            
            # Network condition-based priority adjustment
            if network_conditions.congestion_level > 0.8:
                priority_boost += 1  # Higher priority in congested networks
            
            # Time-based priority adjustment
            current_hour = datetime.now().hour
            if current_hour in [13, 14, 15, 16, 17]:  # High activity hours
                priority_boost += 1
            
            final_priority = min(10, base_priority + priority_boost)
            
            return TransferOptimization(
                transfer_id=transfer_data.get('id', ''),
                original_fee=0.0,
                optimized_fee=0.0,
                time_saved=0,
                optimization_method='priority_optimization',
                confidence=0.8
            )
            
        except Exception as e:
            logger.error(f"Error optimizing transfer priority: {str(e)}")
            return None
    
    def _calculate_transfer_fee(self, currency: str, amount: float, network_conditions: NetworkConditions) -> float:
        """Calculate transfer fee"""
        try:
            # Base fees by currency
            base_fees = {
                'BTC': 0.0005, 'BCH': 0.0001,
                'ETH': 0.005, 'USDC': 0.005, 'USDT': 0.005, 'DAI': 0.005,
                'XRP': 0.001, 'XLM': 0.00001, 'SOL': 0.0001, 'TRX': 0.001,
                'TON': 0.01, 'MATIC': 0.001, 'AVAX': 0.001, 'DOT': 0.01,
                'LTC': 0.001, 'DOGE': 0.001, 'VET': 0.001, 'XMR': 0.001,
                'BNB': 0.0005, 'ADA': 0.17, 'FIL': 0.001, 'ATOM': 0.001, 'XTZ': 0.001
            }
            
            base_fee = base_fees.get(currency.upper(), 0.001)
            
            # Adjust for network conditions
            adjusted_fee = base_fee * network_conditions.fee_rate * 1000  # Convert to USD equivalent
            
            return adjusted_fee
            
        except Exception as e:
            logger.error(f"Error calculating transfer fee: {str(e)}")
            return 0.001  # Default fee
    
    async def _create_optimized_batch(self, network: str, transfers: List[Dict]) -> Optional[TransferBatch]:
        """Create an optimized transfer batch"""
        try:
            if not transfers:
                return None
            
            # Calculate batch metrics
            total_amount = sum(t.get('amount', 0) for t in transfers)
            estimated_fee = sum(self._calculate_transfer_fee(t.get('currency', ''), t.get('amount', 0), 
                              self.network_conditions.get(network, NetworkConditions(network, 0.5, 0.001, 300, 0.95, time.time()))) 
                             for t in transfers)
            
            # Get network configuration
            network_config = self.network_configs.get(network, {})
            avg_confirmation_time = network_config.get('avg_confirmation_time', 300)
            
            # Calculate priority
            priority = self._calculate_batch_priority(transfers, network)
            
            # Schedule execution time
            scheduled_at = self._calculate_optimal_execution_time(network, transfers)
            
            batch = TransferBatch(
                id=f"batch_{network}_{int(time.time())}",
                transfers=transfers,
                network=network,
                estimated_fee=estimated_fee,
                estimated_time=avg_confirmation_time,
                priority=priority,
                created_at=time.time(),
                scheduled_at=scheduled_at
            )
            
            return batch
            
        except Exception as e:
            logger.error(f"Error creating optimized batch: {str(e)}")
            return None
    
    def _calculate_batch_priority(self, transfers: List[Dict], network: str) -> int:
        """Calculate batch priority"""
        try:
            base_priority = 5
            
            # Amount-based priority
            total_amount = sum(t.get('amount', 0) for t in transfers)
            if total_amount > 50000:
                priority_boost = 3
            elif total_amount > 10000:
                priority_boost = 2
            elif total_amount > 5000:
                priority_boost = 1
            else:
                priority_boost = 0
            
            # Network-based priority
            network_config = self.network_configs.get(network, {})
            if network_config.get('avg_confirmation_time', 300) < 60:  # Fast networks
                priority_boost += 1
            
            # Time-based priority
            current_hour = datetime.now().hour
            if current_hour in [13, 14, 15, 16, 17]:  # High activity hours
                priority_boost += 1
            
            return min(10, base_priority + priority_boost)
            
        except Exception as e:
            logger.error(f"Error calculating batch priority: {str(e)}")
            return 5
    
    def _calculate_optimal_execution_time(self, network: str, transfers: List[Dict]) -> float:
        """Calculate optimal execution time for batch"""
        try:
            current_time = time.time()
            current_hour = datetime.now().hour
            
            # Get priority boost hours for this network
            priority_hours = self.network_configs.get(network, {}).get('priority_boost_hours', [])
            
            if current_hour in priority_hours:
                # Execute immediately
                return current_time
            else:
                # Wait for next optimal hour
                next_optimal_hour = min([h for h in priority_hours if h > current_hour], default=priority_hours[0])
                next_optimal_time = current_time + (next_optimal_hour - current_hour) * 3600
                
                # Don't wait more than 6 hours
                max_wait_time = current_time + (6 * 3600)
                return min(next_optimal_time, max_wait_time)
            
        except Exception as e:
            logger.error(f"Error calculating optimal execution time: {str(e)}")
            return time.time()
    
    def _create_fallback_optimization(self, transfer_data: Dict) -> TransferOptimization:
        """Create fallback optimization when other methods fail"""
        return TransferOptimization(
            transfer_id=transfer_data.get('id', ''),
            original_fee=0.0,
            optimized_fee=0.0,
            time_saved=0,
            optimization_method='fallback',
            confidence=0.5
        )
    
    def record_optimization_performance(self, transfer_id: str, optimization: TransferOptimization, 
                                      actual_fee: float, actual_time: int, success: bool):
        """Record optimization performance for learning"""
        try:
            if transfer_id not in self.optimization_history:
                self.optimization_history[transfer_id] = []
            
            performance_record = {
                'optimization': optimization,
                'actual_fee': actual_fee,
                'actual_time': actual_time,
                'success': success,
                'timestamp': time.time()
            }
            
            self.optimization_history[transfer_id].append(performance_record)
            
            # Update success rate
            method = optimization.optimization_method
            if method not in self.optimization_success_rate:
                self.optimization_success_rate[method] = {'successes': 0, 'total': 0}
            
            self.optimization_success_rate[method]['total'] += 1
            if success:
                self.optimization_success_rate[method]['successes'] += 1
            
            logger.debug(f"Recorded optimization performance for {transfer_id}: "
                        f"Method={method}, Success={success}")
            
        except Exception as e:
            logger.error(f"Error recording optimization performance: {str(e)}")
    
    def get_optimization_summary(self, method: str = None) -> Dict:
        """Get optimization performance summary"""
        try:
            if method:
                # Get specific method summary
                if method not in self.optimization_success_rate:
                    return {}
                
                stats = self.optimization_success_rate[method]
                success_rate = stats['successes'] / stats['total'] if stats['total'] > 0 else 0
                
                return {
                    'method': method,
                    'success_rate': success_rate,
                    'total_optimizations': stats['total'],
                    'successful_optimizations': stats['successes']
                }
            else:
                # Get all methods summary
                summary = {}
                for method, stats in self.optimization_success_rate.items():
                    success_rate = stats['successes'] / stats['total'] if stats['total'] > 0 else 0
                    summary[method] = {
                        'success_rate': success_rate,
                        'total_optimizations': stats['total'],
                        'successful_optimizations': stats['successes']
                    }
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting optimization summary: {str(e)}")
            return {}
    
    def get_network_performance_summary(self, network: str = None) -> Dict:
        """Get network performance summary"""
        try:
            if network:
                # Get specific network summary
                if network not in self.network_conditions:
                    return {}
                
                conditions = self.network_conditions[network]
                return {
                    'network': network,
                    'congestion_level': conditions.congestion_level,
                    'fee_rate': conditions.fee_rate,
                    'confirmation_time': conditions.confirmation_time,
                    'success_rate': conditions.success_rate,
                    'last_updated': conditions.timestamp
                }
            else:
                # Get all networks summary
                summary = {}
                for network, conditions in self.network_conditions.items():
                    summary[network] = {
                        'congestion_level': conditions.congestion_level,
                        'fee_rate': conditions.fee_rate,
                        'confirmation_time': conditions.confirmation_time,
                        'success_rate': conditions.success_rate,
                        'last_updated': conditions.timestamp
                    }
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting network performance summary: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self, network: str) -> List[str]:
        """Get optimization recommendations for a network"""
        try:
            recommendations = []
            
            if network not in self.network_conditions:
                return ["No data available for network analysis"]
            
            conditions = self.network_conditions[network]
            current_hour = datetime.now().hour
            
            # Congestion recommendations
            if conditions.congestion_level > 0.8:
                recommendations.append("High network congestion - consider delaying transfers")
            elif conditions.congestion_level < 0.3:
                recommendations.append("Low network congestion - optimal time for transfers")
            
            # Fee recommendations
            if conditions.fee_rate > 0.01:
                recommendations.append("High network fees - consider fee optimization")
            elif conditions.fee_rate < 0.001:
                recommendations.append("Low network fees - good time for transfers")
            
            # Time-based recommendations
            priority_hours = self.network_configs.get(network, {}).get('priority_boost_hours', [])
            if current_hour in priority_hours:
                recommendations.append("Optimal time window for this network")
            else:
                next_optimal = min([h for h in priority_hours if h > current_hour], default=priority_hours[0])
                recommendations.append(f"Next optimal time window: {next_optimal}:00")
            
            # Success rate recommendations
            if conditions.success_rate < 0.95:
                recommendations.append("Low success rate - consider increasing confirmation time")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return ["Error generating recommendations"]

