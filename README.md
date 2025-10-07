# Algorithmic Trading Bot - Binance & Kraken Arbitrage

A sophisticated algorithmic trading bot that performs arbitrage between Binance and Kraken exchanges, optimized for Railway deployment.

## Features

### Core Trading Features
- **Cross-Exchange Arbitrage**: Buy low on one exchange, sell high on another
- **32 Optimized Cryptocurrencies**: Carefully selected based on transfer speed, liquidity, and spread quality
- **Hybrid Strategy**: Transfer-first for fast networks, simultaneous for slower ones
- **Real-time Price Monitoring**: WebSocket integration for instant price updates
- **Smart Position Sizing**: Kelly criterion and risk-adjusted position sizing

### Advanced Features
- **Machine Learning Models**: Spread prediction and market analysis
- **Slippage Protection**: Real-time slippage analysis and protection
- **Volume Analysis**: Liquidity scoring and market depth analysis
- **Competition Detection**: Monitor other arbitrage bots
- **Dynamic Spread Management**: Adaptive spread thresholds
- **Performance Optimization**: Latency reduction and throughput optimization

### Risk Management
- **Advanced Risk Manager**: Portfolio-level risk controls
- **Circuit Breakers**: Automatic failure detection and recovery
- **Emergency Stop**: Automatic halt on critical conditions
- **Position Limits**: Asset-specific trade size limits
- **Correlation Analysis**: Diversification and risk assessment

### Monitoring & Analytics
- **Real-time Dashboard**: Live trading statistics
- **Performance Metrics**: Latency, success rates, profit tracking
- **Database Integration**: SQLite/PostgreSQL for historical data
- **Enhanced Reporting**: Comprehensive analytics and insights
- **Health Monitoring**: System health checks and alerts

## Supported Cryptocurrencies

### Tier 1: Ultra-Fast Transfer (Instant - 2 minutes)
- XRP/USDT, XLM/USDT, SOL/USDT, EOS/USDT, TRX/USDT
- TON/USDT, BNB/USDT, MATIC/USDT, AVAX/USDT, DOT/USDT
- USDC/USDT, USDT/USDC, DAI/USDT, BUSD/USDT
- UNI/USDT, LINK/USDT, ADA/USDT

### Tier 2: Fast Transfer (2-5 minutes)
- XTZ/USDT, MKR/USDT, FIL/USDT, ATOM/USDT
- AAVE/USDT, COMP/USDT, CRV/USDT, SNX/USDT
- YFI/USDT, 1INCH/USDT

### Tier 3: Acceptable Transfer (5-10 minutes)
- LTC/USDT, DOGE/USDT, VET/USDT, BCH/USDT, XMR/USDT

## Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd algotrading-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

### Railway Deployment

1. **Connect to Railway**
   ```bash
   railway login
   railway link
   ```

2. **Set environment variables**
   ```bash
   railway variables set BINANCE_API_KEY=your-api-key
   railway variables set BINANCE_SECRET_KEY=your-secret-key
   railway variables set KRAKEN_API_KEY=your-api-key
   railway variables set KRAKEN_SECRET_KEY=your-secret-key
   ```

3. **Deploy**
   ```bash
   railway up
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BINANCE_API_KEY` | Binance API key | Required |
| `BINANCE_SECRET_KEY` | Binance secret key | Required |
| `KRAKEN_API_KEY` | Kraken API key | Required |
| `KRAKEN_SECRET_KEY` | Kraken secret key | Required |
| `MAX_DAILY_TRADES` | Maximum trades per day | 50 |
| `MAX_POSITION_SIZE` | Maximum position size (USD) | 10000 |
| `MIN_SPREAD_PERCENT` | Minimum spread for trading | 0.8 |
| `WEBSOCKET_ENABLED` | Enable WebSocket feeds | true |
| `ML_MODELS_ENABLED` | Enable ML models | true |
| `PERFORMANCE_MONITORING` | Enable performance monitoring | true |

### Trading Parameters

- **Minimum Spread**: 0.8% (configurable per asset)
- **Position Limits**: Asset-specific based on liquidity
- **Transfer Strategies**: Automatic selection based on network speed
- **Risk Limits**: Portfolio-level exposure controls

## Architecture

### Core Components

1. **Exchange Manager**: Handles API connections and rate limiting
2. **Price Monitor**: Real-time price tracking and WebSocket management
3. **Arbitrage Engine**: Opportunity detection and trade execution
4. **Transfer Manager**: Cross-exchange cryptocurrency transfers
5. **Risk Manager**: Position and portfolio risk controls

### Advanced Components

1. **WebSocket Manager**: Real-time price feeds and market data
2. **Slippage Protection**: Order book analysis and slippage prevention
3. **Advanced Risk Manager**: Portfolio-level risk assessment
4. **Performance Optimizer**: Latency reduction and throughput optimization
5. **ML Models**: Spread prediction and market analysis
6. **Database Manager**: Historical data storage and analytics

### Data Flow

```
WebSocket Feeds → Price Monitor → Arbitrage Engine → Risk Manager → Trade Execution
                     ↓
              Database Manager ← Performance Optimizer ← ML Models
```

## Monitoring

### Real-time Metrics
- Trade execution times
- Profit/loss tracking
- Slippage analysis
- Risk metrics
- Performance statistics

### Health Checks
- Exchange connectivity
- API rate limits
- Database status
- Memory usage
- Error rates

### Alerts
- Emergency stop conditions
- High slippage detection
- Risk limit breaches
- Performance degradation
- System errors

## Risk Management

### Position Controls
- Maximum position size per asset
- Portfolio exposure limits
- Correlation analysis
- Volatility assessment

### Safety Features
- Circuit breakers for repeated failures
- Emergency stop on critical conditions
- Automatic position reduction on high risk
- Diversification requirements

### Monitoring
- Real-time risk scoring
- Portfolio-level risk assessment
- Historical risk analysis
- Performance impact tracking

## Performance Optimization

### Latency Reduction
- WebSocket feeds instead of REST API
- Connection pooling
- Parallel request execution
- Caching strategies

### Throughput Optimization
- Request batching
- Order optimization
- Transfer queuing
- Resource management

### Monitoring
- Performance benchmarking
- Latency profiling
- Resource usage tracking
- Optimization recommendations

## Database Schema

### Tables
- **trades**: Trade execution records
- **market_data**: Price and volume data
- **performance_metrics**: Performance statistics
- **risk_metrics**: Risk assessment data
- **ml_predictions**: ML model predictions

### Analytics
- Trade performance analysis
- Market trend identification
- Risk pattern detection
- Optimization insights

## Troubleshooting

### Common Issues

1. **API Rate Limits**
   - Check rate limit configuration
   - Monitor API usage
   - Implement backoff strategies

2. **High Slippage**
   - Reduce position sizes
   - Check market liquidity
   - Adjust spread thresholds

3. **Transfer Failures**
   - Verify network status
   - Check minimum transfer amounts
   - Monitor transfer fees

4. **Performance Issues**
   - Check system resources
   - Monitor latency metrics
   - Review optimization settings

### Logs

The bot provides comprehensive logging:
- Trade execution details
- Error handling and recovery
- Performance metrics
- Risk assessments
- System health status

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves significant risk. Use at your own risk and never trade with money you cannot afford to lose.

## Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the logs for error details

## Roadmap

### Planned Features
- Additional exchange support
- Advanced ML models
- Portfolio optimization
- Social sentiment analysis
- Automated strategy backtesting

### Performance Improvements
- Microsecond latency optimization
- Advanced caching strategies
- Distributed execution
- Real-time risk adjustment