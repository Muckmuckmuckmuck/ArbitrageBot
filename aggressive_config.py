import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging

# Load environment variables
load_dotenv()

class AggressiveConfig:
    """Aggressive configuration with auto-sizing, dynamic spreads, and smart rate limiting"""
    
    # API Configuration
    PIONEX_API_KEY = os.getenv('PIONEX_API_KEY', '')
    PIONEX_SECRET_KEY = os.getenv('PIONEX_SECRET_KEY', '')
    PIONEX_TESTNET = os.getenv('PIONEX_TESTNET', 'true').lower() == 'true'
    
    COINBASE_API_KEY = os.getenv('COINBASE_API_KEY', '')
    COINBASE_SECRET_KEY = os.getenv('COINBASE_SECRET_KEY', '')
    COINBASE_PASSPHRASE = os.getenv('COINBASE_PASSPHRASE', '')
    COINBASE_SANDBOX = os.getenv('COINBASE_SANDBOX', 'true').lower() == 'true'
    
    # Top 10 Best Cryptos (from comprehensive analysis)
    TIER1_ASSETS = [
        'TON/USDT',   # Score: 0.713 - Layer 1 - 1.7% spread, 60% freq
        'SHIB/USDT',  # Score: 0.710 - Meme - 1.2% spread, 50% freq
        'SOL/USDT',   # Score: 0.667 - Layer 1 - 0.8% spread, 45% freq
    ]
    
    TIER2_ASSETS = [
        'AVAX/USDT',  # Score: 0.654 - Layer 1 - 0.9% spread, 40% freq
        'ARB/USDT',   # Score: 0.640 - Layer 2 - 1.0% spread, 35% freq
        'PEPE/USDT',  # Score: 0.633 - Meme - 1.5% spread, 55% freq
        'DOGE/USDT',  # Score: 0.630 - Meme - 0.8% spread, 35% freq
        'ATOM/USDT',  # Score: 0.627 - Layer 1 - 0.9% spread, 35% freq
    ]
    
    TIER3_ASSETS = [
        'XLM/USDT',   # Score: 0.621 - Payment - 0.8% spread, 30% freq
        'UNI/USDT',   # Score: 0.615 - DeFi - 0.9% spread, 40% freq
    ]
    
    CURRENCY_PAIRS = TIER1_ASSETS + TIER2_ASSETS + TIER3_ASSETS
    
    # ==================== AGGRESSIVE POSITION SIZING ====================
    
    # Base position percentages (starting point for auto-sizing)
    BASE_POSITION_PERCENTAGES = {
        # Tier 1: Top Performers - Start aggressive
        'TON/USDT': 0.25,    # 25% base (will auto-scale up to 40%)
        'SHIB/USDT': 0.23,   # 23% base (will auto-scale up to 38%)
        'SOL/USDT': 0.20,    # 20% base (will auto-scale up to 35%)
        
        # Tier 2: Strong Performers - Start medium-aggressive
        'AVAX/USDT': 0.15,   # 15% base (will auto-scale up to 25%)
        'ARB/USDT': 0.12,    # 12% base (will auto-scale up to 22%)
        'PEPE/USDT': 0.12,   # 12% base (will auto-scale up to 22%)
        'DOGE/USDT': 0.10,   # 10% base (will auto-scale up to 18%)
        'ATOM/USDT': 0.12,   # 12% base (will auto-scale up to 22%)
        
        # Tier 3: Good Performers - Start conservative
        'XLM/USDT': 0.10,    # 10% base (will auto-scale up to 18%)
        'UNI/USDT': 0.10,    # 10% base (will auto-scale up to 18%)
    }
    
    # Auto-sizing configuration
    AUTO_SIZING = {
        'enabled': True,
        'lookback_trades': 20,  # Look at last 20 trades
        'min_win_rate': 0.70,   # 70% win rate to increase size
        'scale_up_factor': 1.10,  # Increase by 10% if profitable
        'scale_down_factor': 0.90,  # Decrease by 10% if losing
        'max_position_percent': 0.40,  # Max 40% per trade
        'min_position_percent': 0.05,  # Min 5% per trade
        'scale_interval_trades': 5,  # Adjust every 5 trades
    }
    
    # Dynamic position sizing based on spread
    DYNAMIC_POSITION_SIZING = {
        'enabled': True,
        'spread_multiplier': True,  # Bigger spread = bigger position
        'max_multiplier': 1.5,  # Max 1.5x position on huge spreads
        'formula': 'position_size * min(spread / min_spread, max_multiplier)',
    }
    
    # ==================== AGGRESSIVE RISK MANAGEMENT ====================
    
    RISK_MANAGEMENT = {
        # Aggressive settings
        'max_position_percent': 0.40,      # Max 40% per trade (was 12%)
        'max_concurrent_trades': 15,       # Max 15 concurrent (was 6)
        'max_total_exposure': 0.95,        # Max 95% total exposure (was 50%)
        'reserve_percent': 0.05,           # Keep 5% reserve (was 30%)
        'min_position_percent': 0.05,      # Min 5% per trade
        
        # No daily trade limits - trade as much as possible
        'max_daily_trades': None,          # Unlimited (was 100)
        
        # Stop-loss settings
        'stop_loss_percent': 0.005,        # 0.5% stop loss
        'trailing_stop_enabled': True,     # Enable trailing stops
        'trailing_stop_percent': 0.003,    # 0.3% trailing stop
        
        # Drawdown protection
        'max_daily_drawdown': 0.10,        # 10% max daily loss
        'emergency_stop_drawdown': 0.15,   # 15% emergency stop
        
        # Account minimums
        'min_account_balance_usd': 100,    # Minimum $100 to operate
    }
    
    # ==================== DYNAMIC SPREAD REQUIREMENTS ====================
    
    # Dynamic spread configuration
    DYNAMIC_SPREADS = {
        'enabled': True,
        'adjustment_interval_minutes': 60,  # Adjust every hour
        'lookback_hours': 24,  # Look at last 24 hours
        
        # Spread adjustment rules
        'high_success_rate': 0.80,  # 80%+ success = lower spread requirement
        'low_success_rate': 0.60,   # <60% success = higher spread requirement
        'spread_adjustment_percent': 0.10,  # Adjust by 10%
        
        # Spread bounds
        'min_spread_floor': 0.003,  # Never go below 0.3%
        'max_spread_ceiling': 0.030,  # Never go above 3.0%
    }
    
    # Base spread requirements (will be dynamically adjusted)
    # Min spread MUST be > 0.7% (0.6% fees + 0.1% buffer for slippage)
    CURRENCY_PAIR_SPREADS = {
        'TON/USDT': {
            'min_spread': 0.008,  # 0.8% (covers 0.6% fees + 0.2% profit)
            'safe_spread': 0.017,  # 1.7%
            'max_spread': 0.030,  # 3.0%
            'slippage': 0.00100,
            'transfer_time': 60,
            'frequency': 0.60,
            'category': 'Layer 1',
            'score': 0.713,
        },
        'SHIB/USDT': {
            'min_spread': 0.008,  # 0.8% (covers 0.6% fees + 0.2% profit)
            'safe_spread': 0.012,  # 1.2%
            'max_spread': 0.022,  # 2.2%
            'slippage': 0.00100,
            'transfer_time': 30,
            'frequency': 0.50,
            'category': 'Meme',
            'score': 0.710,
        },
        'SOL/USDT': {
            'min_spread': 0.008,  # 0.8% (covers 0.6% fees + 0.1% slippage + 0.1% profit)
            'safe_spread': 0.008,  # 0.8%
            'max_spread': 0.015,  # 1.5%
            'slippage': 0.00100,
            'transfer_time': 10,
            'frequency': 0.45,
            'category': 'Layer 1',
            'score': 0.667,
        },
        'AVAX/USDT': {
            'min_spread': 0.008,  # 0.8% (covers 0.6% fees + 0.1% slippage + 0.1% profit)
            'safe_spread': 0.009,  # 0.9%
            'max_spread': 0.017,  # 1.7%
            'slippage': 0.00100,
            'transfer_time': 30,
            'frequency': 0.40,
            'category': 'Layer 1',
            'score': 0.654,
        },
        'ARB/USDT': {
            'min_spread': 0.008,  # 0.8% (covers 0.6% fees + 0.1% slippage + 0.1% profit)
            'safe_spread': 0.010,  # 1.0%
            'max_spread': 0.019,  # 1.9%
            'slippage': 0.00100,
            'transfer_time': 60,
            'frequency': 0.35,
            'category': 'Layer 2',
            'score': 0.640,
        },
        'PEPE/USDT': {
            'min_spread': 0.009,  # 0.9% (covers 0.6% fees + 0.1% slippage + 0.2% profit)
            'safe_spread': 0.015,  # 1.5%
            'max_spread': 0.028,  # 2.8%
            'slippage': 0.00100,
            'transfer_time': 30,
            'frequency': 0.55,
            'category': 'Meme',
            'score': 0.633,
        },
        'DOGE/USDT': {
            'min_spread': 0.008,  # 0.8% (covers 0.6% fees + 0.1% slippage + 0.1% profit)
            'safe_spread': 0.008,  # 0.8%
            'max_spread': 0.016,  # 1.6%
            'slippage': 0.00100,
            'transfer_time': 60,
            'frequency': 0.35,
            'category': 'Meme',
            'score': 0.630,
        },
        'ATOM/USDT': {
            'min_spread': 0.008,  # 0.8% (covers 0.6% fees + 0.1% slippage + 0.1% profit)
            'safe_spread': 0.009,  # 0.9%
            'max_spread': 0.017,  # 1.7%
            'slippage': 0.00100,
            'transfer_time': 60,
            'frequency': 0.35,
            'category': 'Layer 1',
            'score': 0.627,
        },
        'XLM/USDT': {
            'min_spread': 0.008,  # 0.8% (covers 0.6% fees + 0.1% slippage + 0.1% profit)
            'safe_spread': 0.008,  # 0.8%
            'max_spread': 0.015,  # 1.5%
            'slippage': 0.00100,
            'transfer_time': 3,
            'frequency': 0.30,
            'category': 'Payment',
            'score': 0.621,
        },
        'UNI/USDT': {
            'min_spread': 0.008,  # 0.8% (covers 0.6% fees + 0.1% slippage + 0.1% profit)
            'safe_spread': 0.009,  # 0.9%
            'max_spread': 0.018,  # 1.8%
            'slippage': 0.00100,
            'transfer_time': 120,
            'frequency': 0.40,
            'category': 'DeFi',
            'score': 0.615,
        },
    }
    
    # ==================== DYNAMIC SLIPPAGE DETECTION ====================
    
    DYNAMIC_SLIPPAGE = {
        'enabled': True,
        'real_time_detection': True,
        
        # Order book analysis
        'order_book_depth_levels': 20,  # Analyze 20 levels
        'min_liquidity_ratio': 5.0,  # 5x position size in order book
        
        # Slippage prediction
        'use_ml_prediction': True,  # Use ML to predict slippage
        'historical_lookback': 100,  # Last 100 trades
        
        # Slippage thresholds
        'max_acceptable_slippage': 0.003,  # 0.3% max
        'warning_slippage': 0.002,  # 0.2% warning
        
        # Dynamic adjustment
        'adjust_position_size': True,  # Reduce size if high slippage
        'slippage_scale_factor': 0.5,  # 50% reduction if slippage high
    }
    
    # Base slippage estimates (will be dynamically adjusted)
    SLIPPAGE_ESTIMATES = {
        'TON/USDT': 0.00100,   # 0.1% base
        'SHIB/USDT': 0.00100,  # 0.1% base
        'SOL/USDT': 0.00050,   # 0.05% base (high liquidity)
        'AVAX/USDT': 0.00080,  # 0.08% base
        'ARB/USDT': 0.00100,   # 0.1% base
        'PEPE/USDT': 0.00150,  # 0.15% base (lower liquidity)
        'DOGE/USDT': 0.00080,  # 0.08% base (high liquidity)
        'ATOM/USDT': 0.00100,  # 0.1% base
        'XLM/USDT': 0.00080,   # 0.08% base
        'UNI/USDT': 0.00100,   # 0.1% base
    }
    
    # ==================== SMART RATE LIMIT MANAGEMENT ====================
    
    # Exchange rate limits
    EXCHANGE_RATE_LIMITS = {
        'pionex': {
            'requests_per_second': 10,  # 10 req/sec
            'requests_per_minute': 600,  # 600 req/min
            'requests_per_hour': 36000,  # 36k req/hour
            'weight_per_request': 1,
            'max_weight_per_minute': 1200,
        },
        'coinbasepro': {
            'requests_per_second': 10,  # 10 req/sec
            'requests_per_minute': 600,  # 600 req/min
            'requests_per_hour': 36000,  # 36k req/hour
            'weight_per_request': 1,
            'max_weight_per_minute': 1200,
        }
    }
    
    # Smart rate limiting
    SMART_RATE_LIMITING = {
        'enabled': True,
        'safety_margin': 0.80,  # Use 80% of limit (20% buffer)
        'adaptive_throttling': True,  # Slow down if approaching limit
        'priority_queue': True,  # Prioritize important requests
        
        # Request batching
        'batch_requests': True,  # Batch multiple requests
        'max_batch_size': 10,  # Max 10 requests per batch
        
        # Caching
        'cache_enabled': True,
        'cache_ttl_seconds': 2,  # Cache for 2 seconds
        
        # Monitoring
        'track_usage': True,
        'alert_threshold': 0.90,  # Alert at 90% usage
    }
    
    # Optimal check intervals (calculated to avoid rate limits)
    CHECK_INTERVALS = {
        'price_check_seconds': 3,  # Check prices every 3 seconds
        'order_book_check_seconds': 5,  # Check order book every 5 seconds
        'balance_check_seconds': 30,  # Check balance every 30 seconds
        'position_check_seconds': 10,  # Check positions every 10 seconds
        
        # Calculated to stay under rate limits:
        # 10 cryptos * 2 exchanges * (1 price + 0.33 order book + 0.1 balance) = ~28 req/sec
        # With batching and caching: ~10 req/sec average
        # Well under 10 req/sec limit
    }
    
    # ==================== EXCHANGE CONFIGURATIONS ====================
    
    EXCHANGE_CONFIGS = {
        'pionex': {
            'apiKey': PIONEX_API_KEY,
            'secret': PIONEX_SECRET_KEY,
            'sandbox': PIONEX_TESTNET,
            'rateLimit': 100,  # ms between requests
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 10000,
            }
        },
        'coinbasepro': {
            'apiKey': COINBASE_API_KEY,
            'secret': COINBASE_SECRET_KEY,
            'password': COINBASE_PASSPHRASE,
            'sandbox': COINBASE_SANDBOX,
            'rateLimit': 100,  # ms between requests
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
            }
        }
    }
    
    # Exchange fees
    EXCHANGE_FEES = {
        'pionex': {
            'trading_fee': 0.001,  # 0.1%
            'withdrawal_fees': {
                'TON': 0.1, 'SHIB': 100000, 'SOL': 0.01, 'AVAX': 0.01,
                'ARB': 0.1, 'PEPE': 100000, 'DOGE': 1.0, 'ATOM': 0.01,
                'XLM': 0.01, 'UNI': 0.1,
            }
        },
        'coinbasepro': {
            'trading_fee': 0.005,  # 0.5%
            'withdrawal_fees': {
                # Coinbase Pro: FREE withdrawals!
                'TON': 0.0, 'SHIB': 0.0, 'SOL': 0.0, 'AVAX': 0.0,
                'ARB': 0.0, 'PEPE': 0.0, 'DOGE': 0.0, 'ATOM': 0.0,
                'XLM': 0.0, 'UNI': 0.0,
            }
        }
    }
    
    # ==================== LOGGING & MONITORING ====================
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'aggressive_arbitrage.log')
    
    # Comprehensive logging
    LOGGING_CONFIG = {
        'log_all_trades': True,
        'log_position_changes': True,
        'log_spread_adjustments': True,
        'log_slippage_detection': True,
        'log_rate_limit_usage': True,
        'log_performance_metrics': True,
        
        # Performance tracking
        'track_per_crypto_performance': True,
        'track_per_hour_performance': True,
        'track_win_rate': True,
        'track_avg_profit': True,
        'track_slippage': True,
    }
    
    # ==================== RAILWAY DEPLOYMENT ====================
    
    PORT = int(os.getenv('PORT', '8000'))
    RAILWAY_ENVIRONMENT = os.getenv('RAILWAY_ENVIRONMENT', 'production')

def setup_logging():
    """Setup comprehensive logging"""
    logging.basicConfig(
        level=getattr(logging, AggressiveConfig.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(AggressiveConfig.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

