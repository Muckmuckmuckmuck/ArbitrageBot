import os
from config import Config

class RailwayConfig:
    """Railway-specific configuration for deployment"""
    
    # Railway environment variables
    RAILWAY_ENVIRONMENT = os.getenv('RAILWAY_ENVIRONMENT', 'development')
    RAILWAY_PROJECT_ID = os.getenv('RAILWAY_PROJECT_ID', '')
    RAILWAY_SERVICE_ID = os.getenv('RAILWAY_SERVICE_ID', '')
    
    # Database configuration for Railway
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trades.db')
    POSTGRES_URL = os.getenv('POSTGRES_URL', '')
    
    # Redis configuration for Railway
    REDIS_URL = os.getenv('REDIS_URL', '')
    
    # API Keys from Railway secrets
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', Config.BINANCE_API_KEY)
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', Config.BINANCE_SECRET_KEY)
    KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY', Config.KRAKEN_API_KEY)
    KRAKEN_SECRET_KEY = os.getenv('KRAKEN_SECRET_KEY', Config.KRAKEN_SECRET_KEY)
    
    # Trading configuration
    MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', Config.MAX_DAILY_TRADES))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', Config.MAX_POSITION_SIZE))
    MIN_SPREAD_PERCENT = float(os.getenv('MIN_SPREAD_PERCENT', Config.MIN_SPREAD_PERCENT))
    
    # Performance configuration
    WEBSOCKET_ENABLED = os.getenv('WEBSOCKET_ENABLED', 'true').lower() == 'true'
    ML_MODELS_ENABLED = os.getenv('ML_MODELS_ENABLED', 'true').lower() == 'true'
    PERFORMANCE_MONITORING = os.getenv('PERFORMANCE_MONITORING', 'true').lower() == 'true'
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')  # json or text
    
    # Health check configuration
    HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', 300))  # seconds
    HEALTH_CHECK_TIMEOUT = int(os.getenv('HEALTH_CHECK_TIMEOUT', 30))  # seconds
    
    # Resource limits
    MAX_MEMORY_MB = int(os.getenv('MAX_MEMORY_MB', 512))
    MAX_CPU_PERCENT = int(os.getenv('MAX_CPU_PERCENT', 80))
    
    @classmethod
    def get_database_config(cls):
        """Get database configuration for Railway"""
        if cls.POSTGRES_URL:
            return {
                'url': cls.POSTGRES_URL,
                'type': 'postgresql',
                'ssl': 'require'
            }
        elif cls.DATABASE_URL.startswith('postgresql'):
            return {
                'url': cls.DATABASE_URL,
                'type': 'postgresql',
                'ssl': 'require'
            }
        else:
            return {
                'url': cls.DATABASE_URL,
                'type': 'sqlite',
                'ssl': False
            }
    
    @classmethod
    def get_redis_config(cls):
        """Get Redis configuration for Railway"""
        if cls.REDIS_URL:
            return {
                'url': cls.REDIS_URL,
                'ssl': True,
                'decode_responses': True
            }
        return None
    
    @classmethod
    def is_production(cls):
        """Check if running in production environment"""
        return cls.RAILWAY_ENVIRONMENT.lower() == 'production'
    
    @classmethod
    def get_logging_config(cls):
        """Get logging configuration for Railway"""
        if cls.LOG_FORMAT.lower() == 'json':
            return {
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {
                    'json': {
                        'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s"}',
                        'datefmt': '%Y-%m-%d %H:%M:%S'
                    }
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'json',
                        'stream': 'ext://sys.stdout'
                    }
                },
                'root': {
                    'level': cls.LOG_LEVEL,
                    'handlers': ['console']
                }
            }
        else:
            return {
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {
                    'standard': {
                        'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                        'datefmt': '%Y-%m-%d %H:%M:%S'
                    }
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'standard',
                        'stream': 'ext://sys.stdout'
                    }
                },
                'root': {
                    'level': cls.LOG_LEVEL,
                    'handlers': ['console']
                }
            }

