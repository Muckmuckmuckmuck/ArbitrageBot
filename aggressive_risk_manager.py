#!/usr/bin/env python3
"""
Aggressive risk management for high-frequency arbitrage
Allows for multiple concurrent opportunities while maintaining capital efficiency
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class ActivePosition:
    """Data class for active arbitrage position"""
    symbol: str
    position_id: str
    amount: float
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    expected_profit: float
    start_time: float
    status: str = "active"
    risk_level: str = "medium"

class AggressiveRiskManager:
    """Aggressive risk management for high-frequency arbitrage"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.active_positions = {}
        self.position_history = []
        self.daily_trade_count = 0
        self.daily_profit = 0.0
        self.last_reset_time = time.time()
        
        # Aggressive risk parameters
        self.risk_config = {
            'max_position_percent': 0.15,  # 15% of balance per position
            'max_concurrent_trades': 4,    # Maximum 4 concurrent trades
            'reserve_percent': 0.20,       # Keep 20% in reserve
            'max_total_exposure': 0.60,    # Maximum 60% of balance in active trades
            'position_scaling': {
                'ultra_fast': 0.20,        # 20% for ultra-fast assets
                'high_liquidity': 0.15,    # 15% for high-liquidity assets
                'stablecoins': 0.10,      # 10% for stablecoins
            },
            'min_spread_threshold': 0.0003, # 0.03% minimum spread
            'max_slippage': 0.002,         # 0.2% maximum slippage
            'stop_loss_percent': 0.005,    # 0.5% stop loss
            'cooldown_period': 10,         # 10 seconds between trades
        }
        
        # Performance tracking
        self.performance_metrics = {
            'total_trades': 0,
            'successful_trades': 0,
            'total_profit': 0.0,
            'max_drawdown': 0.0,
            'current_drawdown': 0.0,
            'peak_balance': 0.0,
        }
    
    async def can_open_position(self, symbol: str, amount: float, opportunity_data: Dict) -> Tuple[bool, str]:
        """Check if we can open a new position"""
        try:
            # Get current balance
            current_balance = await self._get_total_balance()
            if current_balance <= 0:
                return False, "No balance available"
            
            # Check if we have too many concurrent trades
            if len(self.active_positions) >= self.risk_config['max_concurrent_trades']:
                return False, f"Maximum concurrent trades reached ({self.risk_config['max_concurrent_trades']})"
            
            # Check if we have enough reserve
            total_exposure = sum(pos.amount for pos in self.active_positions.values())
            max_exposure = current_balance * self.risk_config['max_total_exposure']
            if total_exposure + amount > max_exposure:
                return False, f"Total exposure limit reached ({self.risk_config['max_total_exposure']:.1%})"
            
            # Check position size limits
            position_percent = amount / current_balance
            max_position_percent = self._get_max_position_percent(symbol)
            if position_percent > max_position_percent:
                return False, f"Position size too large ({position_percent:.1%} > {max_position_percent:.1%})"
            
            # Check spread threshold
            spread_percent = opportunity_data.get('spread_percent', 0)
            if spread_percent < self.risk_config['min_spread_threshold']:
                return False, f"Spread too small ({spread_percent:.4f} < {self.risk_config['min_spread_threshold']:.4f})"
            
            # Check cooldown period
            if not self._check_cooldown_period():
                return False, "Cooldown period active"
            
            return True, "Position approved"
            
        except Exception as e:
            logger.error(f"Error checking position eligibility: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def _get_max_position_percent(self, symbol: str) -> float:
        """Get maximum position percentage based on asset type"""
        try:
            # Determine asset type
            if symbol in ['XRP/USDT', 'XLM/USDT', 'SOL/USDT', 'EOS/USDT', 'TRX/USDT', 
                         'BNB/USDT', 'AVAX/USDT', 'DOT/USDT', 'ADA/USDT', 'MATIC/USDT']:
                return self.risk_config['position_scaling']['ultra_fast']
            elif symbol in ['BTC/USDT', 'ETH/USDT', 'LTC/USDT', 'DOGE/USDT', 
                           'UNI/USDT', 'LINK/USDT', 'TON/USDT']:
                return self.risk_config['position_scaling']['high_liquidity']
            elif symbol in ['USDT/USDC', 'USDC/USDT', 'DAI/USDT', 'BUSD/USDT', 'USDT/BUSD']:
                return self.risk_config['position_scaling']['stablecoins']
            else:
                return self.risk_config['max_position_percent']
                
        except Exception as e:
            logger.error(f"Error getting max position percent: {str(e)}")
            return self.risk_config['max_position_percent']
    
    def _check_cooldown_period(self) -> bool:
        """Check if cooldown period has passed"""
        try:
            if not self.active_positions:
                return True
            
            # Check if enough time has passed since last trade
            last_trade_time = max(pos.start_time for pos in self.active_positions.values())
            cooldown_period = self.risk_config['cooldown_period']
            
            return time.time() - last_trade_time >= cooldown_period
            
        except Exception as e:
            logger.error(f"Error checking cooldown period: {str(e)}")
            return True
    
    async def _get_total_balance(self) -> float:
        """Get total balance across all exchanges"""
        try:
            total_balance = 0.0
            
            for exchange_name in ['binance', 'okx']:
                try:
                    exchange = self.exchange_manager.get_exchange(exchange_name)
                    balances = await exchange.get_balances()
                    
                    for currency, balance_data in balances.items():
                        if balance_data.get('total', 0) > 0:
                            # Convert to USD (simplified)
                            if currency in ['USDT', 'USDC', 'BUSD', 'DAI']:
                                total_balance += balance_data['total']
                            else:
                                # Assume $1 for other currencies (simplified)
                                total_balance += balance_data['total']
                                
                except Exception as e:
                    logger.error(f"Error getting balance from {exchange_name}: {str(e)}")
                    continue
            
            return total_balance
            
        except Exception as e:
            logger.error(f"Error getting total balance: {str(e)}")
            return 0.0
    
    async def open_position(self, symbol: str, amount: float, opportunity_data: Dict) -> Optional[str]:
        """Open a new arbitrage position"""
        try:
            # Check if we can open the position
            can_open, reason = await self.can_open_position(symbol, amount, opportunity_data)
            if not can_open:
                logger.warning(f"Cannot open position for {symbol}: {reason}")
                return None
            
            # Create position
            position_id = f"{symbol}_{int(time.time())}"
            position = ActivePosition(
                symbol=symbol,
                position_id=position_id,
                amount=amount,
                buy_exchange=opportunity_data['buy_exchange'],
                sell_exchange=opportunity_data['sell_exchange'],
                buy_price=opportunity_data['buy_price'],
                sell_price=opportunity_data['sell_price'],
                expected_profit=opportunity_data.get('estimated_profit', 0),
                start_time=time.time(),
                status="active",
                risk_level=self._determine_risk_level(symbol, amount)
            )
            
            # Add to active positions
            self.active_positions[position_id] = position
            self.daily_trade_count += 1
            
            logger.info(f"Opened position {position_id}: {amount} {symbol} "
                       f"({position.expected_profit:.4f} expected profit)")
            
            return position_id
            
        except Exception as e:
            logger.error(f"Error opening position: {str(e)}")
            return None
    
    def _determine_risk_level(self, symbol: str, amount: float) -> str:
        """Determine risk level for position"""
        try:
            # Ultra-fast assets are lower risk
            if symbol in ['XRP/USDT', 'XLM/USDT', 'SOL/USDT', 'EOS/USDT', 'TRX/USDT']:
                return 'low'
            # High-liquidity assets are medium risk
            elif symbol in ['BTC/USDT', 'ETH/USDT', 'LTC/USDT', 'DOGE/USDT']:
                return 'medium'
            # Stablecoins are lowest risk
            elif symbol in ['USDT/USDC', 'USDC/USDT', 'DAI/USDT', 'BUSD/USDT']:
                return 'very_low'
            else:
                return 'medium'
                
        except Exception as e:
            logger.error(f"Error determining risk level: {str(e)}")
            return 'medium'
    
    async def close_position(self, position_id: str, actual_profit: float, success: bool) -> bool:
        """Close an arbitrage position"""
        try:
            if position_id not in self.active_positions:
                logger.warning(f"Position {position_id} not found")
                return False
            
            position = self.active_positions[position_id]
            
            # Update position status
            position.status = "completed" if success else "failed"
            
            # Update performance metrics
            self.performance_metrics['total_trades'] += 1
            if success:
                self.performance_metrics['successful_trades'] += 1
                self.performance_metrics['total_profit'] += actual_profit
                self.daily_profit += actual_profit
            
            # Move to history
            self.position_history.append(position)
            del self.active_positions[position_id]
            
            # Update drawdown
            await self._update_drawdown()
            
            logger.info(f"Closed position {position_id}: {actual_profit:.4f} profit, "
                       f"Success: {success}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return False
    
    async def _update_drawdown(self) -> None:
        """Update drawdown metrics"""
        try:
            current_balance = await self._get_total_balance()
            
            # Update peak balance
            if current_balance > self.performance_metrics['peak_balance']:
                self.performance_metrics['peak_balance'] = current_balance
                self.performance_metrics['current_drawdown'] = 0.0
            else:
                # Calculate current drawdown
                peak = self.performance_metrics['peak_balance']
                if peak > 0:
                    self.performance_metrics['current_drawdown'] = (peak - current_balance) / peak
                    
                    # Update max drawdown
                    if self.performance_metrics['current_drawdown'] > self.performance_metrics['max_drawdown']:
                        self.performance_metrics['max_drawdown'] = self.performance_metrics['current_drawdown']
            
        except Exception as e:
            logger.error(f"Error updating drawdown: {str(e)}")
    
    def get_risk_summary(self) -> Dict:
        """Get risk management summary"""
        try:
            current_balance = asyncio.run(self._get_total_balance())
            total_exposure = sum(pos.amount for pos in self.active_positions.values())
            
            return {
                'current_balance': current_balance,
                'total_exposure': total_exposure,
                'exposure_percent': total_exposure / current_balance if current_balance > 0 else 0,
                'active_positions': len(self.active_positions),
                'max_concurrent': self.risk_config['max_concurrent_trades'],
                'reserve_available': current_balance * self.risk_config['reserve_percent'],
                'performance_metrics': self.performance_metrics,
                'risk_config': self.risk_config
            }
            
        except Exception as e:
            logger.error(f"Error getting risk summary: {str(e)}")
            return {}
    
    def get_position_recommendations(self) -> List[str]:
        """Get recommendations for position management"""
        try:
            recommendations = []
            
            # Check exposure
            current_balance = asyncio.run(self._get_total_balance())
            total_exposure = sum(pos.amount for pos in self.active_positions.values())
            exposure_percent = total_exposure / current_balance if current_balance > 0 else 0
            
            if exposure_percent > 0.5:
                recommendations.append(f"High exposure: {exposure_percent:.1%} of balance in active trades")
            
            # Check concurrent trades
            if len(self.active_positions) >= self.risk_config['max_concurrent_trades']:
                recommendations.append(f"Maximum concurrent trades reached: {len(self.active_positions)}")
            
            # Check success rate
            if self.performance_metrics['total_trades'] > 10:
                success_rate = self.performance_metrics['successful_trades'] / self.performance_metrics['total_trades']
                if success_rate < 0.7:
                    recommendations.append(f"Low success rate: {success_rate:.1%}")
            
            # Check drawdown
            if self.performance_metrics['current_drawdown'] > 0.05:
                recommendations.append(f"Current drawdown: {self.performance_metrics['current_drawdown']:.1%}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            return ["Error generating recommendations"]

if __name__ == "__main__":
    print("AGGRESSIVE RISK MANAGEMENT FOR HIGH-FREQUENCY ARBITRAGE")
    print("=" * 60)
    print("Key Features:")
    print("• 15% max position per trade (vs 5% conservative)")
    print("• 4 concurrent trades maximum")
    print("• 20% reserve for new opportunities")
    print("• 60% max total exposure")
    print("• Position scaling based on asset type")
    print("• Faster execution (10s cooldown)")
    print("• Higher tolerance for slippage and stop-loss")
    print()
    print("This allows for more aggressive capital utilization")
    print("while maintaining proper risk management.")

