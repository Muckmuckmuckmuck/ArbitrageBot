import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class TriangularArbitrageOpportunity:
    """Data class for triangular arbitrage opportunity"""
    symbol1: str
    symbol2: str
    symbol3: str
    path1_rate: float
    path2_rate: float
    path3_rate: float
    profit_percent: float
    profit_amount: float
    exchange: str
    timestamp: float
    confidence: float

@dataclass
class ArbitragePath:
    """Data class for arbitrage path"""
    path_id: str
    steps: List[Dict]
    total_rate: float
    estimated_time: float
    liquidity_score: float
    risk_score: float

@dataclass
class CrossAssetOpportunity:
    """Data class for cross-asset arbitrage opportunity"""
    base_asset: str
    quote_asset: str
    intermediate_asset: str
    exchange1: str
    exchange2: str
    rate1: float
    rate2: float
    profit_percent: float
    profit_amount: float
    timestamp: float
    confidence: float

class TriangularArbitrageEngine:
    """Triangular and cross-asset arbitrage engine"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.triangular_opportunities = {}
        self.cross_asset_opportunities = {}
        self.arbitrage_history = {}
        
        # Supported triangular arbitrage pairs
        self.triangular_pairs = [
            # BTC-based triangles
            ('BTC/USDT', 'ETH/BTC', 'ETH/USDT'),
            ('BTC/USDT', 'LTC/BTC', 'LTC/USDT'),
            ('BTC/USDT', 'BCH/BTC', 'BCH/USDT'),
            
            # ETH-based triangles
            ('ETH/USDT', 'BNB/ETH', 'BNB/USDT'),
            ('ETH/USDT', 'LINK/ETH', 'LINK/USDT'),
            ('ETH/USDT', 'UNI/ETH', 'UNI/USDT'),
            
            # Stablecoin triangles
            ('USDT/USDC', 'BTC/USDT', 'BTC/USDC'),
            ('USDT/USDC', 'ETH/USDT', 'ETH/USDC'),
            
            # Cross-exchange triangles
            ('XRP/USDT', 'XRP/BTC', 'BTC/USDT'),
            ('ADA/USDT', 'ADA/BTC', 'BTC/USDT'),
            ('DOT/USDT', 'DOT/BTC', 'BTC/USDT'),
        ]
        
        # Cross-asset arbitrage pairs
        self.cross_asset_pairs = [
            # Major cross-asset opportunities
            ('BTC', 'ETH', 'USDT'),
            ('BTC', 'BNB', 'USDT'),
            ('ETH', 'BNB', 'USDT'),
            ('BTC', 'ADA', 'USDT'),
            ('ETH', 'LINK', 'USDT'),
            ('BTC', 'DOT', 'USDT'),
            ('ETH', 'UNI', 'USDT'),
            ('BTC', 'LTC', 'USDT'),
            ('ETH', 'AAVE', 'USDT'),
            ('BTC', 'MATIC', 'USDT'),
        ]
        
        # Arbitrage parameters
        self.arbitrage_parameters = {
            'min_profit_percent': 0.5,  # Minimum 0.5% profit
            'max_execution_time': 300,  # Maximum 5 minutes execution time
            'min_liquidity_score': 0.6,  # Minimum liquidity score
            'max_risk_score': 0.7,  # Maximum risk score
            'confidence_threshold': 0.8,  # Minimum confidence threshold
        }
        
        # Performance tracking
        self.performance_metrics = {}
        self.opportunity_history = {}
        
    async def scan_triangular_opportunities(self, symbols: List[str] = None) -> List[TriangularArbitrageOpportunity]:
        """Scan for triangular arbitrage opportunities"""
        try:
            opportunities = []
            
            # Use provided symbols or default pairs
            if symbols:
                pairs_to_scan = self._filter_triangular_pairs(symbols)
            else:
                pairs_to_scan = self.triangular_pairs
            
            for pair in pairs_to_scan:
                try:
                    opportunity = await self._analyze_triangular_pair(pair)
                    if opportunity and opportunity.profit_percent >= self.arbitrage_parameters['min_profit_percent']:
                        opportunities.append(opportunity)
                        
                        # Store opportunity
                        key = f"{pair[0]}_{pair[1]}_{pair[2]}"
                        self.triangular_opportunities[key] = opportunity
                        
                except Exception as e:
                    logger.error(f"Error analyzing triangular pair {pair}: {str(e)}")
                    continue
            
            # Sort by profit percentage
            opportunities.sort(key=lambda x: x.profit_percent, reverse=True)
            
            logger.info(f"Found {len(opportunities)} triangular arbitrage opportunities")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error scanning triangular opportunities: {str(e)}")
            return []
    
    async def scan_cross_asset_opportunities(self, symbols: List[str] = None) -> List[CrossAssetOpportunity]:
        """Scan for cross-asset arbitrage opportunities"""
        try:
            opportunities = []
            
            # Use provided symbols or default pairs
            if symbols:
                pairs_to_scan = self._filter_cross_asset_pairs(symbols)
            else:
                pairs_to_scan = self.cross_asset_pairs
            
            for pair in pairs_to_scan:
                try:
                    opportunity = await self._analyze_cross_asset_pair(pair)
                    if opportunity and opportunity.profit_percent >= self.arbitrage_parameters['min_profit_percent']:
                        opportunities.append(opportunity)
                        
                        # Store opportunity
                        key = f"{pair[0]}_{pair[1]}_{pair[2]}"
                        self.cross_asset_opportunities[key] = opportunity
                        
                except Exception as e:
                    logger.error(f"Error analyzing cross-asset pair {pair}: {str(e)}")
                    continue
            
            # Sort by profit percentage
            opportunities.sort(key=lambda x: x.profit_percent, reverse=True)
            
            logger.info(f"Found {len(opportunities)} cross-asset arbitrage opportunities")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error scanning cross-asset opportunities: {str(e)}")
            return []
    
    def _filter_triangular_pairs(self, symbols: List[str]) -> List[Tuple[str, str, str]]:
        """Filter triangular pairs based on available symbols"""
        try:
            filtered_pairs = []
            
            for pair in self.triangular_pairs:
                if all(symbol in symbols for symbol in pair):
                    filtered_pairs.append(pair)
            
            return filtered_pairs
            
        except Exception as e:
            logger.error(f"Error filtering triangular pairs: {str(e)}")
            return []
    
    def _filter_cross_asset_pairs(self, symbols: List[str]) -> List[Tuple[str, str, str]]:
        """Filter cross-asset pairs based on available symbols"""
        try:
            filtered_pairs = []
            
            for pair in self.cross_asset_pairs:
                # Check if we have the necessary trading pairs
                base, quote, intermediate = pair
                required_pairs = [
                    f"{base}/{intermediate}",
                    f"{quote}/{intermediate}",
                    f"{base}/{quote}"
                ]
                
                if any(pair in symbols for pair in required_pairs):
                    filtered_pairs.append(pair)
            
            return filtered_pairs
            
        except Exception as e:
            logger.error(f"Error filtering cross-asset pairs: {str(e)}")
            return []
    
    async def _analyze_triangular_pair(self, pair: Tuple[str, str, str]) -> Optional[TriangularArbitrageOpportunity]:
        """Analyze a triangular arbitrage pair"""
        try:
            symbol1, symbol2, symbol3 = pair
            
            # Get current prices
            prices = await self._get_triangular_prices(symbol1, symbol2, symbol3)
            if not prices:
                return None
            
            # Calculate arbitrage opportunity
            opportunity = self._calculate_triangular_arbitrage(symbol1, symbol2, symbol3, prices)
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error analyzing triangular pair {pair}: {str(e)}")
            return None
    
    async def _get_triangular_prices(self, symbol1: str, symbol2: str, symbol3: str) -> Optional[Dict]:
        """Get prices for triangular arbitrage"""
        try:
            # Get prices from both exchanges
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            prices = {}
            
            # Get prices for each symbol
            for symbol in [symbol1, symbol2, symbol3]:
                try:
                    # Try Binance first
                    binance_ticker = await binance_exchange.get_ticker(symbol)
                    if binance_ticker:
                        prices[f"{symbol}_binance"] = binance_ticker['last']
                    
                    # Try Kraken
                    kraken_ticker = await kraken_exchange.get_ticker(symbol)
                    if kraken_ticker:
                        prices[f"{symbol}_kraken"] = kraken_ticker['last']
                        
                except Exception as e:
                    logger.debug(f"Could not get price for {symbol}: {str(e)}")
                    continue
            
            return prices if prices else None
            
        except Exception as e:
            logger.error(f"Error getting triangular prices: {str(e)}")
            return None
    
    def _calculate_triangular_arbitrage(self, symbol1: str, symbol2: str, symbol3: str, 
                                      prices: Dict) -> Optional[TriangularArbitrageOpportunity]:
        """Calculate triangular arbitrage opportunity"""
        try:
            # Example: BTC/USDT -> ETH/BTC -> ETH/USDT
            # Path 1: Buy BTC with USDT
            # Path 2: Buy ETH with BTC
            # Path 3: Sell ETH for USDT
            
            # Get prices (simplified calculation)
            btc_usdt_price = prices.get(f"{symbol1}_binance", 0) or prices.get(f"{symbol1}_kraken", 0)
            eth_btc_price = prices.get(f"{symbol2}_binance", 0) or prices.get(f"{symbol2}_kraken", 0)
            eth_usdt_price = prices.get(f"{symbol3}_binance", 0) or prices.get(f"{symbol3}_kraken", 0)
            
            if not all([btc_usdt_price, eth_btc_price, eth_usdt_price]):
                return None
            
            # Calculate arbitrage
            # Start with 1 USDT
            start_amount = 1.0
            
            # Path 1: 1 USDT -> BTC
            btc_amount = start_amount / btc_usdt_price
            
            # Path 2: BTC -> ETH
            eth_amount = btc_amount / eth_btc_price
            
            # Path 3: ETH -> USDT
            final_amount = eth_amount * eth_usdt_price
            
            # Calculate profit
            profit_amount = final_amount - start_amount
            profit_percent = (profit_amount / start_amount) * 100
            
            # Calculate confidence based on price consistency
            confidence = self._calculate_triangular_confidence(prices)
            
            # Calculate liquidity score
            liquidity_score = self._calculate_liquidity_score(symbol1, symbol2, symbol3)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(symbol1, symbol2, symbol3)
            
            # Check if opportunity meets criteria
            if (profit_percent >= self.arbitrage_parameters['min_profit_percent'] and
                liquidity_score >= self.arbitrage_parameters['min_liquidity_score'] and
                risk_score <= self.arbitrage_parameters['max_risk_score'] and
                confidence >= self.arbitrage_parameters['confidence_threshold']):
                
                return TriangularArbitrageOpportunity(
                    symbol1=symbol1,
                    symbol2=symbol2,
                    symbol3=symbol3,
                    path1_rate=btc_usdt_price,
                    path2_rate=eth_btc_price,
                    path3_rate=eth_usdt_price,
                    profit_percent=profit_percent,
                    profit_amount=profit_amount,
                    exchange='binance',  # Default exchange
                    timestamp=time.time(),
                    confidence=confidence
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating triangular arbitrage: {str(e)}")
            return None
    
    async def _analyze_cross_asset_pair(self, pair: Tuple[str, str, str]) -> Optional[CrossAssetOpportunity]:
        """Analyze a cross-asset arbitrage pair"""
        try:
            base_asset, quote_asset, intermediate_asset = pair
            
            # Get prices from both exchanges
            prices = await self._get_cross_asset_prices(base_asset, quote_asset, intermediate_asset)
            if not prices:
                return None
            
            # Calculate arbitrage opportunity
            opportunity = self._calculate_cross_asset_arbitrage(base_asset, quote_asset, intermediate_asset, prices)
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error analyzing cross-asset pair {pair}: {str(e)}")
            return None
    
    async def _get_cross_asset_prices(self, base_asset: str, quote_asset: str, 
                                    intermediate_asset: str) -> Optional[Dict]:
        """Get prices for cross-asset arbitrage"""
        try:
            # Get prices from both exchanges
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            prices = {}
            
            # Get prices for cross-asset pairs
            pairs_to_check = [
                f"{base_asset}/{intermediate_asset}",
                f"{quote_asset}/{intermediate_asset}",
                f"{base_asset}/{quote_asset}"
            ]
            
            for pair in pairs_to_check:
                try:
                    # Try Binance
                    binance_ticker = await binance_exchange.get_ticker(pair)
                    if binance_ticker:
                        prices[f"{pair}_binance"] = binance_ticker['last']
                    
                    # Try Kraken
                    kraken_ticker = await kraken_exchange.get_ticker(pair)
                    if kraken_ticker:
                        prices[f"{pair}_kraken"] = kraken_ticker['last']
                        
                except Exception as e:
                    logger.debug(f"Could not get price for {pair}: {str(e)}")
                    continue
            
            return prices if prices else None
            
        except Exception as e:
            logger.error(f"Error getting cross-asset prices: {str(e)}")
            return None
    
    def _calculate_cross_asset_arbitrage(self, base_asset: str, quote_asset: str, 
                                       intermediate_asset: str, prices: Dict) -> Optional[CrossAssetOpportunity]:
        """Calculate cross-asset arbitrage opportunity"""
        try:
            # Example: BTC -> ETH -> USDT vs BTC -> USDT
            # Check if we can get better rate through intermediate asset
            
            # Get direct rate
            direct_pair = f"{base_asset}/{quote_asset}"
            direct_rate_binance = prices.get(f"{direct_pair}_binance", 0)
            direct_rate_kraken = prices.get(f"{direct_pair}_kraken", 0)
            
            # Get indirect rates
            base_intermediate_pair = f"{base_asset}/{intermediate_asset}"
            quote_intermediate_pair = f"{quote_asset}/{intermediate_asset}"
            
            base_intermediate_rate_binance = prices.get(f"{base_intermediate_pair}_binance", 0)
            base_intermediate_rate_kraken = prices.get(f"{base_intermediate_pair}_kraken", 0)
            
            quote_intermediate_rate_binance = prices.get(f"{quote_intermediate_pair}_binance", 0)
            quote_intermediate_rate_kraken = prices.get(f"{quote_intermediate_pair}_kraken", 0)
            
            # Calculate indirect rate
            if (base_intermediate_rate_binance and quote_intermediate_rate_kraken):
                indirect_rate = base_intermediate_rate_binance / quote_intermediate_rate_kraken
                exchange1 = 'binance'
                exchange2 = 'kraken'
            elif (base_intermediate_rate_kraken and quote_intermediate_rate_binance):
                indirect_rate = base_intermediate_rate_kraken / quote_intermediate_rate_binance
                exchange1 = 'kraken'
                exchange2 = 'binance'
            else:
                return None
            
            # Compare rates
            if direct_rate_binance and indirect_rate > direct_rate_binance:
                # Arbitrage opportunity: sell through intermediate, buy direct
                profit_percent = ((indirect_rate - direct_rate_binance) / direct_rate_binance) * 100
                profit_amount = indirect_rate - direct_rate_binance
                
                return CrossAssetOpportunity(
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    intermediate_asset=intermediate_asset,
                    exchange1=exchange1,
                    exchange2=exchange2,
                    rate1=indirect_rate,
                    rate2=direct_rate_binance,
                    profit_percent=profit_percent,
                    profit_amount=profit_amount,
                    timestamp=time.time(),
                    confidence=0.8
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating cross-asset arbitrage: {str(e)}")
            return None
    
    def _calculate_triangular_confidence(self, prices: Dict) -> float:
        """Calculate confidence in triangular arbitrage opportunity"""
        try:
            # Check price consistency across exchanges
            price_variations = []
            
            for key, price in prices.items():
                symbol = key.split('_')[0]
                exchange = key.split('_')[1]
                
                # Find corresponding price on other exchange
                other_key = f"{symbol}_{'kraken' if exchange == 'binance' else 'binance'}"
                other_price = prices.get(other_key, 0)
                
                if other_price > 0:
                    variation = abs(price - other_price) / price
                    price_variations.append(variation)
            
            if not price_variations:
                return 0.5  # Default confidence
            
            # Calculate average variation
            avg_variation = sum(price_variations) / len(price_variations)
            
            # Convert variation to confidence (lower variation = higher confidence)
            confidence = max(0.0, 1.0 - avg_variation * 10)
            
            return min(1.0, confidence)
            
        except Exception as e:
            logger.error(f"Error calculating triangular confidence: {str(e)}")
            return 0.5
    
    def _calculate_liquidity_score(self, symbol1: str, symbol2: str, symbol3: str) -> float:
        """Calculate liquidity score for triangular arbitrage"""
        try:
            # Simplified liquidity scoring based on symbol popularity
            liquidity_scores = {
                'BTC/USDT': 1.0, 'ETH/USDT': 0.9, 'BNB/USDT': 0.8,
                'ADA/USDT': 0.7, 'DOT/USDT': 0.6, 'LINK/USDT': 0.7,
                'UNI/USDT': 0.6, 'LTC/USDT': 0.7, 'BCH/USDT': 0.6,
                'USDT/USDC': 0.9, 'DAI/USDT': 0.8, 'BUSD/USDT': 0.8
            }
            
            # Get liquidity scores for each symbol
            score1 = liquidity_scores.get(symbol1, 0.5)
            score2 = liquidity_scores.get(symbol2, 0.5)
            score3 = liquidity_scores.get(symbol3, 0.5)
            
            # Average liquidity score
            avg_liquidity = (score1 + score2 + score3) / 3
            
            return avg_liquidity
            
        except Exception as e:
            logger.error(f"Error calculating liquidity score: {str(e)}")
            return 0.5
    
    def _calculate_risk_score(self, symbol1: str, symbol2: str, symbol3: str) -> float:
        """Calculate risk score for triangular arbitrage"""
        try:
            # Risk factors
            risk_factors = []
            
            # Volatility risk
            volatility_scores = {
                'BTC/USDT': 0.3, 'ETH/USDT': 0.4, 'BNB/USDT': 0.5,
                'ADA/USDT': 0.6, 'DOT/USDT': 0.6, 'LINK/USDT': 0.5,
                'UNI/USDT': 0.6, 'LTC/USDT': 0.4, 'BCH/USDT': 0.5,
                'USDT/USDC': 0.1, 'DAI/USDT': 0.2, 'BUSD/USDT': 0.1
            }
            
            vol1 = volatility_scores.get(symbol1, 0.5)
            vol2 = volatility_scores.get(symbol2, 0.5)
            vol3 = volatility_scores.get(symbol3, 0.5)
            
            avg_volatility = (vol1 + vol2 + vol3) / 3
            risk_factors.append(avg_volatility)
            
            # Execution risk (more steps = higher risk)
            execution_risk = 0.3  # Base execution risk
            risk_factors.append(execution_risk)
            
            # Calculate total risk score
            total_risk = sum(risk_factors) / len(risk_factors)
            
            return min(1.0, max(0.0, total_risk))
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 0.5
    
    async def execute_triangular_arbitrage(self, opportunity: TriangularArbitrageOpportunity, 
                                         amount: float) -> bool:
        """Execute triangular arbitrage opportunity"""
        try:
            logger.info(f"Executing triangular arbitrage: {opportunity.symbol1} -> {opportunity.symbol2} -> {opportunity.symbol3}")
            logger.info(f"Expected profit: {opportunity.profit_percent:.3f}% (${opportunity.profit_amount:.4f})")
            
            # Get exchange
            exchange = self.exchange_manager.get_exchange(opportunity.exchange)
            
            # Step 1: Buy first asset
            try:
                order1 = await exchange.place_market_order(opportunity.symbol1, 'buy', amount)
                logger.info(f"Step 1 completed: Bought {amount} {opportunity.symbol1}")
            except Exception as e:
                logger.error(f"Step 1 failed: {str(e)}")
                return False
            
            # Step 2: Convert to second asset
            try:
                # Calculate amount for second trade
                amount2 = amount / opportunity.path1_rate
                order2 = await exchange.place_market_order(opportunity.symbol2, 'buy', amount2)
                logger.info(f"Step 2 completed: Bought {amount2} {opportunity.symbol2}")
            except Exception as e:
                logger.error(f"Step 2 failed: {str(e)}")
                return False
            
            # Step 3: Convert to third asset
            try:
                # Calculate amount for third trade
                amount3 = amount2 / opportunity.path2_rate
                order3 = await exchange.place_market_order(opportunity.symbol3, 'sell', amount3)
                logger.info(f"Step 3 completed: Sold {amount3} {opportunity.symbol3}")
            except Exception as e:
                logger.error(f"Step 3 failed: {str(e)}")
                return False
            
            # Record execution
            self._record_arbitrage_execution(opportunity, amount, True)
            
            logger.info("Triangular arbitrage executed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error executing triangular arbitrage: {str(e)}")
            self._record_arbitrage_execution(opportunity, amount, False)
            return False
    
    def _record_arbitrage_execution(self, opportunity: TriangularArbitrageOpportunity, 
                                  amount: float, success: bool):
        """Record arbitrage execution for learning"""
        try:
            key = f"{opportunity.symbol1}_{opportunity.symbol2}_{opportunity.symbol3}"
            
            if key not in self.arbitrage_history:
                self.arbitrage_history[key] = []
            
            execution_record = {
                'timestamp': time.time(),
                'amount': amount,
                'profit_percent': opportunity.profit_percent,
                'success': success,
                'confidence': opportunity.confidence
            }
            
            self.arbitrage_history[key].append(execution_record)
            
            # Keep only recent history (last 100 records)
            if len(self.arbitrage_history[key]) > 100:
                self.arbitrage_history[key] = self.arbitrage_history[key][-100:]
            
            logger.debug(f"Recorded arbitrage execution: {key}, Success: {success}")
            
        except Exception as e:
            logger.error(f"Error recording arbitrage execution: {str(e)}")
    
    def get_arbitrage_summary(self, days: int = 7) -> Dict:
        """Get arbitrage performance summary"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 3600)
            
            summary = {
                'triangular_opportunities': len(self.triangular_opportunities),
                'cross_asset_opportunities': len(self.cross_asset_opportunities),
                'execution_history': {},
                'performance_metrics': {}
            }
            
            # Analyze execution history
            for key, executions in self.arbitrage_history.items():
                recent_executions = [
                    exec_record for exec_record in executions
                    if exec_record['timestamp'] >= cutoff_time
                ]
                
                if recent_executions:
                    successful_executions = [e for e in recent_executions if e['success']]
                    success_rate = len(successful_executions) / len(recent_executions) * 100
                    avg_profit = sum(e['profit_percent'] for e in successful_executions) / len(successful_executions) if successful_executions else 0
                    
                    summary['execution_history'][key] = {
                        'total_executions': len(recent_executions),
                        'successful_executions': len(successful_executions),
                        'success_rate': success_rate,
                        'avg_profit_percent': avg_profit
                    }
            
            # Calculate performance metrics
            all_executions = []
            for executions in self.arbitrage_history.values():
                all_executions.extend(executions)
            
            if all_executions:
                recent_all = [e for e in all_executions if e['timestamp'] >= cutoff_time]
                successful_all = [e for e in recent_all if e['success']]
                
                summary['performance_metrics'] = {
                    'total_executions': len(recent_all),
                    'successful_executions': len(successful_all),
                    'overall_success_rate': len(successful_all) / len(recent_all) * 100 if recent_all else 0,
                    'avg_profit_percent': sum(e['profit_percent'] for e in successful_all) / len(successful_all) if successful_all else 0,
                    'total_profit': sum(e['profit_percent'] for e in successful_all) if successful_all else 0
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting arbitrage summary: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations for arbitrage"""
        try:
            recommendations = []
            
            # Get performance summary
            summary = self.get_arbitrage_summary(30)
            
            if not summary:
                return ["No arbitrage data available for recommendations"]
            
            # Success rate recommendations
            overall_success_rate = summary.get('performance_metrics', {}).get('overall_success_rate', 0)
            if overall_success_rate > 80:
                recommendations.append("High success rate - current arbitrage strategy appears optimal")
            elif overall_success_rate < 60:
                recommendations.append("Low success rate - consider adjusting profit thresholds")
            
            # Profit recommendations
            avg_profit = summary.get('performance_metrics', {}).get('avg_profit_percent', 0)
            if avg_profit > 1.0:
                recommendations.append("Good profit margins - consider increasing position sizes")
            elif avg_profit < 0.5:
                recommendations.append("Low profit margins - consider focusing on higher-profit opportunities")
            
            # Opportunity recommendations
            triangular_count = summary.get('triangular_opportunities', 0)
            cross_asset_count = summary.get('cross_asset_opportunities', 0)
            
            if triangular_count > cross_asset_count:
                recommendations.append("More triangular opportunities - focus on triangular arbitrage")
            else:
                recommendations.append("More cross-asset opportunities - focus on cross-asset arbitrage")
            
            # Execution recommendations
            total_executions = summary.get('performance_metrics', {}).get('total_executions', 0)
            if total_executions < 10:
                recommendations.append("Low execution frequency - consider lowering profit thresholds")
            elif total_executions > 100:
                recommendations.append("High execution frequency - consider raising profit thresholds")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return ["Error generating recommendations"]

