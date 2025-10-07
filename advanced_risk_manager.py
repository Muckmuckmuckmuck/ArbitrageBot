import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Data class for risk metrics"""
    symbol: str
    current_exposure: float
    max_exposure: float
    exposure_ratio: float
    volatility: float
    correlation_risk: float
    liquidity_risk: float
    total_risk_score: float
    timestamp: float

@dataclass
class PortfolioRisk:
    """Data class for portfolio-level risk"""
    total_exposure: float
    max_portfolio_exposure: float
    exposure_ratio: float
    diversification_score: float
    concentration_risk: float
    correlation_matrix: Dict[str, Dict[str, float]]
    risk_score: float
    timestamp: float

class AdvancedRiskManager:
    """Enhanced risk management system with portfolio-level controls"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.current_exposures = {}
        self.risk_history = {}
        self.correlation_matrix = {}
        self.volatility_cache = {}
        self.liquidity_scores = {}
        
        # Risk limits
        self.max_position_size = 10000  # Maximum position size in USD
        self.max_portfolio_exposure = 50000  # Maximum total portfolio exposure
        self.max_correlation = 0.7  # Maximum correlation between positions
        self.max_volatility = 0.1  # Maximum volatility threshold
        self.min_liquidity_score = 0.5  # Minimum liquidity score
        
        # Risk weights
        self.risk_weights = {
            'exposure': 0.3,
            'volatility': 0.25,
            'correlation': 0.2,
            'liquidity': 0.15,
            'concentration': 0.1
        }
        
    async def assess_position_risk(self, symbol: str, amount: float, price: float) -> Tuple[bool, RiskMetrics]:
        """Assess risk for a potential position"""
        try:
            # Calculate exposure
            exposure = amount * price
            max_exposure = Config.POSITION_LIMITS.get(symbol, self.max_position_size)
            exposure_ratio = exposure / max_exposure
            
            # Get volatility
            volatility = await self._get_volatility(symbol)
            
            # Get correlation risk
            correlation_risk = await self._get_correlation_risk(symbol)
            
            # Get liquidity risk
            liquidity_risk = await self._get_liquidity_risk(symbol)
            
            # Calculate total risk score
            risk_score = (
                exposure_ratio * self.risk_weights['exposure'] +
                volatility * self.risk_weights['volatility'] +
                correlation_risk * self.risk_weights['correlation'] +
                liquidity_risk * self.risk_weights['liquidity']
            )
            
            # Create risk metrics
            risk_metrics = RiskMetrics(
                symbol=symbol,
                current_exposure=exposure,
                max_exposure=max_exposure,
                exposure_ratio=exposure_ratio,
                volatility=volatility,
                correlation_risk=correlation_risk,
                liquidity_risk=liquidity_risk,
                total_risk_score=risk_score,
                timestamp=time.time()
            )
            
            # Check if risk is acceptable
            is_acceptable = (
                exposure_ratio <= 1.0 and
                volatility <= self.max_volatility and
                correlation_risk <= self.max_correlation and
                liquidity_risk >= self.min_liquidity_score and
                risk_score <= 0.8  # Overall risk threshold
            )
            
            logger.info(f"Risk assessment for {symbol}: Score={risk_score:.3f}, "
                       f"Exposure={exposure_ratio:.3f}, Volatility={volatility:.3f}, "
                       f"Correlation={correlation_risk:.3f}, Liquidity={liquidity_risk:.3f}, "
                       f"Acceptable={is_acceptable}")
            
            return is_acceptable, risk_metrics
            
        except Exception as e:
            logger.error(f"Error assessing position risk for {symbol}: {str(e)}")
            return False, None
    
    async def assess_portfolio_risk(self) -> PortfolioRisk:
        """Assess portfolio-level risk"""
        try:
            # Calculate total exposure
            total_exposure = sum(self.current_exposures.values())
            exposure_ratio = total_exposure / self.max_portfolio_exposure
            
            # Calculate diversification score
            diversification_score = await self._calculate_diversification_score()
            
            # Calculate concentration risk
            concentration_risk = await self._calculate_concentration_risk()
            
            # Update correlation matrix
            await self._update_correlation_matrix()
            
            # Calculate overall risk score
            risk_score = (
                exposure_ratio * self.risk_weights['exposure'] +
                (1 - diversification_score) * self.risk_weights['correlation'] +
                concentration_risk * self.risk_weights['concentration']
            )
            
            portfolio_risk = PortfolioRisk(
                total_exposure=total_exposure,
                max_portfolio_exposure=self.max_portfolio_exposure,
                exposure_ratio=exposure_ratio,
                diversification_score=diversification_score,
                concentration_risk=concentration_risk,
                correlation_matrix=self.correlation_matrix.copy(),
                risk_score=risk_score,
                timestamp=time.time()
            )
            
            logger.info(f"Portfolio risk assessment: Total exposure=${total_exposure:.2f}, "
                       f"Exposure ratio={exposure_ratio:.3f}, Diversification={diversification_score:.3f}, "
                       f"Concentration={concentration_risk:.3f}, Risk score={risk_score:.3f}")
            
            return portfolio_risk
            
        except Exception as e:
            logger.error(f"Error assessing portfolio risk: {str(e)}")
            return None
    
    async def _get_volatility(self, symbol: str) -> float:
        """Get volatility estimate for a symbol"""
        try:
            # Check cache
            if symbol in self.volatility_cache:
                cache_time = self.volatility_cache[symbol]['timestamp']
                if time.time() - cache_time < 300:  # 5 minutes cache
                    return self.volatility_cache[symbol]['volatility']
            
            # Get recent price data from both exchanges
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            # Get ticker data
            binance_ticker = await binance_exchange.get_ticker(symbol)
            kraken_ticker = await kraken_exchange.get_ticker(symbol)
            
            if not binance_ticker or not kraken_ticker:
                return 0.05  # Default volatility
            
            # Calculate price spread as volatility proxy
            binance_price = binance_ticker['last']
            kraken_price = kraken_ticker['last']
            
            price_diff = abs(binance_price - kraken_price)
            avg_price = (binance_price + kraken_price) / 2
            volatility = price_diff / avg_price
            
            # Cache the result
            self.volatility_cache[symbol] = {
                'volatility': volatility,
                'timestamp': time.time()
            }
            
            return volatility
            
        except Exception as e:
            logger.error(f"Error getting volatility for {symbol}: {str(e)}")
            return 0.05  # Default volatility
    
    async def _get_correlation_risk(self, symbol: str) -> float:
        """Get correlation risk for a symbol"""
        try:
            if not self.current_exposures:
                return 0.0
            
            # Calculate correlation with existing positions
            correlations = []
            for existing_symbol in self.current_exposures.keys():
                if existing_symbol != symbol:
                    correlation = await self._calculate_correlation(symbol, existing_symbol)
                    if correlation is not None:
                        correlations.append(correlation)
            
            if not correlations:
                return 0.0
            
            # Return average correlation
            avg_correlation = sum(correlations) / len(correlations)
            return avg_correlation
            
        except Exception as e:
            logger.error(f"Error getting correlation risk for {symbol}: {str(e)}")
            return 0.0
    
    async def _get_liquidity_risk(self, symbol: str) -> float:
        """Get liquidity risk for a symbol"""
        try:
            # Check cache
            if symbol in self.liquidity_scores:
                cache_time = self.liquidity_scores[symbol]['timestamp']
                if time.time() - cache_time < 600:  # 10 minutes cache
                    return self.liquidity_scores[symbol]['score']
            
            # Get order book data from both exchanges
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            binance_orderbook = await binance_exchange.get_orderbook(symbol, 20)
            kraken_orderbook = await kraken_exchange.get_orderbook(symbol, 20)
            
            if not binance_orderbook or not kraken_orderbook:
                return 0.3  # Default low liquidity score
            
            # Calculate liquidity score based on order book depth
            binance_liquidity = self._calculate_orderbook_liquidity(binance_orderbook)
            kraken_liquidity = self._calculate_orderbook_liquidity(kraken_orderbook)
            
            # Average liquidity score
            avg_liquidity = (binance_liquidity + kraken_liquidity) / 2
            
            # Cache the result
            self.liquidity_scores[symbol] = {
                'score': avg_liquidity,
                'timestamp': time.time()
            }
            
            return avg_liquidity
            
        except Exception as e:
            logger.error(f"Error getting liquidity risk for {symbol}: {str(e)}")
            return 0.3  # Default low liquidity score
    
    def _calculate_orderbook_liquidity(self, orderbook: Dict) -> float:
        """Calculate liquidity score from order book"""
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            # Calculate depth for top 10 levels
            bid_depth = sum(price * quantity for price, quantity in bids[:10])
            ask_depth = sum(price * quantity for price, quantity in asks[:10])
            
            # Normalize by price
            mid_price = (bids[0][0] + asks[0][0]) / 2
            total_depth = (bid_depth + ask_depth) / mid_price
            
            # Convert to liquidity score (0-1)
            liquidity_score = min(total_depth / 1000000, 1.0)  # Normalize to 1M USD
            
            return liquidity_score
            
        except Exception as e:
            logger.error(f"Error calculating orderbook liquidity: {str(e)}")
            return 0.0
    
    async def _calculate_correlation(self, symbol1: str, symbol2: str) -> Optional[float]:
        """Calculate correlation between two symbols"""
        try:
            # Simple correlation based on price movements
            # In a real implementation, this would use historical price data
            
            # Get current prices
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            ticker1_binance = await binance_exchange.get_ticker(symbol1)
            ticker1_kraken = await kraken_exchange.get_ticker(symbol1)
            ticker2_binance = await binance_exchange.get_ticker(symbol2)
            ticker2_kraken = await kraken_exchange.get_ticker(symbol2)
            
            if not all([ticker1_binance, ticker1_kraken, ticker2_binance, ticker2_kraken]):
                return None
            
            # Calculate spread for each symbol
            spread1 = abs(ticker1_binance['last'] - ticker1_kraken['last']) / ticker1_binance['last']
            spread2 = abs(ticker2_binance['last'] - ticker2_kraken['last']) / ticker2_binance['last']
            
            # Simple correlation based on spread similarity
            # This is a simplified approach - real correlation would use historical data
            correlation = 1.0 - abs(spread1 - spread2)
            
            return max(0.0, min(1.0, correlation))
            
        except Exception as e:
            logger.error(f"Error calculating correlation between {symbol1} and {symbol2}: {str(e)}")
            return None
    
    async def _calculate_diversification_score(self) -> float:
        """Calculate portfolio diversification score"""
        try:
            if not self.current_exposures:
                return 1.0  # Perfect diversification with no positions
            
            # Calculate Herfindahl-Hirschman Index (HHI)
            total_exposure = sum(self.current_exposures.values())
            if total_exposure == 0:
                return 1.0
            
            hhi = sum((exposure / total_exposure) ** 2 for exposure in self.current_exposures.values())
            
            # Convert HHI to diversification score (0-1)
            diversification_score = 1.0 - hhi
            
            return diversification_score
            
        except Exception as e:
            logger.error(f"Error calculating diversification score: {str(e)}")
            return 0.5  # Default moderate diversification
    
    async def _calculate_concentration_risk(self) -> float:
        """Calculate concentration risk"""
        try:
            if not self.current_exposures:
                return 0.0
            
            # Calculate maximum position as percentage of total
            total_exposure = sum(self.current_exposures.values())
            max_exposure = max(self.current_exposures.values())
            
            concentration_ratio = max_exposure / total_exposure if total_exposure > 0 else 0
            
            return concentration_ratio
            
        except Exception as e:
            logger.error(f"Error calculating concentration risk: {str(e)}")
            return 0.0
    
    async def _update_correlation_matrix(self):
        """Update correlation matrix for all symbols"""
        try:
            symbols = list(self.current_exposures.keys())
            if len(symbols) < 2:
                return
            
            for i, symbol1 in enumerate(symbols):
                if symbol1 not in self.correlation_matrix:
                    self.correlation_matrix[symbol1] = {}
                
                for j, symbol2 in enumerate(symbols):
                    if symbol2 not in self.correlation_matrix:
                        self.correlation_matrix[symbol2] = {}
                    
                    if symbol1 != symbol2:
                        correlation = await self._calculate_correlation(symbol1, symbol2)
                        if correlation is not None:
                            self.correlation_matrix[symbol1][symbol2] = correlation
                            self.correlation_matrix[symbol2][symbol1] = correlation
            
        except Exception as e:
            logger.error(f"Error updating correlation matrix: {str(e)}")
    
    def update_position(self, symbol: str, amount: float, price: float):
        """Update position in risk tracking"""
        try:
            exposure = amount * price
            self.current_exposures[symbol] = exposure
            
            # Update risk history
            if symbol not in self.risk_history:
                self.risk_history[symbol] = []
            
            risk_metrics = RiskMetrics(
                symbol=symbol,
                current_exposure=exposure,
                max_exposure=Config.POSITION_LIMITS.get(symbol, self.max_position_size),
                exposure_ratio=exposure / Config.POSITION_LIMITS.get(symbol, self.max_position_size),
                volatility=0.0,  # Will be calculated in real-time
                correlation_risk=0.0,  # Will be calculated in real-time
                liquidity_risk=0.0,  # Will be calculated in real-time
                total_risk_score=0.0,  # Will be calculated in real-time
                timestamp=time.time()
            )
            
            self.risk_history[symbol].append(risk_metrics)
            
            # Keep only recent history
            if len(self.risk_history[symbol]) > 1000:
                self.risk_history[symbol] = self.risk_history[symbol][-1000:]
            
            logger.info(f"Updated position for {symbol}: ${exposure:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating position for {symbol}: {str(e)}")
    
    def close_position(self, symbol: str):
        """Close position in risk tracking"""
        try:
            if symbol in self.current_exposures:
                del self.current_exposures[symbol]
                logger.info(f"Closed position for {symbol}")
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
    
    def get_risk_summary(self) -> Dict:
        """Get current risk summary"""
        try:
            total_exposure = sum(self.current_exposures.values())
            num_positions = len(self.current_exposures)
            
            summary = {
                'total_exposure': total_exposure,
                'max_portfolio_exposure': self.max_portfolio_exposure,
                'exposure_ratio': total_exposure / self.max_portfolio_exposure,
                'num_positions': num_positions,
                'positions': dict(self.current_exposures),
                'timestamp': time.time()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting risk summary: {str(e)}")
            return {}

