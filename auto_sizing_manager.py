#!/usr/bin/env python3
"""
Auto-Sizing Manager
Automatically adjusts position sizes based on performance
"""

import logging
from typing import Dict, Any, List, Tuple
from collections import deque
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TradeResult:
    """Store trade result for performance tracking"""
    symbol: str
    timestamp: datetime
    position_size: float
    entry_price: float
    exit_price: float
    profit: float
    profit_percent: float
    success: bool
    slippage: float

class AutoSizingManager:
    """Manages automatic position sizing based on performance"""
    
    def __init__(self, config):
        self.config = config
        self.base_positions = config.BASE_POSITION_PERCENTAGES.copy()
        self.current_positions = config.BASE_POSITION_PERCENTAGES.copy()
        
        # Track trade history per crypto
        self.trade_history: Dict[str, deque] = {}
        for symbol in config.CURRENCY_PAIRS:
            self.trade_history[symbol] = deque(maxlen=config.AUTO_SIZING['lookback_trades'])
        
        # Performance metrics
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Auto-Sizing Manager initialized")
    
    def record_trade(self, trade_result: TradeResult):
        """Record a trade result"""
        symbol = trade_result.symbol
        
        if symbol not in self.trade_history:
            self.trade_history[symbol] = deque(maxlen=self.config.AUTO_SIZING['lookback_trades'])
        
        self.trade_history[symbol].append(trade_result)
        
        # Update position size if enough trades
        if len(self.trade_history[symbol]) >= self.config.AUTO_SIZING['scale_interval_trades']:
            self._update_position_size(symbol)
        
        logger.info(f"Recorded trade for {symbol}: "
                   f"Profit: ${trade_result.profit:.2f} ({trade_result.profit_percent*100:.2f}%), "
                   f"Success: {trade_result.success}")
    
    def _update_position_size(self, symbol: str):
        """Update position size based on recent performance"""
        if not self.config.AUTO_SIZING['enabled']:
            return
        
        trades = list(self.trade_history[symbol])
        if len(trades) < self.config.AUTO_SIZING['scale_interval_trades']:
            return
        
        # Calculate recent performance
        recent_trades = trades[-self.config.AUTO_SIZING['scale_interval_trades']:]
        wins = sum(1 for t in recent_trades if t.success)
        win_rate = wins / len(recent_trades)
        
        avg_profit = sum(t.profit_percent for t in recent_trades) / len(recent_trades)
        
        current_size = self.current_positions[symbol]
        base_size = self.base_positions[symbol]
        
        # Determine if we should scale up or down
        if win_rate >= self.config.AUTO_SIZING['min_win_rate'] and avg_profit > 0:
            # Scale up
            new_size = current_size * self.config.AUTO_SIZING['scale_up_factor']
            logger.info(f"✅ {symbol}: Scaling UP position size "
                       f"({current_size*100:.1f}% → {new_size*100:.1f}%) "
                       f"Win rate: {win_rate*100:.1f}%, Avg profit: {avg_profit*100:.2f}%")
        elif win_rate < self.config.AUTO_SIZING['min_win_rate'] or avg_profit < 0:
            # Scale down
            new_size = current_size * self.config.AUTO_SIZING['scale_down_factor']
            logger.warning(f"⚠️  {symbol}: Scaling DOWN position size "
                          f"({current_size*100:.1f}% → {new_size*100:.1f}%) "
                          f"Win rate: {win_rate*100:.1f}%, Avg profit: {avg_profit*100:.2f}%")
        else:
            # Keep current size
            return
        
        # Apply bounds
        new_size = max(self.config.AUTO_SIZING['min_position_percent'], new_size)
        new_size = min(self.config.AUTO_SIZING['max_position_percent'], new_size)
        
        # Don't go below base size by more than 50%
        new_size = max(base_size * 0.5, new_size)
        
        self.current_positions[symbol] = new_size
        
        # Update performance metrics
        self._update_performance_metrics(symbol, win_rate, avg_profit)
    
    def _update_performance_metrics(self, symbol: str, win_rate: float, avg_profit: float):
        """Update performance metrics for a symbol"""
        trades = list(self.trade_history[symbol])
        
        self.performance_metrics[symbol] = {
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_profit_percent': avg_profit,
            'current_position_size': self.current_positions[symbol],
            'base_position_size': self.base_positions[symbol],
            'size_multiplier': self.current_positions[symbol] / self.base_positions[symbol],
            'total_profit': sum(t.profit for t in trades),
            'avg_slippage': sum(t.slippage for t in trades) / len(trades) if trades else 0,
        }
    
    def get_position_size(self, symbol: str, spread: float, account_balance: float) -> float:
        """Get dynamic position size for a symbol"""
        
        # Get base position size (auto-adjusted)
        base_percent = self.current_positions.get(symbol, 0.10)
        
        # Apply dynamic sizing based on spread (if enabled)
        if self.config.DYNAMIC_POSITION_SIZING['enabled'] and self.config.DYNAMIC_POSITION_SIZING['spread_multiplier']:
            min_spread = self.config.CURRENCY_PAIR_SPREADS[symbol]['min_spread']
            max_multiplier = self.config.DYNAMIC_POSITION_SIZING['max_multiplier']
            
            # Bigger spread = bigger position (up to max_multiplier)
            spread_multiplier = min(spread / min_spread, max_multiplier)
            adjusted_percent = base_percent * spread_multiplier
            
            # Apply bounds
            adjusted_percent = min(adjusted_percent, self.config.RISK_MANAGEMENT['max_position_percent'])
            adjusted_percent = max(adjusted_percent, self.config.RISK_MANAGEMENT['min_position_percent'])
        else:
            adjusted_percent = base_percent
        
        # Calculate dollar amount
        position_size = account_balance * adjusted_percent
        
        logger.debug(f"{symbol}: Base {base_percent*100:.1f}%, "
                    f"Adjusted {adjusted_percent*100:.1f}%, "
                    f"Size ${position_size:,.2f}")
        
        return position_size
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        report = {
            'per_crypto': self.performance_metrics,
            'overall': self._calculate_overall_metrics(),
            'timestamp': datetime.now().isoformat(),
        }
        return report
    
    def _calculate_overall_metrics(self) -> Dict[str, Any]:
        """Calculate overall portfolio metrics"""
        all_trades = []
        for trades in self.trade_history.values():
            all_trades.extend(trades)
        
        if not all_trades:
            return {}
        
        wins = sum(1 for t in all_trades if t.success)
        total_profit = sum(t.profit for t in all_trades)
        avg_profit_percent = sum(t.profit_percent for t in all_trades) / len(all_trades)
        avg_slippage = sum(t.slippage for t in all_trades) / len(all_trades)
        
        return {
            'total_trades': len(all_trades),
            'win_rate': wins / len(all_trades),
            'total_profit': total_profit,
            'avg_profit_percent': avg_profit_percent,
            'avg_slippage': avg_slippage,
            'best_crypto': max(self.performance_metrics.items(), 
                             key=lambda x: x[1]['win_rate'])[0] if self.performance_metrics else None,
            'worst_crypto': min(self.performance_metrics.items(), 
                              key=lambda x: x[1]['win_rate'])[0] if self.performance_metrics else None,
        }
    
    def reset_position_size(self, symbol: str):
        """Reset position size to base for a symbol"""
        self.current_positions[symbol] = self.base_positions[symbol]
        logger.info(f"Reset {symbol} position size to base: {self.base_positions[symbol]*100:.1f}%")
    
    def reset_all_position_sizes(self):
        """Reset all position sizes to base"""
        self.current_positions = self.base_positions.copy()
        logger.info("Reset all position sizes to base values")

