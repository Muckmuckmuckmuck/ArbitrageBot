import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class MLPrediction:
    """Data class for ML model predictions"""
    symbol: str
    predicted_spread: float
    confidence: float
    features: Dict[str, float]
    model_type: str
    prediction_time: float

class BasicMLModels:
    """Basic machine learning models for spread prediction and optimization"""
    
    def __init__(self):
        self.spread_history = {}
        self.feature_cache = {}
        self.model_weights = {}
        self.prediction_history = {}
        
    def predict_spread(self, symbol: str, market_features: Dict) -> MLPrediction:
        """Predict spread using basic ML models"""
        try:
            # Get historical data
            if symbol not in self.spread_history:
                self.spread_history[symbol] = []
            
            # Extract features
            features = self._extract_features(symbol, market_features)
            
            # Use different models based on available data
            if len(self.spread_history[symbol]) < 10:
                # Not enough data for ML, use simple heuristic
                predicted_spread = self._heuristic_prediction(symbol, features)
                confidence = 0.3
                model_type = 'heuristic'
            elif len(self.spread_history[symbol]) < 50:
                # Use linear regression
                predicted_spread, confidence = self._linear_regression_prediction(symbol, features)
                model_type = 'linear_regression'
            else:
                # Use ensemble model
                predicted_spread, confidence = self._ensemble_prediction(symbol, features)
                model_type = 'ensemble'
            
            # Create prediction record
            prediction = MLPrediction(
                symbol=symbol,
                predicted_spread=predicted_spread,
                confidence=confidence,
                features=features,
                model_type=model_type,
                prediction_time=market_features.get('timestamp', 0)
            )
            
            # Store prediction
            self._store_prediction(symbol, prediction)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting spread for {symbol}: {str(e)}")
            return self._get_default_prediction(symbol, market_features)
    
    def _extract_features(self, symbol: str, market_features: Dict) -> Dict[str, float]:
        """Extract features for ML models"""
        try:
            features = {
                'volatility': market_features.get('volatility', 0.02),
                'volume_ratio': market_features.get('volume_ratio', 1.0),
                'competition_level': market_features.get('competition_level', 0.5),
                'time_of_day': market_features.get('time_of_day', 12),
                'day_of_week': market_features.get('day_of_week', 1),
                'market_trend': market_features.get('market_trend', 0),
                'liquidity_score': market_features.get('liquidity_score', 0.6),
                'order_book_imbalance': market_features.get('order_book_imbalance', 0.1)
            }
            
            # Add historical features
            if symbol in self.spread_history and len(self.spread_history[symbol]) > 0:
                recent_spreads = [h['spread'] for h in self.spread_history[symbol][-10:]]
                features.update({
                    'avg_spread_10': np.mean(recent_spreads),
                    'std_spread_10': np.std(recent_spreads),
                    'max_spread_10': np.max(recent_spreads),
                    'min_spread_10': np.min(recent_spreads),
                    'spread_trend': self._calculate_spread_trend(recent_spreads)
                })
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features for {symbol}: {str(e)}")
            return {
                'volatility': 0.02,
                'volume_ratio': 1.0,
                'competition_level': 0.5,
                'time_of_day': 12,
                'day_of_week': 1,
                'market_trend': 0,
                'liquidity_score': 0.6,
                'order_book_imbalance': 0.1
            }
    
    def _heuristic_prediction(self, symbol: str, features: Dict[str, float]) -> float:
        """Simple heuristic-based spread prediction"""
        try:
            # Base spread estimate
            base_spread = 0.01  # 1%
            
            # Adjust based on features
            volatility_multiplier = 1 + (features['volatility'] * 10)  # Higher volatility = higher spread
            volume_multiplier = 1 - (features['volume_ratio'] - 1) * 0.2  # Higher volume = lower spread
            competition_multiplier = 1 + (features['competition_level'] * 0.5)  # Higher competition = higher spread
            
            # Time-based adjustments
            time_multiplier = 1.0
            if 8 <= features['time_of_day'] <= 16:  # Market hours
                time_multiplier = 0.8  # Lower spreads during active hours
            elif 22 <= features['time_of_day'] or features['time_of_day'] <= 6:  # Off hours
                time_multiplier = 1.3  # Higher spreads during off hours
            
            predicted_spread = base_spread * volatility_multiplier * volume_multiplier * competition_multiplier * time_multiplier
            
            return max(min(predicted_spread, 0.05), 0.005)  # Cap between 0.5% and 5%
            
        except Exception as e:
            logger.error(f"Error in heuristic prediction for {symbol}: {str(e)}")
            return 0.01  # Default 1%
    
    def _linear_regression_prediction(self, symbol: str, features: Dict[str, float]) -> Tuple[float, float]:
        """Linear regression-based spread prediction"""
        try:
            if symbol not in self.spread_history or len(self.spread_history[symbol]) < 10:
                return self._heuristic_prediction(symbol, features), 0.3
            
            # Prepare training data
            X = []  # Features
            y = []  # Target (spreads)
            
            for record in self.spread_history[symbol]:
                if 'features' in record:
                    feature_vector = [
                        record['features'].get('volatility', 0.02),
                        record['features'].get('volume_ratio', 1.0),
                        record['features'].get('competition_level', 0.5),
                        record['features'].get('time_of_day', 12) / 24.0,  # Normalize to 0-1
                        record['features'].get('liquidity_score', 0.6)
                    ]
                    X.append(feature_vector)
                    y.append(record['spread'])
            
            if len(X) < 5:
                return self._heuristic_prediction(symbol, features), 0.3
            
            # Simple linear regression using normal equation
            X = np.array(X)
            y = np.array(y)
            
            # Add bias term
            X_bias = np.c_[np.ones(X.shape[0]), X]
            
            # Calculate weights using normal equation
            try:
                weights = np.linalg.inv(X_bias.T.dot(X_bias)).dot(X_bias.T).dot(y)
            except np.linalg.LinAlgError:
                # If matrix is singular, use heuristic
                return self._heuristic_prediction(symbol, features), 0.3
            
            # Make prediction
            current_features = [
                features['volatility'],
                features['volume_ratio'],
                features['competition_level'],
                features['time_of_day'] / 24.0,
                features['liquidity_score']
            ]
            current_features = np.array([1] + current_features)  # Add bias
            
            predicted_spread = weights.dot(current_features)
            
            # Calculate confidence based on R-squared
            predictions = X_bias.dot(weights)
            ss_res = np.sum((y - predictions) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            confidence = max(0.1, min(r_squared, 0.9))  # Cap between 0.1 and 0.9
            
            return max(min(predicted_spread, 0.05), 0.005), confidence
            
        except Exception as e:
            logger.error(f"Error in linear regression prediction for {symbol}: {str(e)}")
            return self._heuristic_prediction(symbol, features), 0.3
    
    def _ensemble_prediction(self, symbol: str, features: Dict[str, float]) -> Tuple[float, float]:
        """Ensemble model combining multiple prediction methods"""
        try:
            predictions = []
            confidences = []
            
            # Linear regression prediction
            lr_pred, lr_conf = self._linear_regression_prediction(symbol, features)
            predictions.append(lr_pred)
            confidences.append(lr_conf)
            
            # Moving average prediction
            ma_pred, ma_conf = self._moving_average_prediction(symbol, features)
            predictions.append(ma_pred)
            confidences.append(ma_conf)
            
            # Trend-based prediction
            trend_pred, trend_conf = self._trend_based_prediction(symbol, features)
            predictions.append(trend_pred)
            confidences.append(trend_conf)
            
            # Weighted average of predictions
            total_weight = sum(confidences)
            if total_weight > 0:
                weighted_prediction = sum(p * c for p, c in zip(predictions, confidences)) / total_weight
                avg_confidence = sum(confidences) / len(confidences)
            else:
                weighted_prediction = np.mean(predictions)
                avg_confidence = 0.5
            
            return weighted_prediction, avg_confidence
            
        except Exception as e:
            logger.error(f"Error in ensemble prediction for {symbol}: {str(e)}")
            return self._heuristic_prediction(symbol, features), 0.3
    
    def _moving_average_prediction(self, symbol: str, features: Dict[str, float]) -> Tuple[float, float]:
        """Moving average-based prediction"""
        try:
            if symbol not in self.spread_history or len(self.spread_history[symbol]) < 5:
                return self._heuristic_prediction(symbol, features), 0.3
            
            # Get recent spreads
            recent_spreads = [h['spread'] for h in self.spread_history[symbol][-20:]]
            
            # Calculate different moving averages
            ma_5 = np.mean(recent_spreads[-5:]) if len(recent_spreads) >= 5 else np.mean(recent_spreads)
            ma_10 = np.mean(recent_spreads[-10:]) if len(recent_spreads) >= 10 else np.mean(recent_spreads)
            ma_20 = np.mean(recent_spreads) if len(recent_spreads) >= 20 else np.mean(recent_spreads)
            
            # Weighted average (more weight on recent data)
            prediction = ma_5 * 0.5 + ma_10 * 0.3 + ma_20 * 0.2
            
            # Calculate confidence based on consistency
            spread_std = np.std(recent_spreads)
            spread_mean = np.mean(recent_spreads)
            consistency = 1 - (spread_std / spread_mean) if spread_mean > 0 else 0
            confidence = max(0.1, min(consistency, 0.8))
            
            return prediction, confidence
            
        except Exception as e:
            logger.error(f"Error in moving average prediction for {symbol}: {str(e)}")
            return self._heuristic_prediction(symbol, features), 0.3
    
    def _trend_based_prediction(self, symbol: str, features: Dict[str, float]) -> Tuple[float, float]:
        """Trend-based prediction"""
        try:
            if symbol not in self.spread_history or len(self.spread_history[symbol]) < 10:
                return self._heuristic_prediction(symbol, features), 0.3
            
            # Get recent spreads
            recent_spreads = [h['spread'] for h in self.spread_history[symbol][-20:]]
            
            # Calculate trend
            if len(recent_spreads) >= 5:
                x = np.arange(len(recent_spreads))
                y = np.array(recent_spreads)
                
                # Simple linear trend
                slope = np.polyfit(x, y, 1)[0]
                
                # Predict next value
                last_spread = recent_spreads[-1]
                predicted_spread = last_spread + slope
                
                # Calculate confidence based on trend consistency
                trend_consistency = 1 - abs(slope) * 100  # Lower slope = higher consistency
                confidence = max(0.1, min(trend_consistency, 0.7))
            else:
                predicted_spread = np.mean(recent_spreads)
                confidence = 0.3
            
            return max(min(predicted_spread, 0.05), 0.005), confidence
            
        except Exception as e:
            logger.error(f"Error in trend-based prediction for {symbol}: {str(e)}")
            return self._heuristic_prediction(symbol, features), 0.3
    
    def _calculate_spread_trend(self, spreads: List[float]) -> float:
        """Calculate spread trend"""
        try:
            if len(spreads) < 2:
                return 0.0
            
            # Simple linear trend calculation
            x = np.arange(len(spreads))
            y = np.array(spreads)
            
            slope = np.polyfit(x, y, 1)[0]
            return slope
            
        except Exception as e:
            logger.error(f"Error calculating spread trend: {str(e)}")
            return 0.0
    
    def _store_prediction(self, symbol: str, prediction: MLPrediction):
        """Store prediction for future use"""
        try:
            if symbol not in self.prediction_history:
                self.prediction_history[symbol] = []
            
            self.prediction_history[symbol].append({
                'timestamp': prediction.prediction_time,
                'predicted_spread': prediction.predicted_spread,
                'confidence': prediction.confidence,
                'model_type': prediction.model_type,
                'features': prediction.features
            })
            
            # Keep only recent predictions (last 100)
            if len(self.prediction_history[symbol]) > 100:
                self.prediction_history[symbol] = self.prediction_history[symbol][-100:]
                
        except Exception as e:
            logger.error(f"Error storing prediction for {symbol}: {str(e)}")
    
    def _get_default_prediction(self, symbol: str, market_features: Dict) -> MLPrediction:
        """Get default prediction when calculation fails"""
        return MLPrediction(
            symbol=symbol,
            predicted_spread=0.01,  # Default 1%
            confidence=0.3,
            features={},
            model_type='default',
            prediction_time=market_features.get('timestamp', 0)
        )
    
    def update_spread_history(self, symbol: str, actual_spread: float, features: Dict[str, float]):
        """Update spread history with actual data"""
        try:
            if symbol not in self.spread_history:
                self.spread_history[symbol] = []
            
            self.spread_history[symbol].append({
                'timestamp': time.time(),
                'spread': actual_spread,
                'features': features
            })
            
            # Keep only recent history (last 200 entries)
            if len(self.spread_history[symbol]) > 200:
                self.spread_history[symbol] = self.spread_history[symbol][-200:]
                
        except Exception as e:
            logger.error(f"Error updating spread history for {symbol}: {str(e)}")
    
    def get_model_performance(self, symbol: str) -> Dict:
        """Get model performance metrics"""
        try:
            if symbol not in self.prediction_history or symbol not in self.spread_history:
                return {'error': 'Insufficient data'}
            
            predictions = self.prediction_history[symbol]
            actuals = self.spread_history[symbol]
            
            if len(predictions) < 5 or len(actuals) < 5:
                return {'error': 'Insufficient data'}
            
            # Match predictions with actuals (simplified)
            matched_data = []
            for pred in predictions[-20:]:  # Last 20 predictions
                # Find closest actual spread in time
                closest_actual = min(actuals, key=lambda x: abs(x['timestamp'] - pred['timestamp']))
                if abs(closest_actual['timestamp'] - pred['timestamp']) < 3600:  # Within 1 hour
                    matched_data.append({
                        'predicted': pred['predicted_spread'],
                        'actual': closest_actual['spread']
                    })
            
            if not matched_data:
                return {'error': 'No matched data'}
            
            # Calculate metrics
            errors = [abs(d['predicted'] - d['actual']) for d in matched_data]
            mae = np.mean(errors)
            mse = np.mean([e**2 for e in errors])
            rmse = np.sqrt(mse)
            
            # Calculate accuracy
            accuracy = 1 - (mae / np.mean([d['actual'] for d in matched_data]))
            
            return {
                'mae': mae,
                'mse': mse,
                'rmse': rmse,
                'accuracy': accuracy,
                'sample_size': len(matched_data),
                'avg_confidence': np.mean([p['confidence'] for p in predictions[-20:]])
            }
            
        except Exception as e:
            logger.error(f"Error getting model performance for {symbol}: {str(e)}")
            return {'error': str(e)}
    
    def get_ml_summary(self) -> Dict:
        """Get ML models summary for all symbols"""
        try:
            summary = {}
            
            for symbol in Config.CURRENCY_PAIRS:
                performance = self.get_model_performance(symbol)
                
                if symbol in self.spread_history:
                    history_count = len(self.spread_history[symbol])
                else:
                    history_count = 0
                
                if symbol in self.prediction_history:
                    prediction_count = len(self.prediction_history[symbol])
                else:
                    prediction_count = 0
                
                summary[symbol] = {
                    'history_count': history_count,
                    'prediction_count': prediction_count,
                    'performance': performance
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting ML summary: {str(e)}")
            return {}

