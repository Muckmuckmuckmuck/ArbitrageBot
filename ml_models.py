import asyncio
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import logging

logger = logging.getLogger(__name__)

@dataclass
class MLPrediction:
    """Data class for ML predictions"""
    symbol: str
    predicted_spread: float
    confidence: float
    features_used: List[str]
    timestamp: float
    model_type: str

@dataclass
class TrainingData:
    """Data class for training data"""
    symbol: str
    features: Dict[str, float]
    target: float
    timestamp: float

class BasicMLModels:
    """Basic machine learning models for spread prediction and optimization"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.training_data = {}
        self.feature_importance = {}
        self.model_performance = {}
        
        # Model types
        self.model_types = {
            'spread_prediction': RandomForestRegressor(n_estimators=100, random_state=42),
            'volatility_prediction': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'liquidity_prediction': LinearRegression()
        }
        
        # Feature columns
        self.feature_columns = [
            'hour_of_day', 'day_of_week', 'volume_ratio', 'price_volatility',
            'spread_history_avg', 'spread_history_std', 'market_cap_ratio',
            'order_book_depth', 'recent_trades_count', 'exchange_imbalance'
        ]
        
    def prepare_features(self, symbol: str, market_data: Dict, historical_data: List[Dict]) -> Dict[str, float]:
        """Prepare features for ML models"""
        try:
            features = {}
            
            # Time-based features
            current_time = time.time()
            hour = time.localtime(current_time).tm_hour
            day_of_week = time.localtime(current_time).tm_wday
            
            features['hour_of_day'] = hour
            features['day_of_week'] = day_of_week
            
            # Market data features
            features['volume_ratio'] = market_data.get('volume_ratio', 0.0)
            features['price_volatility'] = market_data.get('volatility', 0.0)
            features['order_book_depth'] = market_data.get('order_book_depth', 0.0)
            features['recent_trades_count'] = market_data.get('recent_trades_count', 0)
            features['exchange_imbalance'] = market_data.get('exchange_imbalance', 0.0)
            
            # Historical spread features
            if historical_data:
                spreads = [d.get('spread', 0.0) for d in historical_data[-50:]]  # Last 50 records
                features['spread_history_avg'] = np.mean(spreads) if spreads else 0.0
                features['spread_history_std'] = np.std(spreads) if spreads else 0.0
            else:
                features['spread_history_avg'] = 0.0
                features['spread_history_std'] = 0.0
            
            # Market cap ratio (simplified)
            features['market_cap_ratio'] = market_data.get('market_cap_ratio', 1.0)
            
            return features
            
        except Exception as e:
            logger.error(f"Error preparing features for {symbol}: {str(e)}")
            return {}
    
    def collect_training_data(self, symbol: str, market_data: Dict, actual_spread: float):
        """Collect training data for ML models"""
        try:
            if symbol not in self.training_data:
                self.training_data[symbol] = []
            
            # Prepare features
            features = self.prepare_features(symbol, market_data, self.training_data[symbol])
            
            if not features:
                return
            
            # Create training data point
            training_point = TrainingData(
                symbol=symbol,
                features=features,
                target=actual_spread,
                timestamp=time.time()
            )
            
            self.training_data[symbol].append(training_point)
            
            # Keep only recent data (last 10,000 records)
            if len(self.training_data[symbol]) > 10000:
                self.training_data[symbol] = self.training_data[symbol][-10000:]
            
            logger.debug(f"Collected training data for {symbol}: {actual_spread:.4f}% spread")
            
        except Exception as e:
            logger.error(f"Error collecting training data for {symbol}: {str(e)}")
    
    async def train_models(self, symbol: str, min_samples: int = 100) -> bool:
        """Train ML models for a symbol"""
        try:
            if symbol not in self.training_data:
                logger.warning(f"No training data available for {symbol}")
                return False
            
            data = self.training_data[symbol]
            if len(data) < min_samples:
                logger.warning(f"Insufficient training data for {symbol}: {len(data)} samples")
                return False
            
            # Prepare data
            X = []
            y = []
            
            for point in data:
                features = [point.features.get(col, 0.0) for col in self.feature_columns]
                X.append(features)
                y.append(point.target)
            
            X = np.array(X)
            y = np.array(y)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train models
            trained_models = {}
            trained_scalers = {}
            
            for model_name, model in self.model_types.items():
                try:
                    # Scale features
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)
                    
                    # Train model
                    model.fit(X_train_scaled, y_train)
                    
                    # Evaluate model
                    y_pred = model.predict(X_test_scaled)
                    mse = mean_squared_error(y_test, y_pred)
                    r2 = r2_score(y_test, y_pred)
                    
                    # Store model and scaler
                    trained_models[model_name] = model
                    trained_scalers[model_name] = scaler
                    
                    # Store performance metrics
                    if symbol not in self.model_performance:
                        self.model_performance[symbol] = {}
                    
                    self.model_performance[symbol][model_name] = {
                        'mse': mse,
                        'r2': r2,
                        'samples': len(data),
                        'timestamp': time.time()
                    }
                    
                    logger.info(f"Trained {model_name} for {symbol}: R²={r2:.3f}, MSE={mse:.6f}")
                    
                except Exception as e:
                    logger.error(f"Error training {model_name} for {symbol}: {str(e)}")
                    continue
            
            # Store trained models
            if symbol not in self.models:
                self.models[symbol] = {}
            if symbol not in self.scalers:
                self.scalers[symbol] = {}
            
            self.models[symbol].update(trained_models)
            self.scalers[symbol].update(trained_scalers)
            
            return len(trained_models) > 0
            
        except Exception as e:
            logger.error(f"Error training models for {symbol}: {str(e)}")
            return False
    
    async def predict_spread(self, symbol: str, market_data: Dict) -> Optional[MLPrediction]:
        """Predict spread using ML models"""
        try:
            if symbol not in self.models or 'spread_prediction' not in self.models[symbol]:
                logger.warning(f"No trained model available for {symbol}")
                return None
            
            # Prepare features
            features = self.prepare_features(symbol, market_data, self.training_data.get(symbol, []))
            if not features:
                return None
            
            # Get model and scaler
            model = self.models[symbol]['spread_prediction']
            scaler = self.scalers[symbol]['spread_prediction']
            
            # Prepare feature vector
            feature_vector = np.array([[features.get(col, 0.0) for col in self.feature_columns]])
            
            # Scale features
            feature_vector_scaled = scaler.transform(feature_vector)
            
            # Make prediction
            predicted_spread = model.predict(feature_vector_scaled)[0]
            
            # Calculate confidence (simplified)
            confidence = min(0.9, max(0.1, 1.0 - abs(predicted_spread - 0.01) / 0.01))
            
            prediction = MLPrediction(
                symbol=symbol,
                predicted_spread=predicted_spread,
                confidence=confidence,
                features_used=self.feature_columns.copy(),
                timestamp=time.time(),
                model_type='spread_prediction'
            )
            
            logger.debug(f"Predicted spread for {symbol}: {predicted_spread:.4f}% (confidence: {confidence:.3f})")
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting spread for {symbol}: {str(e)}")
            return None
    
    async def predict_volatility(self, symbol: str, market_data: Dict) -> Optional[float]:
        """Predict volatility using ML models"""
        try:
            if symbol not in self.models or 'volatility_prediction' not in self.models[symbol]:
                return None
            
            # Prepare features
            features = self.prepare_features(symbol, market_data, self.training_data.get(symbol, []))
            if not features:
                return None
            
            # Get model and scaler
            model = self.models[symbol]['volatility_prediction']
            scaler = self.scalers[symbol]['volatility_prediction']
            
            # Prepare feature vector
            feature_vector = np.array([[features.get(col, 0.0) for col in self.feature_columns]])
            
            # Scale features
            feature_vector_scaled = scaler.transform(feature_vector)
            
            # Make prediction
            predicted_volatility = model.predict(feature_vector_scaled)[0]
            
            return max(0.0, predicted_volatility)
            
        except Exception as e:
            logger.error(f"Error predicting volatility for {symbol}: {str(e)}")
            return None
    
    async def predict_liquidity(self, symbol: str, market_data: Dict) -> Optional[float]:
        """Predict liquidity using ML models"""
        try:
            if symbol not in self.models or 'liquidity_prediction' not in self.models[symbol]:
                return None
            
            # Prepare features
            features = self.prepare_features(symbol, market_data, self.training_data.get(symbol, []))
            if not features:
                return None
            
            # Get model and scaler
            model = self.models[symbol]['liquidity_prediction']
            scaler = self.scalers[symbol]['liquidity_prediction']
            
            # Prepare feature vector
            feature_vector = np.array([[features.get(col, 0.0) for col in self.feature_columns]])
            
            # Scale features
            feature_vector_scaled = scaler.transform(feature_vector)
            
            # Make prediction
            predicted_liquidity = model.predict(feature_vector_scaled)[0]
            
            return max(0.0, min(1.0, predicted_liquidity))
            
        except Exception as e:
            logger.error(f"Error predicting liquidity for {symbol}: {str(e)}")
            return None
    
    def get_feature_importance(self, symbol: str, model_type: str = 'spread_prediction') -> Dict[str, float]:
        """Get feature importance for a model"""
        try:
            if (symbol not in self.models or 
                model_type not in self.models[symbol] or 
                not hasattr(self.models[symbol][model_type], 'feature_importances_')):
                return {}
            
            model = self.models[symbol][model_type]
            importance = model.feature_importances_
            
            feature_importance = {}
            for i, col in enumerate(self.feature_columns):
                if i < len(importance):
                    feature_importance[col] = importance[i]
            
            # Sort by importance
            sorted_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
            
            return sorted_importance
            
        except Exception as e:
            logger.error(f"Error getting feature importance for {symbol}: {str(e)}")
            return {}
    
    def get_model_performance(self, symbol: str) -> Dict:
        """Get model performance metrics"""
        try:
            if symbol not in self.model_performance:
                return {}
            
            return self.model_performance[symbol].copy()
            
        except Exception as e:
            logger.error(f"Error getting model performance for {symbol}: {str(e)}")
            return {}
    
    def save_models(self, symbol: str, filepath: str):
        """Save trained models to disk"""
        try:
            if symbol not in self.models:
                logger.warning(f"No models to save for {symbol}")
                return
            
            model_data = {
                'models': self.models[symbol],
                'scalers': self.scalers[symbol],
                'feature_columns': self.feature_columns,
                'timestamp': time.time()
            }
            
            joblib.dump(model_data, filepath)
            logger.info(f"Saved models for {symbol} to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving models for {symbol}: {str(e)}")
    
    def load_models(self, symbol: str, filepath: str) -> bool:
        """Load trained models from disk"""
        try:
            model_data = joblib.load(filepath)
            
            if symbol not in self.models:
                self.models[symbol] = {}
            if symbol not in self.scalers:
                self.scalers[symbol] = {}
            
            self.models[symbol].update(model_data['models'])
            self.scalers[symbol].update(model_data['scalers'])
            
            logger.info(f"Loaded models for {symbol} from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading models for {symbol}: {str(e)}")
            return False
    
    def get_training_data_summary(self) -> Dict:
        """Get summary of training data"""
        try:
            summary = {}
            
            for symbol, data in self.training_data.items():
                if data:
                    spreads = [point.target for point in data]
                    summary[symbol] = {
                        'samples': len(data),
                        'avg_spread': np.mean(spreads),
                        'std_spread': np.std(spreads),
                        'min_spread': np.min(spreads),
                        'max_spread': np.max(spreads),
                        'latest_timestamp': max(point.timestamp for point in data)
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting training data summary: {str(e)}")
            return {}
    
    async def retrain_models_periodically(self, symbols: List[str], interval_hours: int = 24):
        """Retrain models periodically"""
        try:
            while True:
                logger.info(f"Starting periodic model retraining for {len(symbols)} symbols")
                
                for symbol in symbols:
                    try:
                        success = await self.train_models(symbol)
                        if success:
                            logger.info(f"Successfully retrained models for {symbol}")
                        else:
                            logger.warning(f"Failed to retrain models for {symbol}")
                    except Exception as e:
                        logger.error(f"Error retraining models for {symbol}: {str(e)}")
                
                logger.info(f"Completed periodic model retraining. Next retraining in {interval_hours} hours")
                await asyncio.sleep(interval_hours * 3600)
                
        except Exception as e:
            logger.error(f"Error in periodic model retraining: {str(e)}")
    
    def cleanup_old_data(self, max_age_hours: int = 168):  # 1 week
        """Clean up old training data"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)
            
            for symbol in self.training_data:
                original_count = len(self.training_data[symbol])
                self.training_data[symbol] = [
                    point for point in self.training_data[symbol]
                    if point.timestamp >= cutoff_time
                ]
                
                removed_count = original_count - len(self.training_data[symbol])
                if removed_count > 0:
                    logger.info(f"Cleaned up {removed_count} old training records for {symbol}")
            
        except Exception as e:
            logger.error(f"Error cleaning up old training data: {str(e)}")

