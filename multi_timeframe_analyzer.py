import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class Candlestick:
    """Data class for candlestick data"""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str

@dataclass
class TechnicalIndicator:
    """Data class for technical indicators"""
    name: str
    value: float
    signal: str
    strength: float
    timestamp: float
    timeframe: str

@dataclass
class MarketTrend:
    """Data class for market trend analysis"""
    timeframe: str
    trend_direction: str
    trend_strength: float
    support_level: float
    resistance_level: float
    confidence: float
    timestamp: float

@dataclass
class MultiTimeframeAnalysis:
    """Data class for multi-timeframe analysis"""
    symbol: str
    timeframes: List[str]
    trends: Dict[str, MarketTrend]
    indicators: Dict[str, List[TechnicalIndicator]]
    signals: List[str]
    overall_sentiment: str
    confidence: float
    timestamp: float

class MultiTimeframeAnalyzer:
    """Multi-timeframe market analysis system"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.candlestick_data = {}
        self.technical_indicators = {}
        self.trend_analysis = {}
        self.analysis_history = {}
        
        # Timeframe configurations
        self.timeframes = {
            '1m': {'seconds': 60, 'weight': 0.1, 'description': '1 minute'},
            '5m': {'seconds': 300, 'weight': 0.2, 'description': '5 minutes'},
            '15m': {'seconds': 900, 'weight': 0.3, 'description': '15 minutes'},
            '1h': {'seconds': 3600, 'weight': 0.25, 'description': '1 hour'},
            '4h': {'seconds': 14400, 'weight': 0.15, 'description': '4 hours'}
        }
        
        # Technical indicators
        self.indicators = {
            'sma_20': {'name': 'Simple Moving Average 20', 'timeframes': ['5m', '15m', '1h']},
            'sma_50': {'name': 'Simple Moving Average 50', 'timeframes': ['15m', '1h', '4h']},
            'ema_12': {'name': 'Exponential Moving Average 12', 'timeframes': ['5m', '15m']},
            'ema_26': {'name': 'Exponential Moving Average 26', 'timeframes': ['5m', '15m', '1h']},
            'rsi': {'name': 'Relative Strength Index', 'timeframes': ['5m', '15m', '1h']},
            'macd': {'name': 'MACD', 'timeframes': ['15m', '1h', '4h']},
            'bollinger': {'name': 'Bollinger Bands', 'timeframes': ['15m', '1h']},
            'stochastic': {'name': 'Stochastic Oscillator', 'timeframes': ['5m', '15m']}
        }
        
        # Trend analysis parameters
        self.trend_parameters = {
            'min_trend_length': 5,  # Minimum candlesticks for trend
            'trend_threshold': 0.02,  # 2% price change for trend
            'support_resistance_lookback': 20,  # Lookback periods for S/R levels
            'trend_confirmation_threshold': 0.7  # 70% confidence threshold
        }
        
    async def analyze_multi_timeframe(self, symbol: str) -> MultiTimeframeAnalysis:
        """Perform multi-timeframe analysis for a symbol"""
        try:
            # Collect candlestick data for all timeframes
            await self._collect_candlestick_data(symbol)
            
            # Calculate technical indicators
            await self._calculate_technical_indicators(symbol)
            
            # Analyze trends for each timeframe
            trends = await self._analyze_trends(symbol)
            
            # Generate trading signals
            signals = await self._generate_trading_signals(symbol, trends)
            
            # Determine overall sentiment
            overall_sentiment = self._determine_overall_sentiment(trends)
            
            # Calculate confidence
            confidence = self._calculate_analysis_confidence(trends)
            
            analysis = MultiTimeframeAnalysis(
                symbol=symbol,
                timeframes=list(self.timeframes.keys()),
                trends=trends,
                indicators=self.technical_indicators.get(symbol, {}),
                signals=signals,
                overall_sentiment=overall_sentiment,
                confidence=confidence,
                timestamp=time.time()
            )
            
            # Store analysis
            if symbol not in self.analysis_history:
                self.analysis_history[symbol] = []
            
            self.analysis_history[symbol].append(analysis)
            
            # Keep only recent history (last 100 analyses)
            if len(self.analysis_history[symbol]) > 100:
                self.analysis_history[symbol] = self.analysis_history[symbol][-100:]
            
            logger.info(f"Multi-timeframe analysis for {symbol}: "
                       f"Sentiment={overall_sentiment}, Confidence={confidence:.3f}, "
                       f"Signals={len(signals)}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error performing multi-timeframe analysis for {symbol}: {str(e)}")
            return MultiTimeframeAnalysis(
                symbol=symbol,
                timeframes=[],
                trends={},
                indicators={},
                signals=[],
                overall_sentiment='neutral',
                confidence=0.0,
                timestamp=time.time()
            )
    
    async def _collect_candlestick_data(self, symbol: str):
        """Collect candlestick data for all timeframes"""
        try:
            if symbol not in self.candlestick_data:
                self.candlestick_data[symbol] = {}
            
            for timeframe, config in self.timeframes.items():
                # Get candlestick data for this timeframe
                candlesticks = await self._get_candlestick_data(symbol, timeframe, 100)
                
                if candlesticks:
                    self.candlestick_data[symbol][timeframe] = candlesticks
                    
                    logger.debug(f"Collected {len(candlesticks)} candlesticks for {symbol} {timeframe}")
                else:
                    logger.warning(f"No candlestick data available for {symbol} {timeframe}")
            
        except Exception as e:
            logger.error(f"Error collecting candlestick data for {symbol}: {str(e)}")
    
    async def _get_candlestick_data(self, symbol: str, timeframe: str, limit: int) -> List[Candlestick]:
        """Get candlestick data from exchange"""
        try:
            # Get data from both exchanges and combine
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            # Convert timeframe to exchange format
            exchange_timeframe = self._convert_timeframe_format(timeframe)
            
            # Get data from Binance (primary)
            binance_data = await binance_exchange.get_candles(symbol, exchange_timeframe, limit)
            
            # Get data from Kraken (secondary)
            kraken_data = await kraken_exchange.get_candles(symbol, exchange_timeframe, limit)
            
            # Combine and average the data
            combined_data = []
            
            if binance_data and kraken_data:
                # Use the shorter dataset as reference
                min_length = min(len(binance_data), len(kraken_data))
                
                for i in range(min_length):
                    binance_candle = binance_data[i]
                    kraken_candle = kraken_data[i]
                    
                    # Average the prices
                    combined_candle = Candlestick(
                        timestamp=binance_candle['timestamp'],
                        open=(binance_candle['open'] + kraken_candle['open']) / 2,
                        high=(binance_candle['high'] + kraken_candle['high']) / 2,
                        low=(binance_candle['low'] + kraken_candle['low']) / 2,
                        close=(binance_candle['close'] + kraken_candle['close']) / 2,
                        volume=(binance_candle['volume'] + kraken_candle['volume']) / 2,
                        timeframe=timeframe
                    )
                    
                    combined_data.append(combined_candle)
            
            elif binance_data:
                # Use only Binance data
                for candle_data in binance_data:
                    candle = Candlestick(
                        timestamp=candle_data['timestamp'],
                        open=candle_data['open'],
                        high=candle_data['high'],
                        low=candle_data['low'],
                        close=candle_data['close'],
                        volume=candle_data['volume'],
                        timeframe=timeframe
                    )
                    combined_data.append(candle)
            
            return combined_data
            
        except Exception as e:
            logger.error(f"Error getting candlestick data for {symbol} {timeframe}: {str(e)}")
            return []
    
    def _convert_timeframe_format(self, timeframe: str) -> str:
        """Convert internal timeframe format to exchange format"""
        conversions = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '4h'
        }
        
        return conversions.get(timeframe, '1h')
    
    async def _calculate_technical_indicators(self, symbol: str):
        """Calculate technical indicators for all timeframes"""
        try:
            if symbol not in self.candlestick_data:
                return
            
            if symbol not in self.technical_indicators:
                self.technical_indicators[symbol] = {}
            
            for timeframe, candlesticks in self.candlestick_data[symbol].items():
                if timeframe not in self.technical_indicators[symbol]:
                    self.technical_indicators[symbol][timeframe] = []
                
                indicators = []
                
                # Calculate indicators based on timeframe
                if timeframe in ['5m', '15m', '1h']:
                    # SMA 20
                    sma_20 = self._calculate_sma(candlesticks, 20)
                    if sma_20 is not None:
                        indicators.append(TechnicalIndicator(
                            name='SMA_20',
                            value=sma_20,
                            signal=self._get_sma_signal(candlesticks, sma_20),
                            strength=0.7,
                            timestamp=time.time(),
                            timeframe=timeframe
                        ))
                
                if timeframe in ['15m', '1h', '4h']:
                    # SMA 50
                    sma_50 = self._calculate_sma(candlesticks, 50)
                    if sma_50 is not None:
                        indicators.append(TechnicalIndicator(
                            name='SMA_50',
                            value=sma_50,
                            signal=self._get_sma_signal(candlesticks, sma_50),
                            strength=0.8,
                            timestamp=time.time(),
                            timeframe=timeframe
                        ))
                
                if timeframe in ['5m', '15m']:
                    # RSI
                    rsi = self._calculate_rsi(candlesticks, 14)
                    if rsi is not None:
                        indicators.append(TechnicalIndicator(
                            name='RSI',
                            value=rsi,
                            signal=self._get_rsi_signal(rsi),
                            strength=0.6,
                            timestamp=time.time(),
                            timeframe=timeframe
                        ))
                
                if timeframe in ['15m', '1h', '4h']:
                    # MACD
                    macd_line, signal_line, histogram = self._calculate_macd(candlesticks)
                    if macd_line is not None:
                        indicators.append(TechnicalIndicator(
                            name='MACD',
                            value=macd_line,
                            signal=self._get_macd_signal(macd_line, signal_line, histogram),
                            strength=0.7,
                            timestamp=time.time(),
                            timeframe=timeframe
                        ))
                
                # Store indicators
                self.technical_indicators[symbol][timeframe] = indicators
                
                logger.debug(f"Calculated {len(indicators)} indicators for {symbol} {timeframe}")
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators for {symbol}: {str(e)}")
    
    def _calculate_sma(self, candlesticks: List[Candlestick], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        try:
            if len(candlesticks) < period:
                return None
            
            recent_candles = candlesticks[-period:]
            sma = sum(candle.close for candle in recent_candles) / period
            
            return sma
            
        except Exception as e:
            logger.error(f"Error calculating SMA: {str(e)}")
            return None
    
    def _calculate_rsi(self, candlesticks: List[Candlestick], period: int) -> Optional[float]:
        """Calculate Relative Strength Index"""
        try:
            if len(candlesticks) < period + 1:
                return None
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(candlesticks)):
                change = candlesticks[i].close - candlesticks[i-1].close
                price_changes.append(change)
            
            if len(price_changes) < period:
                return None
            
            # Calculate gains and losses
            gains = [max(change, 0) for change in price_changes[-period:]]
            losses = [abs(min(change, 0)) for change in price_changes[-period:]]
            
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            return None
    
    def _calculate_macd(self, candlesticks: List[Candlestick]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate MACD"""
        try:
            if len(candlesticks) < 26:
                return None, None, None
            
            # Calculate EMAs
            ema_12 = self._calculate_ema(candlesticks, 12)
            ema_26 = self._calculate_ema(candlesticks, 26)
            
            if ema_12 is None or ema_26 is None:
                return None, None, None
            
            # MACD line
            macd_line = ema_12 - ema_26
            
            # Signal line (9-period EMA of MACD line)
            # For simplicity, we'll use a simplified calculation
            signal_line = macd_line * 0.9  # Approximate
            
            # Histogram
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            return None, None, None
    
    def _calculate_ema(self, candlesticks: List[Candlestick], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        try:
            if len(candlesticks) < period:
                return None
            
            # Calculate smoothing factor
            smoothing_factor = 2 / (period + 1)
            
            # Start with SMA
            sma = self._calculate_sma(candlesticks, period)
            if sma is None:
                return None
            
            # Calculate EMA
            ema = sma
            for i in range(period, len(candlesticks)):
                ema = (candlesticks[i].close * smoothing_factor) + (ema * (1 - smoothing_factor))
            
            return ema
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {str(e)}")
            return None
    
    def _get_sma_signal(self, candlesticks: List[Candlestick], sma: float) -> str:
        """Get SMA signal"""
        try:
            if not candlesticks:
                return 'neutral'
            
            current_price = candlesticks[-1].close
            
            if current_price > sma * 1.01:  # 1% above SMA
                return 'bullish'
            elif current_price < sma * 0.99:  # 1% below SMA
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.error(f"Error getting SMA signal: {str(e)}")
            return 'neutral'
    
    def _get_rsi_signal(self, rsi: float) -> str:
        """Get RSI signal"""
        try:
            if rsi > 70:
                return 'bearish'  # Overbought
            elif rsi < 30:
                return 'bullish'  # Oversold
            else:
                return 'neutral'
                
        except Exception as e:
            logger.error(f"Error getting RSI signal: {str(e)}")
            return 'neutral'
    
    def _get_macd_signal(self, macd_line: float, signal_line: float, histogram: float) -> str:
        """Get MACD signal"""
        try:
            if macd_line > signal_line and histogram > 0:
                return 'bullish'
            elif macd_line < signal_line and histogram < 0:
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.error(f"Error getting MACD signal: {str(e)}")
            return 'neutral'
    
    async def _analyze_trends(self, symbol: str) -> Dict[str, MarketTrend]:
        """Analyze trends for each timeframe"""
        try:
            trends = {}
            
            if symbol not in self.candlestick_data:
                return trends
            
            for timeframe, candlesticks in self.candlestick_data[symbol].items():
                if len(candlesticks) < self.trend_parameters['min_trend_length']:
                    continue
                
                # Analyze trend direction
                trend_direction = self._analyze_trend_direction(candlesticks)
                
                # Calculate trend strength
                trend_strength = self._calculate_trend_strength(candlesticks, trend_direction)
                
                # Find support and resistance levels
                support_level, resistance_level = self._find_support_resistance(candlesticks)
                
                # Calculate confidence
                confidence = self._calculate_trend_confidence(candlesticks, trend_direction, trend_strength)
                
                trend = MarketTrend(
                    timeframe=timeframe,
                    trend_direction=trend_direction,
                    trend_strength=trend_strength,
                    support_level=support_level,
                    resistance_level=resistance_level,
                    confidence=confidence,
                    timestamp=time.time()
                )
                
                trends[timeframe] = trend
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing trends for {symbol}: {str(e)}")
            return {}
    
    def _analyze_trend_direction(self, candlesticks: List[Candlestick]) -> str:
        """Analyze trend direction"""
        try:
            if len(candlesticks) < 10:
                return 'neutral'
            
            # Calculate price change over recent periods
            recent_periods = min(10, len(candlesticks) - 1)
            start_price = candlesticks[-recent_periods].close
            end_price = candlesticks[-1].close
            
            price_change_percent = (end_price - start_price) / start_price * 100
            
            if price_change_percent > self.trend_parameters['trend_threshold'] * 100:
                return 'uptrend'
            elif price_change_percent < -self.trend_parameters['trend_threshold'] * 100:
                return 'downtrend'
            else:
                return 'sideways'
                
        except Exception as e:
            logger.error(f"Error analyzing trend direction: {str(e)}")
            return 'neutral'
    
    def _calculate_trend_strength(self, candlesticks: List[Candlestick], trend_direction: str) -> float:
        """Calculate trend strength"""
        try:
            if len(candlesticks) < 10:
                return 0.0
            
            # Calculate price momentum
            recent_periods = min(20, len(candlesticks) - 1)
            price_changes = []
            
            for i in range(len(candlesticks) - recent_periods, len(candlesticks)):
                if i > 0:
                    change = (candlesticks[i].close - candlesticks[i-1].close) / candlesticks[i-1].close
                    price_changes.append(change)
            
            if not price_changes:
                return 0.0
            
            # Calculate consistency of trend
            if trend_direction == 'uptrend':
                positive_changes = sum(1 for change in price_changes if change > 0)
                consistency = positive_changes / len(price_changes)
            elif trend_direction == 'downtrend':
                negative_changes = sum(1 for change in price_changes if change < 0)
                consistency = negative_changes / len(price_changes)
            else:
                consistency = 0.5  # Neutral
            
            # Calculate momentum
            momentum = abs(sum(price_changes)) / len(price_changes)
            
            # Combine consistency and momentum
            trend_strength = (consistency + momentum) / 2
            
            return min(1.0, max(0.0, trend_strength))
            
        except Exception as e:
            logger.error(f"Error calculating trend strength: {str(e)}")
            return 0.0
    
    def _find_support_resistance(self, candlesticks: List[Candlestick]) -> Tuple[float, float]:
        """Find support and resistance levels"""
        try:
            if len(candlesticks) < self.trend_parameters['support_resistance_lookback']:
                return 0.0, 0.0
            
            # Get recent highs and lows
            recent_candles = candlesticks[-self.trend_parameters['support_resistance_lookback']:]
            
            highs = [candle.high for candle in recent_candles]
            lows = [candle.low for candle in recent_candles]
            
            # Find resistance (recent high)
            resistance_level = max(highs)
            
            # Find support (recent low)
            support_level = min(lows)
            
            return support_level, resistance_level
            
        except Exception as e:
            logger.error(f"Error finding support/resistance: {str(e)}")
            return 0.0, 0.0
    
    def _calculate_trend_confidence(self, candlesticks: List[Candlestick], trend_direction: str, trend_strength: float) -> float:
        """Calculate confidence in trend analysis"""
        try:
            if len(candlesticks) < 10:
                return 0.0
            
            # Base confidence on trend strength
            base_confidence = trend_strength
            
            # Adjust for data quality (more data = higher confidence)
            data_quality = min(1.0, len(candlesticks) / 100)
            
            # Adjust for price consistency
            recent_prices = [candle.close for candle in candlesticks[-10:]]
            price_consistency = 1.0 - (max(recent_prices) - min(recent_prices)) / max(recent_prices)
            
            # Combine factors
            confidence = (base_confidence + data_quality + price_consistency) / 3
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating trend confidence: {str(e)}")
            return 0.0
    
    async def _generate_trading_signals(self, symbol: str, trends: Dict[str, MarketTrend]) -> List[str]:
        """Generate trading signals based on multi-timeframe analysis"""
        try:
            signals = []
            
            if not trends:
                return signals
            
            # Signal 1: Trend alignment across timeframes
            trend_alignment = self._check_trend_alignment(trends)
            if trend_alignment:
                signals.append(f"Trend alignment: {trend_alignment}")
            
            # Signal 2: Strong trend in multiple timeframes
            strong_trends = [tf for tf, trend in trends.items() if trend.trend_strength > 0.7]
            if len(strong_trends) >= 2:
                signals.append(f"Strong trends in {len(strong_trends)} timeframes")
            
            # Signal 3: Support/Resistance levels
            support_resistance_signals = self._check_support_resistance(trends)
            signals.extend(support_resistance_signals)
            
            # Signal 4: Trend reversal signals
            reversal_signals = self._check_trend_reversal(trends)
            signals.extend(reversal_signals)
            
            # Signal 5: Momentum signals
            momentum_signals = self._check_momentum(trends)
            signals.extend(momentum_signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating trading signals for {symbol}: {str(e)}")
            return []
    
    def _check_trend_alignment(self, trends: Dict[str, MarketTrend]) -> Optional[str]:
        """Check if trends are aligned across timeframes"""
        try:
            if len(trends) < 2:
                return None
            
            trend_directions = [trend.trend_direction for trend in trends.values()]
            
            # Check for consistent uptrend
            if all(direction == 'uptrend' for direction in trend_directions):
                return 'bullish_alignment'
            elif all(direction == 'downtrend' for direction in trend_directions):
                return 'bearish_alignment'
            elif all(direction == 'sideways' for direction in trend_directions):
                return 'sideways_alignment'
            else:
                return 'mixed_signals'
                
        except Exception as e:
            logger.error(f"Error checking trend alignment: {str(e)}")
            return None
    
    def _check_support_resistance(self, trends: Dict[str, MarketTrend]) -> List[str]:
        """Check support and resistance levels"""
        try:
            signals = []
            
            for timeframe, trend in trends.items():
                if trend.confidence > 0.7:
                    if trend.trend_direction == 'uptrend':
                        signals.append(f"{timeframe}: Strong resistance at {trend.resistance_level:.6f}")
                    elif trend.trend_direction == 'downtrend':
                        signals.append(f"{timeframe}: Strong support at {trend.support_level:.6f}")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error checking support/resistance: {str(e)}")
            return []
    
    def _check_trend_reversal(self, trends: Dict[str, MarketTrend]) -> List[str]:
        """Check for trend reversal signals"""
        try:
            signals = []
            
            # Look for divergence between timeframes
            if len(trends) >= 2:
                short_term_trends = [t for tf, t in trends.items() if tf in ['1m', '5m']]
                long_term_trends = [t for tf, t in trends.items() if tf in ['1h', '4h']]
                
                if short_term_trends and long_term_trends:
                    short_term_direction = short_term_trends[0].trend_direction
                    long_term_direction = long_term_trends[0].trend_direction
                    
                    if short_term_direction != long_term_direction:
                        signals.append(f"Trend reversal signal: {short_term_direction} vs {long_term_direction}")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error checking trend reversal: {str(e)}")
            return []
    
    def _check_momentum(self, trends: Dict[str, MarketTrend]) -> List[str]:
        """Check momentum signals"""
        try:
            signals = []
            
            strong_trends = [tf for tf, trend in trends.items() if trend.trend_strength > 0.8]
            
            if strong_trends:
                signals.append(f"Strong momentum in {len(strong_trends)} timeframes")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error checking momentum: {str(e)}")
            return []
    
    def _determine_overall_sentiment(self, trends: Dict[str, MarketTrend]) -> str:
        """Determine overall market sentiment"""
        try:
            if not trends:
                return 'neutral'
            
            # Weight trends by timeframe importance
            weighted_sentiment = 0.0
            total_weight = 0.0
            
            for timeframe, trend in trends.items():
                weight = self.timeframes.get(timeframe, {}).get('weight', 0.1)
                
                # Convert trend direction to sentiment score
                if trend.trend_direction == 'uptrend':
                    sentiment_score = 1.0
                elif trend.trend_direction == 'downtrend':
                    sentiment_score = -1.0
                else:
                    sentiment_score = 0.0
                
                # Weight by trend strength and confidence
                weighted_score = sentiment_score * trend.trend_strength * trend.confidence * weight
                weighted_sentiment += weighted_score
                total_weight += weight
            
            if total_weight == 0:
                return 'neutral'
            
            avg_sentiment = weighted_sentiment / total_weight
            
            if avg_sentiment > 0.3:
                return 'bullish'
            elif avg_sentiment < -0.3:
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.error(f"Error determining overall sentiment: {str(e)}")
            return 'neutral'
    
    def _calculate_analysis_confidence(self, trends: Dict[str, MarketTrend]) -> float:
        """Calculate confidence in overall analysis"""
        try:
            if not trends:
                return 0.0
            
            # Calculate weighted average confidence
            weighted_confidence = 0.0
            total_weight = 0.0
            
            for timeframe, trend in trends.items():
                weight = self.timeframes.get(timeframe, {}).get('weight', 0.1)
                weighted_confidence += trend.confidence * weight
                total_weight += weight
            
            if total_weight == 0:
                return 0.0
            
            return weighted_confidence / total_weight
            
        except Exception as e:
            logger.error(f"Error calculating analysis confidence: {str(e)}")
            return 0.0
    
    def get_analysis_summary(self, symbol: str = None, days: int = 7) -> Dict:
        """Get analysis summary"""
        try:
            if symbol:
                # Get specific symbol summary
                if symbol not in self.analysis_history:
                    return {}
                
                recent_analyses = [
                    analysis for analysis in self.analysis_history[symbol]
                    if time.time() - analysis.timestamp <= days * 24 * 3600
                ]
                
                if not recent_analyses:
                    return {}
                
                # Calculate statistics
                sentiments = [a.overall_sentiment for a in recent_analyses]
                confidences = [a.confidence for a in recent_analyses]
                
                sentiment_counts = {}
                for sentiment in sentiments:
                    sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
                
                summary = {
                    'symbol': symbol,
                    'total_analyses': len(recent_analyses),
                    'avg_confidence': sum(confidences) / len(confidences),
                    'sentiment_distribution': sentiment_counts,
                    'dominant_sentiment': max(sentiment_counts.keys(), key=lambda k: sentiment_counts[k]),
                    'time_period_days': days
                }
                
                return summary
            else:
                # Get all symbols summary
                summary = {}
                for sym in self.analysis_history.keys():
                    sym_summary = self.get_analysis_summary(sym, days)
                    if sym_summary:
                        summary[sym] = sym_summary
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting analysis summary: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self, symbol: str) -> List[str]:
        """Get optimization recommendations based on multi-timeframe analysis"""
        try:
            recommendations = []
            
            if symbol not in self.analysis_history:
                return ["No analysis data available for recommendations"]
            
            latest_analysis = self.analysis_history[symbol][-1]
            
            # Sentiment-based recommendations
            if latest_analysis.overall_sentiment == 'bullish':
                recommendations.append("Bullish sentiment across timeframes - consider long positions")
            elif latest_analysis.overall_sentiment == 'bearish':
                recommendations.append("Bearish sentiment across timeframes - consider short positions")
            else:
                recommendations.append("Neutral sentiment - consider range trading strategies")
            
            # Confidence-based recommendations
            if latest_analysis.confidence > 0.8:
                recommendations.append("High confidence analysis - good opportunity for larger positions")
            elif latest_analysis.confidence < 0.4:
                recommendations.append("Low confidence analysis - consider reducing position sizes")
            
            # Trend-based recommendations
            strong_trends = [tf for tf, trend in latest_analysis.trends.items() if trend.trend_strength > 0.7]
            if len(strong_trends) >= 2:
                recommendations.append(f"Strong trends in {len(strong_trends)} timeframes - good momentum opportunity")
            
            # Signal-based recommendations
            if latest_analysis.signals:
                recommendations.append(f"Multiple signals detected: {', '.join(latest_analysis.signals[:3])}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return ["Error generating recommendations"]

