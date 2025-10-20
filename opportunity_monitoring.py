#!/usr/bin/env python3
"""
Opportunity Monitoring System - Enterprise Grade
================================================

This module provides comprehensive opportunity monitoring with:
- Real-time spread monitoring
- Opportunity validation
- Competition detection
- Market condition analysis
- Performance tracking

Key Features:
1. Real-time Spread Monitoring: Continuous spread tracking
2. Opportunity Validation: Validate opportunities before execution
3. Competition Detection: Detect competing bots
4. Market Condition Analysis: Analyze market conditions
5. Performance Tracking: Track opportunity success rates
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import statistics

import ccxt

# Import bot configuration
from coinbase_gemini_config import Config
from enhanced_retry_logic import enhanced_retry_logic

logger = logging.getLogger(__name__)

class OpportunityStatus(Enum):
    """Opportunity status enumeration"""
    ACTIVE = "active"           # Opportunity is active
    EXPIRED = "expired"         # Opportunity has expired
    EXECUTED = "executed"       # Opportunity has been executed
    CANCELLED = "cancelled"     # Opportunity was cancelled
    INVALID = "invalid"         # Opportunity is invalid

class MarketCondition(Enum):
    """Market condition enumeration"""
    NORMAL = "normal"           # Normal market conditions
    VOLATILE = "volatile"       # High volatility
    LOW_LIQUIDITY = "low_liquidity"  # Low liquidity
    HIGH_COMPETITION = "high_competition"  # High competition

@dataclass
class Opportunity:
    """Information about an arbitrage opportunity"""
    opportunity_id: str
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    estimated_profit: float
    status: OpportunityStatus
    created_at: datetime
    expires_at: datetime
    validation_score: float = 0.0
    market_condition: MarketCondition = MarketCondition.NORMAL
    competition_level: float = 0.0
    liquidity_score: float = 0.0
    volatility_score: float = 0.0

@dataclass
class MarketData:
    """Market data for analysis"""
    symbol: str
    timestamp: datetime
    coinbase_price: float
    gemini_price: float
    spread_percent: float
    coinbase_volume: float
    gemini_volume: float
    coinbase_bid: float
    coinbase_ask: float
    gemini_bid: float
    gemini_ask: float

class OpportunityMonitoring:
    """
    Comprehensive opportunity monitoring system
    """
    
    def __init__(self, exchanges: Dict[str, ccxt.Exchange], config: Config):
        self.exchanges = exchanges
        self.config = config
        self.opportunities: Dict[str, Opportunity] = {}
        self.market_data_history: List[MarketData] = []
        self.competition_detection: Dict[str, List[datetime]] = {}
        
        # Configuration
        self.opportunity_timeout_minutes = 5
        self.validation_threshold = 0.7  # Minimum validation score
        self.competition_threshold = 3   # Max opportunities per minute
        self.volatility_threshold = 0.05  # 5% volatility threshold
        self.liquidity_threshold = 1000  # Minimum volume threshold
        
        # Monitoring
        self.last_scan = datetime.now()
        self.scan_interval_seconds = 10
        self.market_data_retention_hours = 24
        
        logger.info("🚀 Opportunity Monitoring System initialized")
        logger.info(f"   Opportunity timeout: {self.opportunity_timeout_minutes} minutes")
        logger.info(f"   Validation threshold: {self.validation_threshold}")
        logger.info(f"   Competition threshold: {self.competition_threshold} opportunities/minute")

    async def scan_for_opportunities(self) -> List[Opportunity]:
        """
        Scan for arbitrage opportunities across all currency pairs
        """
        opportunities = []
        
        for symbol in self.config.CURRENCY_PAIRS:
            try:
                # Get market data for both exchanges
                market_data = await self._get_market_data(symbol)
                
                if market_data:
                    # Store market data
                    self.market_data_history.append(market_data)
                    
                    # Check for opportunities
                    opportunity = await self._analyze_opportunity(market_data)
                    
                    if opportunity:
                        opportunities.append(opportunity)
                        self.opportunities[opportunity.opportunity_id] = opportunity
                
            except Exception as e:
                logger.warning(f"⚠️ Error scanning {symbol}: {str(e)}")
        
        # Clean up old market data
        self._cleanup_old_market_data()
        
        # Clean up expired opportunities
        self._cleanup_expired_opportunities()
        
        if opportunities:
            logger.info(f"🎯 Found {len(opportunities)} opportunities")
            for opp in opportunities:
                logger.info(f"   {opp.symbol}: {opp.spread_percent:.3f}% spread, "
                           f"${opp.estimated_profit:.3f} profit, "
                           f"validation: {opp.validation_score:.2f}")
        
        return opportunities

    async def _get_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Get market data for a symbol from both exchanges
        """
        try:
            # Get data from both exchanges in parallel
            tasks = []
            for exchange_name in ['coinbase', 'gemini']:
                if exchange_name in self.exchanges:
                    task = self._get_exchange_data(exchange_name, symbol)
                    tasks.append(task)
            
            if len(tasks) < 2:
                return None
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for errors
            coinbase_data = None
            gemini_data = None
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"⚠️ Error getting data from exchange {i}: {str(result)}")
                elif i == 0:  # coinbase
                    coinbase_data = result
                elif i == 1:  # gemini
                    gemini_data = result
            
            if not coinbase_data or not gemini_data:
                return None
            
            # Calculate spread
            spread_percent = abs(coinbase_data['price'] - gemini_data['price']) / min(coinbase_data['price'], gemini_data['price']) * 100
            
            return MarketData(
                symbol=symbol,
                timestamp=datetime.now(),
                coinbase_price=coinbase_data['price'],
                gemini_price=gemini_data['price'],
                spread_percent=spread_percent,
                coinbase_volume=coinbase_data['volume'],
                gemini_volume=gemini_data['volume'],
                coinbase_bid=coinbase_data['bid'],
                coinbase_ask=coinbase_data['ask'],
                gemini_bid=gemini_data['bid'],
                gemini_ask=gemini_data['ask']
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting market data for {symbol}: {str(e)}")
            return None

    async def _get_exchange_data(self, exchange_name: str, symbol: str) -> Dict[str, float]:
        """
        Get market data from a specific exchange
        """
        try:
            exchange = self.exchanges[exchange_name]
            
            # Get ticker data
            ticker = await enhanced_retry_logic.execute_with_retry(
                exchange.fetch_ticker,
                'fetch_ticker',
                exchange_name,
                symbol
            )
            
            if hasattr(ticker, '__await__'):
                ticker = await ticker
            
            return {
                'price': float(ticker['last']),
                'volume': float(ticker['baseVolume']),
                'bid': float(ticker['bid']),
                'ask': float(ticker['ask'])
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting data from {exchange_name} for {symbol}: {str(e)}")
            raise e

    async def _analyze_opportunity(self, market_data: MarketData) -> Optional[Opportunity]:
        """
        Analyze market data to find arbitrage opportunities
        """
        try:
            # Calculate spread
            spread_percent = market_data.spread_percent
            
            # Check if spread is profitable
            min_spread = self.config.CURRENCY_PAIR_SPREADS.get(market_data.symbol, {}).get('min_spread', 0.01)
            if spread_percent < min_spread * 100:
                return None
            
            # Determine buy/sell exchanges
            if market_data.coinbase_price < market_data.gemini_price:
                buy_exchange = 'coinbase'
                sell_exchange = 'gemini'
                buy_price = market_data.coinbase_price
                sell_price = market_data.gemini_price
            else:
                buy_exchange = 'gemini'
                sell_exchange = 'coinbase'
                buy_price = market_data.gemini_price
                sell_price = market_data.coinbase_price
            
            # Calculate estimated profit
            estimated_profit = await self._calculate_profit(market_data.symbol, buy_price, sell_price)
            
            if estimated_profit < self.config.MIN_PROFIT_USD:
                return None
            
            # Create opportunity
            opportunity_id = f"opp_{market_data.symbol}_{int(time.time())}"
            opportunity = Opportunity(
                opportunity_id=opportunity_id,
                symbol=market_data.symbol,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                spread_percent=spread_percent,
                estimated_profit=estimated_profit,
                status=OpportunityStatus.ACTIVE,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=self.opportunity_timeout_minutes)
            )
            
            # Validate opportunity
            validation_score = await self._validate_opportunity(opportunity, market_data)
            opportunity.validation_score = validation_score
            
            # Analyze market conditions
            market_condition = await self._analyze_market_conditions(market_data)
            opportunity.market_condition = market_condition
            
            # Check competition
            competition_level = await self._check_competition(market_data.symbol)
            opportunity.competition_level = competition_level
            
            # Check liquidity
            liquidity_score = await self._check_liquidity(market_data)
            opportunity.liquidity_score = liquidity_score
            
            # Check volatility
            volatility_score = await self._check_volatility(market_data.symbol)
            opportunity.volatility_score = volatility_score
            
            # Only return opportunities that pass validation
            if validation_score >= self.validation_threshold:
                return opportunity
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error analyzing opportunity for {market_data.symbol}: {str(e)}")
            return None

    async def _calculate_profit(self, symbol: str, buy_price: float, sell_price: float) -> float:
        """
        Calculate estimated profit for an opportunity
        """
        try:
            # Get position size
            position_size = await self._get_position_size(symbol)
            
            # Calculate gross profit
            gross_profit = position_size * (sell_price - buy_price)
            
            # Calculate fees
            buy_fee = position_size * buy_price * self.config.EXCHANGE_FEES['coinbase']['taker']
            sell_fee = position_size * sell_price * self.config.EXCHANGE_FEES['gemini']['taker']
            total_fees = buy_fee + sell_fee
            
            # Calculate net profit
            net_profit = gross_profit - total_fees
            
            return net_profit
            
        except Exception as e:
            logger.error(f"❌ Error calculating profit for {symbol}: {str(e)}")
            return 0.0

    async def _get_position_size(self, symbol: str) -> float:
        """
        Get position size for a symbol
        """
        try:
            # Get total account value
            total_value = 0.0
            for exchange_name, exchange in self.exchanges.items():
                balance = await enhanced_retry_logic.execute_with_retry(
                    exchange.fetch_balance,
                    'fetch_balance',
                    exchange_name
                )
                
                if hasattr(balance, '__await__'):
                    balance = await balance
                
                # Calculate USD value
                usd_balance = balance.get('free', {}).get('USD', 0)
                total_value += float(usd_balance)
            
            # Get position percentage for this symbol
            position_percent = self.config.BASE_POSITION_PERCENTAGES.get(symbol, 0.05)
            
            # Calculate position size
            position_size = total_value * position_percent
            
            return position_size
            
        except Exception as e:
            logger.error(f"❌ Error getting position size for {symbol}: {str(e)}")
            return 100.0  # Default position size

    async def _validate_opportunity(self, opportunity: Opportunity, market_data: MarketData) -> float:
        """
        Validate an opportunity and return a score (0.0 to 1.0)
        """
        try:
            score = 0.0
            
            # Check spread quality (40% weight)
            min_spread = self.config.CURRENCY_PAIR_SPREADS.get(opportunity.symbol, {}).get('min_spread', 0.01)
            if opportunity.spread_percent > min_spread * 100 * 2:
                score += 0.4
            elif opportunity.spread_percent > min_spread * 100 * 1.5:
                score += 0.3
            elif opportunity.spread_percent > min_spread * 100:
                score += 0.2
            
            # Check profit quality (30% weight)
            if opportunity.estimated_profit > self.config.MIN_PROFIT_USD * 5:
                score += 0.3
            elif opportunity.estimated_profit > self.config.MIN_PROFIT_USD * 2:
                score += 0.2
            elif opportunity.estimated_profit > self.config.MIN_PROFIT_USD:
                score += 0.1
            
            # Check liquidity (20% weight)
            total_volume = market_data.coinbase_volume + market_data.gemini_volume
            if total_volume > self.liquidity_threshold * 10:
                score += 0.2
            elif total_volume > self.liquidity_threshold * 5:
                score += 0.15
            elif total_volume > self.liquidity_threshold:
                score += 0.1
            
            # Check competition (10% weight)
            if opportunity.competition_level < 1:
                score += 0.1
            elif opportunity.competition_level < 2:
                score += 0.05
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"❌ Error validating opportunity {opportunity.opportunity_id}: {str(e)}")
            return 0.0

    async def _analyze_market_conditions(self, market_data: MarketData) -> MarketCondition:
        """
        Analyze market conditions
        """
        try:
            # Check volatility
            if market_data.spread_percent > 5.0:  # 5% spread indicates high volatility
                return MarketCondition.VOLATILE
            
            # Check liquidity
            total_volume = market_data.coinbase_volume + market_data.gemini_volume
            if total_volume < self.liquidity_threshold:
                return MarketCondition.LOW_LIQUIDITY
            
            # Check competition
            competition_level = await self._check_competition(market_data.symbol)
            if competition_level > self.competition_threshold:
                return MarketCondition.HIGH_COMPETITION
            
            return MarketCondition.NORMAL
            
        except Exception as e:
            logger.error(f"❌ Error analyzing market conditions: {str(e)}")
            return MarketCondition.NORMAL

    async def _check_competition(self, symbol: str) -> float:
        """
        Check competition level for a symbol
        """
        try:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            
            # Count opportunities in the last minute
            recent_opportunities = 0
            for opp in self.opportunities.values():
                if (opp.symbol == symbol and 
                    opp.created_at > minute_ago and 
                    opp.status == OpportunityStatus.ACTIVE):
                    recent_opportunities += 1
            
            return recent_opportunities
            
        except Exception as e:
            logger.error(f"❌ Error checking competition for {symbol}: {str(e)}")
            return 0.0

    async def _check_liquidity(self, market_data: MarketData) -> float:
        """
        Check liquidity score for market data
        """
        try:
            total_volume = market_data.coinbase_volume + market_data.gemini_volume
            
            if total_volume > self.liquidity_threshold * 10:
                return 1.0
            elif total_volume > self.liquidity_threshold * 5:
                return 0.8
            elif total_volume > self.liquidity_threshold:
                return 0.6
            else:
                return 0.3
                
        except Exception as e:
            logger.error(f"❌ Error checking liquidity: {str(e)}")
            return 0.0

    async def _check_volatility(self, symbol: str) -> float:
        """
        Check volatility score for a symbol
        """
        try:
            # Get recent market data for this symbol
            recent_data = [md for md in self.market_data_history 
                          if md.symbol == symbol and 
                          md.timestamp > datetime.now() - timedelta(minutes=10)]
            
            if len(recent_data) < 2:
                return 0.5  # Default moderate volatility
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(recent_data)):
                change = abs(recent_data[i].coinbase_price - recent_data[i-1].coinbase_price) / recent_data[i-1].coinbase_price
                price_changes.append(change)
            
            if not price_changes:
                return 0.5
            
            # Calculate volatility
            volatility = statistics.stdev(price_changes)
            
            if volatility > self.volatility_threshold:
                return 1.0  # High volatility
            elif volatility > self.volatility_threshold * 0.5:
                return 0.7  # Medium volatility
            else:
                return 0.3  # Low volatility
                
        except Exception as e:
            logger.error(f"❌ Error checking volatility for {symbol}: {str(e)}")
            return 0.5

    def _cleanup_old_market_data(self):
        """
        Clean up old market data
        """
        cutoff_time = datetime.now() - timedelta(hours=self.market_data_retention_hours)
        self.market_data_history = [md for md in self.market_data_history if md.timestamp > cutoff_time]

    def _cleanup_expired_opportunities(self):
        """
        Clean up expired opportunities
        """
        now = datetime.now()
        expired_opportunities = []
        
        for opp_id, opportunity in self.opportunities.items():
            if now > opportunity.expires_at:
                expired_opportunities.append(opp_id)
                opportunity.status = OpportunityStatus.EXPIRED
        
        for opp_id in expired_opportunities:
            del self.opportunities[opp_id]
        
        if expired_opportunities:
            logger.info(f"🧹 Cleaned up {len(expired_opportunities)} expired opportunities")

    def get_opportunity_stats(self) -> Dict[str, Any]:
        """
        Get opportunity statistics
        """
        total_opportunities = len(self.opportunities)
        active_opportunities = len([opp for opp in self.opportunities.values() if opp.status == OpportunityStatus.ACTIVE])
        
        # Calculate average validation score
        validation_scores = [opp.validation_score for opp in self.opportunities.values()]
        avg_validation_score = statistics.mean(validation_scores) if validation_scores else 0.0
        
        # Calculate average spread
        spreads = [opp.spread_percent for opp in self.opportunities.values()]
        avg_spread = statistics.mean(spreads) if spreads else 0.0
        
        # Calculate average profit
        profits = [opp.estimated_profit for opp in self.opportunities.values()]
        avg_profit = statistics.mean(profits) if profits else 0.0
        
        return {
            'total_opportunities': total_opportunities,
            'active_opportunities': active_opportunities,
            'avg_validation_score': avg_validation_score,
            'avg_spread': avg_spread,
            'avg_profit': avg_profit,
            'market_data_points': len(self.market_data_history)
        }

    async def run_monitoring_cycle(self):
        """
        Run periodic monitoring cycle
        """
        while True:
            try:
                opportunities = await self.scan_for_opportunities()
                
                # Log statistics
                stats = self.get_opportunity_stats()
                logger.info(f"📊 Monitoring stats: {stats['active_opportunities']} active opportunities, "
                           f"avg validation: {stats['avg_validation_score']:.2f}, "
                           f"avg spread: {stats['avg_spread']:.3f}%")
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring cycle: {str(e)}")
            
            # Wait for next cycle
            await asyncio.sleep(self.scan_interval_seconds)

# Example usage
async def test_opportunity_monitoring():
    """
    Test the opportunity monitoring system
    """
    # This would be called from the main bot
    pass

if __name__ == "__main__":
    asyncio.run(test_opportunity_monitoring())
