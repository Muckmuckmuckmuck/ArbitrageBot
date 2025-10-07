
# Add to percentage_balance_manager.py

class FixedPercentageBalanceManager:
    """Fixed percentage balance manager with balance validation"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.balance_validator = BalanceValidator()
        self.config = Config
        self.current_positions = {}
        self.active_concurrent_trades = 0
    
    async def get_adaptive_position_size(self, symbol: str, spread_percent: float, 
                                      volatility: float) -> float:
        """Calculate adaptive position size with balance validation"""
        try:
            # Get total account value
            total_account_value = await self.get_total_account_value()
            
            if total_account_value < self.config.RISK_MANAGEMENT['min_account_balance_usd']:
                logger.warning(f"Account value ${total_account_value:,.2f} below minimum")
                return 0.0
            
            # Calculate base position size
            asset_allocation_percent = self.config.POSITION_PERCENTAGES.get(symbol, 0.05)
            base_position_size = total_account_value * asset_allocation_percent
            
            # Apply risk limits
            max_position_size = total_account_value * self.config.RISK_MANAGEMENT['max_position_percent']
            min_position_size = total_account_value * self.config.RISK_MANAGEMENT['min_position_percent']
            
            position_size = min(base_position_size, max_position_size)
            position_size = max(position_size, min_position_size)
            
            # Validate against available balances
            validated_size = await self._validate_position_size(symbol, position_size)
            
            return validated_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0.0
    
    async def _validate_position_size(self, symbol: str, position_size: float) -> float:
        """Validate position size against available balances"""
        try:
            # Get exchanges
            exchanges = ['binance', 'okx']
            validated_sizes = []
            
            for exchange_name in exchanges:
                try:
                    # Get current price
                    exchange = self.exchange_manager.get_exchange(exchange_name)
                    ticker = await exchange.get_ticker(symbol)
                    current_price = ticker['last']
                    
                    # Validate USDT balance for buy side
                    buy_validation = await self.balance_validator.validate_balance(
                        exchange_name, 'USDT', position_size * current_price, buffer_percent=0.1
                    )
                    
                    if buy_validation.is_valid:
                        # Calculate max position based on available balance
                        max_position = buy_validation.available_amount / (current_price * 1.1)
                        validated_sizes.append(max_position)
                    else:
                        logger.warning(f"Insufficient USDT balance on {exchange_name}")
                        validated_sizes.append(0.0)
                        
                except Exception as e:
                    logger.error(f"Error validating position size on {exchange_name}: {str(e)}")
                    validated_sizes.append(0.0)
            
            # Return the maximum validated position size
            max_validated = max(validated_sizes) if validated_sizes else 0.0
            
            # Ensure minimum position size
            min_position = self.config.RISK_MANAGEMENT['min_position_percent'] * await self.get_total_account_value()
            if max_validated < min_position:
                return 0.0
            
            return max_validated
            
        except Exception as e:
            logger.error(f"Error validating position size: {str(e)}")
            return 0.0
