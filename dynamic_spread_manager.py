#!/usr/bin/env python3
"""
Dynamic Spread Manager
Automatically adjusts spread requirements based on market conditions and performance
"""

import logging
from typing import Dict, Any, List, Tuple
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SpreadOpportunity:
    """Store spread opportunity data"""
    symbol: str
    timestamp: datetime
    spread: float
    traded: bool
    success: bool
    profit: float = 0.0

class DynamicSpreadManager:
    """Manages dynamic spread requirements"""
    
    def __init__(self, config):
        self.config = config
        self.base_spreads = {}
        self.current_spreads = {}
        
        # Initialize spreads from config
        for symbol, data in config.CURRENCY_PAIR_SPREADS.items():
            self.base_spreads[symbol] = data['min_spread']
            self.current_spreads[symbol] = data['min_spread']
        
        # Track spread opportunities
        self.spread_history: Dict[str, deque] = {}
        for symbol in config.CURRENCY_PAIRS:
            self.spread_history[symbol] = deque(maxlen=1000)  # Last 1000 opportunities
        
        # Last adjustment time
        self.last_adjustment = {}
        for symbol in config.CURRENCY_PAIRS:
            self.last_adjustment[symbol] = datetime.now()
        
        logger.info("Dynamic Spread Manager initialized")
    
    def record_spread_opportunity(self, opportunity: SpreadOpportunity):
        """Record a spread opportunity"""
        symbol = opportunity.symbol
        
        if symbol not in self.spread_history:
            self.spread_history[symbol] = deque(maxlen=1000)
        
        self.spread_history[symbol].append(opportunity)
        
        # Check if we should adjust spread requirements
        self._check_adjustment_needed(symbol)
    
    def _check_adjustment_needed(self, symbol: str):
        """Check if spread adjustment is needed"""
        if not self.config.DYNAMIC_SPREADS['enabled']:
            return
        
        # Check if enough time has passed since last adjustment
        adjustment_interval = timedelta(minutes=self.config.DYNAMIC_SPREADS['adjustment_interval_minutes'])
        if datetime.now() - self.last_adjustment[symbol] < adjustment_interval:
            return
        
        # Analyze recent performance
        lookback_hours = self.config.DYNAMIC_SPREADS['lookback_hours']
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        
        recent_opportunities = [
            opp for opp in self.spread_history[symbol]
            if opp.timestamp > cutoff_time and opp.traded
        ]
        
        if len(recent_opportunities) < 10:  # Need at least 10 trades
            return
        
        # Calculate success rate
        successes = sum(1 for opp in recent_opportunities if opp.success)
        success_rate = successes / len(recent_opportunities)
        
        # Adjust spread based on success rate
        self._adjust_spread(symbol, success_rate)
        
        self.last_adjustment[symbol] = datetime.now()
    
    def _adjust_spread(self, symbol: str, success_rate: float):
        """Adjust spread requirement based on success rate"""
        current_spread = self.current_spreads[symbol]
        base_spread = self.base_spreads[symbol]
        
        high_success = self.config.DYNAMIC_SPREADS['high_success_rate']
        low_success = self.config.DYNAMIC_SPREADS['low_success_rate']
        adjustment_percent = self.config.DYNAMIC_SPREADS['spread_adjustment_percent']
        
        if success_rate >= high_success:
            # High success rate = lower spread requirement
            new_spread = current_spread * (1 - adjustment_percent)
            logger.info(f"✅ {symbol}: Lowering spread requirement "
                       f"({current_spread*100:.2f}% → {new_spread*100:.2f}%) "
                       f"Success rate: {success_rate*100:.1f}%")
        elif success_rate <= low_success:
            # Low success rate = higher spread requirement
            new_spread = current_spread * (1 + adjustment_percent)
            logger.warning(f"⚠️  {symbol}: Raising spread requirement "
                          f"({current_spread*100:.2f}% → {new_spread*100:.2f}%) "
                          f"Success rate: {success_rate*100:.1f}%")
        else:
            # Medium success rate = keep current
            return
        
        # Apply bounds
        min_floor = self.config.DYNAMIC_SPREADS['min_spread_floor']
        max_ceiling = self.config.DYNAMIC_SPREADS['max_spread_ceiling']
        
        new_spread = max(min_floor, new_spread)
        new_spread = min(max_ceiling, new_spread)
        
        # Don't deviate too far from base
        new_spread = max(base_spread * 0.5, new_spread)  # At least 50% of base
        new_spread = min(base_spread * 2.0, new_spread)  # At most 200% of base
        
        self.current_spreads[symbol] = new_spread
    
    def get_min_spread(self, symbol: str) -> float:
        """Get current minimum spread requirement"""
        return self.current_spreads.get(symbol, self.base_spreads.get(symbol, 0.005))
    
    def get_current_spread(self, symbol: str) -> float:
        """Get current minimum spread requirement (alias for get_min_spread)"""
        return self.get_min_spread(symbol)
    
    def should_trade(self, symbol: str, current_spread: float) -> Tuple[bool, str]:
        """Determine if current spread is sufficient to trade"""
        min_spread = self.get_min_spread(symbol)
        
        if current_spread < min_spread:
            return False, f"Spread {current_spread*100:.2f}% < min {min_spread*100:.2f}%"
        
        return True, f"Spread {current_spread*100:.2f}% >= min {min_spread*100:.2f}%"
    
    def get_spread_statistics(self, symbol: str) -> Dict[str, Any]:
        """Get spread statistics for a symbol"""
        if symbol not in self.spread_history:
            return {}
        
        opportunities = list(self.spread_history[symbol])
        if not opportunities:
            return {}
        
        # Filter to last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_opps = [opp for opp in opportunities if opp.timestamp > cutoff_time]
        
        if not recent_opps:
            return {}
        
        spreads = [opp.spread for opp in recent_opps]
        traded_opps = [opp for opp in recent_opps if opp.traded]
        successful_trades = [opp for opp in traded_opps if opp.success]
        
        return {
            'total_opportunities': len(recent_opps),
            'traded_opportunities': len(traded_opps),
            'successful_trades': len(successful_trades),
            'success_rate': len(successful_trades) / len(traded_opps) if traded_opps else 0,
            'avg_spread': sum(spreads) / len(spreads),
            'min_spread_seen': min(spreads),
            'max_spread_seen': max(spreads),
            'current_min_spread': self.current_spreads[symbol],
            'base_min_spread': self.base_spreads[symbol],
            'spread_adjustment_factor': self.current_spreads[symbol] / self.base_spreads[symbol],
        }
    
    def get_all_spread_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get spread statistics for all symbols"""
        stats = {}
        for symbol in self.config.CURRENCY_PAIRS:
            stats[symbol] = self.get_spread_statistics(symbol)
        return stats
    
    def reset_spread(self, symbol: str):
        """Reset spread requirement to base"""
        self.current_spreads[symbol] = self.base_spreads[symbol]
        logger.info(f"Reset {symbol} spread to base: {self.base_spreads[symbol]*100:.2f}%")
    
    def reset_all_spreads(self):
        """Reset all spread requirements to base"""
        self.current_spreads = self.base_spreads.copy()
        logger.info("Reset all spreads to base values")

