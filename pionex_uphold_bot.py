#!/usr/bin/env python3
"""
Pionex.US and Uphold Arbitrage Trading Bot
Automated arbitrage trading between Pionex.US and Uphold exchanges
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from pionex_uphold_config import PionexUpholdConfig, setup_logging
from pionex_uphold_exchanges import PionexUpholdExchangeManager
from balance_validator import BalanceValidator
from fixed_percentage_balance_manager import FixedPercentageBalanceManager
from comprehensive_error_handler import ComprehensiveErrorHandler, ErrorContext
from rate_limit_manager import RateLimitManager

logger = setup_logging()

@dataclass
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    potential_profit_usd: float
    trade_amount_usd: float
    timestamp: float

class PionexUpholdArbitrageBot:
    """
    Main arbitrage trading bot for Pionex.US and Uphold
    """
    
    def __init__(self):
        self.config = PionexUpholdConfig
        self.exchange_manager = PionexUpholdExchangeManager()
        self.balance_validator = BalanceValidator(self.exchange_manager)
        self.balance_manager = FixedPercentageBalanceManager(self.exchange_manager, self.balance_validator)
        self.error_handler = ComprehensiveErrorHandler()
        self.rate_limit_manager = RateLimitManager()
        
        self.running = False
        self.total_trades = 0
        self.total_profit = 0.0
        self.start_time = None
        
    async def start(self):
        """Start the trading bot"""
        logger.info("=" * 80)
        logger.info("PIONEX.US + UPHOLD ARBITRAGE BOT STARTING")
        logger.info("=" * 80)
        
        self.running = True
        self.start_time = time.time()
        
        try:
            # Initialize balances
            await self._initialize_balances()
            
            # Start main trading loop
            await self._trading_loop()
            
        except Exception as e:
            logger.critical(f"Fatal error in main bot: {str(e)}")
            await self.error_handler.trigger_emergency_stop(f"Fatal error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping arbitrage bot...")
        self.running = False
        
        # Close all exchange connections
        self.exchange_manager.close_all()
        
        # Print final statistics
        await self._print_final_stats()
        
        logger.info("Bot stopped successfully")
    
    async def _initialize_balances(self):
        """Initialize and validate account balances"""
        logger.info("Initializing account balances...")
        
        try:
            # Fetch balances from both exchanges
            pionex_balance = await self.exchange_manager.fetch_balance('pionex')
            logger.info(f"Pionex.US balance: {pionex_balance['total']}")
            
            # Note: Uphold might not be initialized yet (custom implementation needed)
            # uphold_balance = await self.exchange_manager.fetch_balance('uphold')
            # logger.info(f"Uphold balance: {uphold_balance['total']}")
            
            # Calculate total account value
            total_value = await self.balance_manager.get_total_account_value()
            logger.info(f"Total account value: ${total_value:,.2f}")
            
            # Validate minimum balance
            min_balance = self.config.RISK_MANAGEMENT['min_account_balance_usd']
            if total_value < min_balance:
                raise ValueError(f"Account balance ${total_value:,.2f} is below minimum ${min_balance:,.2f}")
            
            logger.info("✅ Balance initialization successful")
            
        except Exception as e:
            logger.error(f"Error initializing balances: {str(e)}")
            raise
    
    async def _trading_loop(self):
        """Main trading loop"""
        logger.info("Starting main trading loop...")
        
        while self.running and not self.error_handler.is_emergency_stop_active():
            try:
                # Check if we've hit daily trade limit
                if self.total_trades >= self.config.MAX_DAILY_TRADES:
                    logger.info(f"Daily trade limit reached ({self.config.MAX_DAILY_TRADES})")
                    await asyncio.sleep(60)
                    continue
                
                # Scan for arbitrage opportunities
                opportunities = await self._scan_opportunities()
                
                if not opportunities:
                    logger.debug("No arbitrage opportunities found")
                    await asyncio.sleep(5)  # Wait 5 seconds before next scan
                    continue
                
                # Process opportunities
                for opportunity in opportunities:
                    if not self.running or self.error_handler.is_emergency_stop_active():
                        break
                    
                    await self._execute_arbitrage(opportunity)
                
                # Brief pause between scans
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {str(e)}")
                await self.error_handler.handle_error(
                    e,
                    ErrorContext(operation="trading_loop", details=str(e))
                )
                await asyncio.sleep(5)
    
    async def _scan_opportunities(self) -> List[ArbitrageOpportunity]:
        """Scan for arbitrage opportunities"""
        opportunities = []
        
        for symbol in self.config.CURRENCY_PAIRS:
            try:
                # Fetch prices from both exchanges
                pionex_ticker = await self.exchange_manager.fetch_ticker('pionex', symbol)
                # uphold_ticker = await self.exchange_manager.fetch_ticker('uphold', symbol)
                
                # For now, since Uphold might not be initialized, we'll skip cross-exchange
                # In a real implementation, you'd fetch from both exchanges
                
                # Calculate spread
                # For demonstration, we'll just check Pionex
                pionex_bid = pionex_ticker['bid']
                pionex_ask = pionex_ticker['ask']
                
                # Note: You would compare Pionex vs Uphold prices here
                # spread_percent = (sell_price - buy_price) / buy_price
                
                # For now, skip to next symbol
                continue
                
            except Exception as e:
                logger.debug(f"Error scanning {symbol}: {str(e)}")
                continue
        
        return opportunities
    
    async def _execute_arbitrage(self, opportunity: ArbitrageOpportunity):
        """Execute an arbitrage trade"""
        logger.info(f"Executing arbitrage: {opportunity.symbol}")
        logger.info(f"  Buy on {opportunity.buy_exchange} @ ${opportunity.buy_price:,.4f}")
        logger.info(f"  Sell on {opportunity.sell_exchange} @ ${opportunity.sell_price:,.4f}")
        logger.info(f"  Spread: {opportunity.spread_percent:.2f}%")
        logger.info(f"  Expected profit: ${opportunity.potential_profit_usd:,.2f}")
        
        try:
            # 1. Validate balances
            balance_checks = await self.balance_validator.validate_trade_balance(
                opportunity.buy_exchange,
                opportunity.sell_exchange,
                opportunity.symbol,
                opportunity.trade_amount_usd,
                opportunity.buy_price,
                opportunity.sell_price
            )
            
            if not all(res.is_valid for res in balance_checks.values()):
                logger.warning(f"Insufficient balance for trade: {balance_checks}")
                return
            
            # 2. Check rate limits
            can_trade = await self.rate_limit_manager.can_execute_trade(
                opportunity.buy_exchange,
                opportunity.sell_exchange
            )
            
            if not can_trade:
                logger.warning("Rate limit would be exceeded, skipping trade")
                return
            
            # 3. Update open positions
            await self.balance_manager.update_open_positions(
                opportunity.symbol,
                opportunity.trade_amount_usd,
                True
            )
            
            # 4. Execute buy order
            base_currency = opportunity.symbol.split('/')[0]
            buy_amount = opportunity.trade_amount_usd / opportunity.buy_price
            
            buy_order = await self.exchange_manager.create_order(
                opportunity.buy_exchange,
                opportunity.symbol,
                'market',
                'buy',
                buy_amount
            )
            
            # 5. Execute sell order
            sell_order = await self.exchange_manager.create_order(
                opportunity.sell_exchange,
                opportunity.symbol,
                'market',
                'sell',
                buy_amount
            )
            
            # 6. Update statistics
            self.total_trades += 1
            self.total_profit += opportunity.potential_profit_usd
            
            # 7. Close position
            await self.balance_manager.update_open_positions(
                opportunity.symbol,
                opportunity.trade_amount_usd,
                False
            )
            
            logger.info(f"✅ Arbitrage executed successfully!")
            logger.info(f"   Total trades: {self.total_trades}")
            logger.info(f"   Total profit: ${self.total_profit:,.2f}")
            
        except Exception as e:
            logger.error(f"Error executing arbitrage: {str(e)}")
            await self.error_handler.handle_error(
                e,
                ErrorContext(
                    exchange=opportunity.buy_exchange,
                    symbol=opportunity.symbol,
                    operation="execute_arbitrage",
                    details=str(e)
                )
            )
    
    async def _print_final_stats(self):
        """Print final statistics"""
        runtime = time.time() - self.start_time if self.start_time else 0
        runtime_hours = runtime / 3600
        
        logger.info("=" * 80)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Runtime: {runtime_hours:.2f} hours")
        logger.info(f"Total trades: {self.total_trades}")
        logger.info(f"Total profit: ${self.total_profit:,.2f}")
        if runtime_hours > 0:
            logger.info(f"Profit per hour: ${self.total_profit / runtime_hours:,.2f}")
        if self.total_trades > 0:
            logger.info(f"Average profit per trade: ${self.total_profit / self.total_trades:,.2f}")
        logger.info("=" * 80)

async def main():
    """Main entry point"""
    logger.info("Initializing Pionex.US + Uphold Arbitrage Bot...")
    
    bot = PionexUpholdArbitrageBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
        await bot.stop()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())

