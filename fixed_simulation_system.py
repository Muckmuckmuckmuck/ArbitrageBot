#!/usr/bin/env python3
"""
Fixed Simulation System for High-Frequency Arbitrage Bot
Addresses critical balance management issues found in testing
"""

import asyncio
import time
import random
import json
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import math

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FixedSimulatedPrice:
    """Fixed simulated price data"""
    symbol: str
    exchange: str
    price: float
    volume: float
    timestamp: float
    spread: float = 0.0

@dataclass
class FixedSimulatedTrade:
    """Fixed simulated trade execution"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    amount: float
    profit_expected: float
    profit_actual: float
    fees_paid: float
    slippage: float
    execution_time: float
    status: str
    timestamp: float
    trade_id: str

@dataclass
class FixedSimulationResults:
    """Fixed simulation test results"""
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_profit: float
    total_fees: float
    total_slippage: float
    success_rate: float
    avg_profit_per_trade: float
    max_drawdown: float
    sharpe_ratio: float
    errors_found: List[str]
    warnings_found: List[str]
    performance_issues: List[str]
    balance_issues_fixed: List[str]

class FixedSimulatedExchange:
    """Fixed simulated exchange with proper balance management"""
    
    def __init__(self, name: str, base_fee: float = 0.001, initial_balance: float = 10000.0):
        self.name = name
        self.base_fee = base_fee
        self.balance = {'USDT': initial_balance}  # Starting balance
        self.crypto_balances = {}  # Track crypto balances
        self.orders = []
        self.rate_limit_usage = {'orders': 0, 'requests': 0}
        self.rate_limits = {'orders_per_minute': 1200, 'requests_per_minute': 1200}
        self.last_reset = time.time()
        self.balance_lock = asyncio.Lock()  # Add balance lock for thread safety
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Get simulated ticker data"""
        # Simulate realistic price movements
        base_price = 1.0 if 'USDT' in symbol else random.uniform(0.1, 100.0)
        volatility = random.uniform(0.001, 0.01)  # 0.1% to 1% volatility
        price_change = random.gauss(0, volatility)
        current_price = base_price * (1 + price_change)
        
        return {
            'last': current_price,
            'bid': current_price * 0.999,
            'ask': current_price * 1.001,
            'volume': random.uniform(1000, 10000)
        }
    
    async def get_balance(self) -> Dict[str, float]:
        """Get simulated balance"""
        async with self.balance_lock:
            return self.balance.copy()
    
    async def get_crypto_balance(self, symbol: str) -> float:
        """Get crypto balance for a symbol"""
        async with self.balance_lock:
            return self.crypto_balances.get(symbol, 0.0)
    
    async def create_order(self, symbol: str, type: str, side: str, amount: float, price: float = None) -> Dict[str, Any]:
        """Simulate order creation with proper balance management"""
        async with self.balance_lock:
            # Check rate limits
            if self.rate_limit_usage['orders'] >= self.rate_limits['orders_per_minute']:
                raise Exception(f"Rate limit exceeded on {self.name}")
            
            # Calculate fees
            fee = amount * self.base_fee
            
            # Simulate slippage
            slippage = random.uniform(0.0001, 0.001)  # 0.01% to 0.1% slippage
            if side == 'buy':
                actual_price = price * (1 + slippage)
            else:
                actual_price = price * (1 - slippage)
            
            # Calculate required balance
            if side == 'buy':
                required_usdt = amount * actual_price + fee
                if self.balance['USDT'] < required_usdt:
                    raise Exception(f"Insufficient USDT balance. Required: {required_usdt:.2f}, Available: {self.balance['USDT']:.2f}")
                
                # Execute buy order
                self.balance['USDT'] -= required_usdt
                if symbol not in self.crypto_balances:
                    self.crypto_balances[symbol] = 0
                self.crypto_balances[symbol] += amount
                
            else:  # sell
                if self.crypto_balances.get(symbol, 0) < amount:
                    raise Exception(f"Insufficient {symbol} balance. Required: {amount:.2f}, Available: {self.crypto_balances.get(symbol, 0):.2f}")
                
                # Execute sell order
                self.crypto_balances[symbol] -= amount
                self.balance['USDT'] += amount * actual_price - fee
            
            # Update rate limit usage
            self.rate_limit_usage['orders'] += 1
            
            return {
                'id': f"{self.name}_{int(time.time() * 1000)}",
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': actual_price,
                'fee': fee,
                'status': 'filled',
                'timestamp': time.time()
            }
    
    def reset_rate_limits(self):
        """Reset rate limits"""
        current_time = time.time()
        if current_time - self.last_reset >= 60:  # 1 minute
            self.rate_limit_usage = {'orders': 0, 'requests': 0}
            self.last_reset = current_time
    
    async def get_total_balance_usd(self) -> float:
        """Get total balance in USD"""
        async with self.balance_lock:
            total_usd = self.balance['USDT']
            for symbol, amount in self.crypto_balances.items():
                if amount > 0:
                    try:
                        ticker = await self.get_ticker(f"{symbol}/USDT")
                        total_usd += amount * ticker['last']
                    except:
                        pass  # Ignore if price unavailable
            return total_usd

class FixedSimulatedPriceMonitor:
    """Fixed simulated price monitor"""
    
    def __init__(self):
        self.prices = {}
        self.running = False
    
    async def start_monitoring(self, symbols: List[str]):
        """Start price monitoring"""
        self.running = True
        logger.info(f"Started monitoring {len(symbols)} symbols")
    
    async def stop_monitoring(self):
        """Stop price monitoring"""
        self.running = False
        logger.info("Stopped price monitoring")
    
    def get_price_spread(self, symbol: str) -> Dict[str, Dict]:
        """Get simulated price spreads"""
        # Simulate price differences between exchanges
        base_price = random.uniform(1.0, 100.0)
        spread_percent = random.uniform(0.005, 0.03)  # 0.5% to 3% spread
        
        binance_price = base_price
        okx_price = base_price * (1 + spread_percent)
        
        # Randomly assign which exchange has higher price
        if random.random() > 0.5:
            buy_price, sell_price = binance_price, okx_price
            buy_exchange, sell_exchange = 'binance', 'okx'
        else:
            buy_price, sell_price = okx_price, binance_price
            buy_exchange, sell_exchange = 'okx', 'binance'
        
        return {
            'binance_okx': {
                'lower_price': buy_price,
                'higher_price': sell_price,
                'lower_price_exchange': buy_exchange,
                'higher_price_exchange': sell_exchange,
                'spread_percent': (sell_price - buy_price) / buy_price,
                'timestamp': time.time()
            }
        }

class FixedSimulationTester:
    """Fixed comprehensive simulation tester"""
    
    def __init__(self):
        self.config = self._load_test_config()
        self.exchanges = {
            'binance': FixedSimulatedExchange('binance', 0.0017, 10000.0),
            'okx': FixedSimulatedExchange('okx', 0.0015, 10000.0)
        }
        self.price_monitor = FixedSimulatedPriceMonitor()
        self.trades = []
        self.errors = []
        self.warnings = []
        self.performance_issues = []
        self.balance_issues_fixed = []
        
    def _load_test_config(self) -> Dict[str, Any]:
        """Load test configuration"""
        return {
            'currency_pairs': [
                'TON/USDT', 'ALGO/USDT', 'VET/USDT', 'XLM/USDT',
                'TRX/USDT', 'FTM/USDT', 'MATIC/USDT', 'SOL/USDT',
                'BCH/USDT', 'XRP/USDT', 'DASH/USDT', 'LTC/USDT',
                'HBAR/USDT', 'ICP/USDT', 'LINK/USDT', 'ATOM/USDT'
            ],
            'spread_requirements': {
                'TON/USDT': 0.008, 'ALGO/USDT': 0.006, 'VET/USDT': 0.007, 'XLM/USDT': 0.006,
                'TRX/USDT': 0.006, 'FTM/USDT': 0.007, 'MATIC/USDT': 0.005, 'SOL/USDT': 0.004,
                'BCH/USDT': 0.004, 'XRP/USDT': 0.003, 'DASH/USDT': 0.005, 'LTC/USDT': 0.004,
                'HBAR/USDT': 0.005, 'ICP/USDT': 0.004, 'LINK/USDT': 0.004, 'ATOM/USDT': 0.004
            },
            'position_percentages': {
                'TON/USDT': 0.08, 'ALGO/USDT': 0.08, 'VET/USDT': 0.06, 'XLM/USDT': 0.08,
                'TRX/USDT': 0.06, 'FTM/USDT': 0.05, 'MATIC/USDT': 0.06, 'SOL/USDT': 0.07,
                'BCH/USDT': 0.05, 'XRP/USDT': 0.06, 'DASH/USDT': 0.04, 'LTC/USDT': 0.05,
                'HBAR/USDT': 0.04, 'ICP/USDT': 0.03, 'LINK/USDT': 0.05, 'ATOM/USDT': 0.04
            },
            'max_concurrent_trades': 8,
            'max_total_exposure': 0.60,
            'reserve_percent': 0.20,
            'test_duration_minutes': 5,  # Reduced for testing
            'opportunities_per_minute': 5
        }
    
    async def run_fixed_simulation(self) -> FixedSimulationResults:
        """Run fixed simulation test"""
        logger.info("Starting fixed simulation test...")
        
        start_time = time.time()
        end_time = start_time + (self.config['test_duration_minutes'] * 60)
        
        # Start price monitoring
        await self.price_monitor.start_monitoring(self.config['currency_pairs'])
        
        # Run simulation
        while time.time() < end_time:
            try:
                await self._simulate_trading_cycle()
                await asyncio.sleep(2)  # 2 seconds between cycles
            except Exception as e:
                self.errors.append(f"Trading cycle error: {str(e)}")
                logger.error(f"Trading cycle error: {str(e)}")
        
        # Stop monitoring
        await self.price_monitor.stop_monitoring()
        
        # Analyze results
        results = self._analyze_simulation_results()
        
        logger.info("Fixed simulation test completed")
        return results
    
    async def _simulate_trading_cycle(self):
        """Simulate one trading cycle with fixed balance management"""
        try:
            # Generate opportunities
            opportunities = await self._generate_opportunities()
            
            # Process opportunities
            for opportunity in opportunities:
                if await self._can_execute_trade():
                    await self._execute_fixed_trade(opportunity)
            
            # Reset rate limits
            for exchange in self.exchanges.values():
                exchange.reset_rate_limits()
            
        except Exception as e:
            self.errors.append(f"Trading cycle error: {str(e)}")
            raise
    
    async def _generate_opportunities(self) -> List[Dict[str, Any]]:
        """Generate simulated arbitrage opportunities"""
        opportunities = []
        
        for symbol in self.config['currency_pairs']:
            try:
                # Get price spread
                spreads = self.price_monitor.get_price_spread(symbol)
                
                for spread_data in spreads.values():
                    spread_percent = spread_data['spread_percent']
                    min_spread = self.config['spread_requirements'].get(symbol, 0.005)
                    
                    if spread_percent >= min_spread:
                        opportunity = {
                            'symbol': symbol,
                            'buy_exchange': spread_data['lower_price_exchange'],
                            'sell_exchange': spread_data['higher_price_exchange'],
                            'buy_price': spread_data['lower_price'],
                            'sell_price': spread_data['higher_price'],
                            'spread_percent': spread_percent,
                            'timestamp': time.time()
                        }
                        opportunities.append(opportunity)
            
            except Exception as e:
                self.errors.append(f"Opportunity generation error for {symbol}: {str(e)}")
        
        return opportunities
    
    async def _can_execute_trade(self) -> bool:
        """Check if we can execute a trade with proper balance validation"""
        try:
            # Check concurrent trade limit
            active_trades = len([t for t in self.trades if t.status == 'pending'])
            if active_trades >= self.config['max_concurrent_trades']:
                return False
            
            # Check total exposure
            total_balance = 0
            for exchange in self.exchanges.values():
                total_balance += await exchange.get_total_balance_usd()
            
            total_exposure = self.config['max_total_exposure'] * total_balance
            
            # Check if we have sufficient balance for a trade
            min_trade_amount = total_balance * 0.01  # 1% minimum
            if min_trade_amount < 10:  # Minimum $10 trade
                return False
            
            return True
            
        except Exception as e:
            self.errors.append(f"Trade validation error: {str(e)}")
            return False
    
    async def _execute_fixed_trade(self, opportunity: Dict[str, Any]):
        """Execute a fixed simulated trade with proper balance management"""
        try:
            start_time = time.time()
            
            # Calculate position size with balance validation
            position_size = await self._calculate_fixed_position_size(opportunity)
            if position_size <= 0:
                self.warnings.append(f"Invalid position size for {opportunity['symbol']}")
                return
            
            # Get exchanges
            buy_exchange = self.exchanges[opportunity['buy_exchange']]
            sell_exchange = self.exchanges[opportunity['sell_exchange']]
            
            # Validate balances before execution
            if not await self._validate_balances(buy_exchange, sell_exchange, opportunity['symbol'], position_size):
                self.warnings.append(f"Insufficient balances for {opportunity['symbol']}")
                return
            
            # Execute buy order
            buy_order = await buy_exchange.create_order(
                symbol=opportunity['symbol'],
                type='market',
                side='buy',
                amount=position_size,
                price=opportunity['buy_price']
            )
            
            # Execute sell order
            sell_order = await sell_exchange.create_order(
                symbol=opportunity['symbol'],
                type='market',
                side='sell',
                amount=position_size,
                price=opportunity['sell_price']
            )
            
            # Calculate results
            execution_time = time.time() - start_time
            profit_expected = position_size * opportunity['spread_percent']
            profit_actual = (sell_order['price'] - buy_order['price']) * position_size
            fees_paid = buy_order['fee'] + sell_order['fee']
            slippage = abs(sell_order['price'] - opportunity['sell_price']) * position_size
            
            # Create trade record
            trade = FixedSimulatedTrade(
                symbol=opportunity['symbol'],
                buy_exchange=opportunity['buy_exchange'],
                sell_exchange=opportunity['sell_exchange'],
                buy_price=buy_order['price'],
                sell_price=sell_order['price'],
                amount=position_size,
                profit_expected=profit_expected,
                profit_actual=profit_actual,
                fees_paid=fees_paid,
                slippage=slippage,
                execution_time=execution_time,
                status='completed',
                timestamp=time.time(),
                trade_id=f"fixed_{int(time.time() * 1000)}"
            )
            
            self.trades.append(trade)
            
            # Check for issues
            self._check_trade_issues(trade)
            
            # Log successful trade
            logger.info(f"✅ Successful trade: {opportunity['symbol']} - Profit: ${profit_actual:.2f}")
            
        except Exception as e:
            self.errors.append(f"Trade execution error: {str(e)}")
            logger.error(f"Trade execution error: {str(e)}")
    
    async def _calculate_fixed_position_size(self, opportunity: Dict[str, Any]) -> float:
        """Calculate position size with proper balance validation"""
        try:
            # Get total balance across all exchanges
            total_balance = 0
            for exchange in self.exchanges.values():
                total_balance += await exchange.get_total_balance_usd()
            
            if total_balance <= 0:
                return 0.0
            
            # Get position percentage
            position_percent = self.config['position_percentages'].get(opportunity['symbol'], 0.05)
            
            # Calculate position size
            position_size = total_balance * position_percent
            
            # Apply limits
            max_position = total_balance * 0.08  # 8% max
            min_position = total_balance * 0.01  # 1% min
            
            position_size = min(position_size, max_position)
            position_size = max(position_size, min_position)
            
            # Validate against available balance
            buy_exchange = self.exchanges[opportunity['buy_exchange']]
            required_usdt = position_size * opportunity['buy_price'] * 1.1  # 10% buffer
            
            buy_balance = await buy_exchange.get_balance()
            if buy_balance['USDT'] < required_usdt:
                # Reduce position size to available balance
                available_usdt = buy_balance['USDT']
                position_size = available_usdt / (opportunity['buy_price'] * 1.1)
                
                if position_size < min_position:
                    return 0.0
            
            return position_size
            
        except Exception as e:
            self.errors.append(f"Position size calculation error: {str(e)}")
            return 0.0
    
    async def _validate_balances(self, buy_exchange, sell_exchange, symbol: str, amount: float) -> bool:
        """Validate balances before trade execution"""
        try:
            # Check buy exchange has enough USDT
            buy_balance = await buy_exchange.get_balance()
            required_usdt = amount * 1.1  # 10% buffer
            if buy_balance['USDT'] < required_usdt:
                return False
            
            # Check sell exchange has enough crypto
            sell_crypto_balance = await sell_exchange.get_crypto_balance(symbol)
            if sell_crypto_balance < amount:
                return False
            
            return True
            
        except Exception as e:
            self.errors.append(f"Balance validation error: {str(e)}")
            return False
    
    def _check_trade_issues(self, trade: FixedSimulatedTrade):
        """Check for issues in trade execution"""
        try:
            # Check for negative profit
            if trade.profit_actual < 0:
                self.errors.append(f"Negative profit trade: {trade.symbol} - ${trade.profit_actual:.2f}")
            
            # Check for high slippage
            slippage_percent = trade.slippage / (trade.amount * trade.sell_price) * 100
            if slippage_percent > 0.5:  # > 0.5% slippage
                self.warnings.append(f"High slippage: {trade.symbol} - {slippage_percent:.2f}%")
            
            # Check for high fees
            fee_percent = trade.fees_paid / (trade.amount * trade.sell_price) * 100
            if fee_percent > 0.1:  # > 0.1% fees
                self.warnings.append(f"High fees: {trade.symbol} - {fee_percent:.2f}%")
            
            # Check for slow execution
            if trade.execution_time > 5.0:  # > 5 seconds
                self.performance_issues.append(f"Slow execution: {trade.symbol} - {trade.execution_time:.2f}s")
            
            # Check for low profit
            if trade.profit_actual < trade.profit_expected * 0.5:  # < 50% of expected
                self.warnings.append(f"Low profit: {trade.symbol} - Expected: ${trade.profit_expected:.2f}, Actual: ${trade.profit_actual:.2f}")
            
        except Exception as e:
            self.errors.append(f"Trade issue check error: {str(e)}")
    
    def _analyze_simulation_results(self) -> FixedSimulationResults:
        """Analyze simulation results"""
        try:
            total_trades = len(self.trades)
            successful_trades = len([t for t in self.trades if t.status == 'completed'])
            failed_trades = total_trades - successful_trades
            
            total_profit = sum(t.profit_actual for t in self.trades if t.status == 'completed')
            total_fees = sum(t.fees_paid for t in self.trades)
            total_slippage = sum(t.slippage for t in self.trades)
            
            success_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
            avg_profit_per_trade = (total_profit / successful_trades) if successful_trades > 0 else 0
            
            # Calculate max drawdown
            max_drawdown = self._calculate_max_drawdown()
            
            # Calculate Sharpe ratio
            sharpe_ratio = self._calculate_sharpe_ratio()
            
            # Track balance issues fixed
            balance_issues_fixed = [
                "Added balance validation before trade execution",
                "Implemented proper balance tracking",
                "Added balance locks for thread safety",
                "Fixed insufficient balance error handling",
                "Added balance buffer for trade execution"
            ]
            
            return FixedSimulationResults(
                total_trades=total_trades,
                successful_trades=successful_trades,
                failed_trades=failed_trades,
                total_profit=total_profit,
                total_fees=total_fees,
                total_slippage=total_slippage,
                success_rate=success_rate,
                avg_profit_per_trade=avg_profit_per_trade,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                errors_found=self.errors.copy(),
                warnings_found=self.warnings.copy(),
                performance_issues=self.performance_issues.copy(),
                balance_issues_fixed=balance_issues_fixed
            )
            
        except Exception as e:
            logger.error(f"Error analyzing results: {str(e)}")
            return FixedSimulationResults(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, [str(e)], [], [], [])
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        try:
            if not self.trades:
                return 0.0
            
            # Calculate cumulative profit
            cumulative_profit = 0
            max_profit = 0
            max_drawdown = 0
            
            for trade in self.trades:
                if trade.status == 'completed':
                    cumulative_profit += trade.profit_actual
                    max_profit = max(max_profit, cumulative_profit)
                    drawdown = max_profit - cumulative_profit
                    max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {str(e)}")
            return 0.0
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio"""
        try:
            if len(self.trades) < 2:
                return 0.0
            
            profits = [t.profit_actual for t in self.trades if t.status == 'completed']
            if len(profits) < 2:
                return 0.0
            
            mean_profit = sum(profits) / len(profits)
            variance = sum((p - mean_profit) ** 2 for p in profits) / len(profits)
            std_dev = math.sqrt(variance)
            
            if std_dev == 0:
                return 0.0
            
            return mean_profit / std_dev
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0.0
    
    def print_simulation_results(self, results: FixedSimulationResults):
        """Print simulation results"""
        print('\n' + '=' * 80)
        print('FIXED SIMULATION TEST RESULTS')
        print('=' * 80)
        
        print(f'Total Trades: {results.total_trades}')
        print(f'Successful Trades: {results.successful_trades}')
        print(f'Failed Trades: {results.failed_trades}')
        print(f'Success Rate: {results.success_rate:.2f}%')
        print(f'Total Profit: ${results.total_profit:.2f}')
        print(f'Total Fees: ${results.total_fees:.2f}')
        print(f'Total Slippage: ${results.total_slippage:.2f}')
        print(f'Average Profit per Trade: ${results.avg_profit_per_trade:.2f}')
        print(f'Max Drawdown: ${results.max_drawdown:.2f}')
        print(f'Sharpe Ratio: {results.sharpe_ratio:.2f}')
        
        if results.balance_issues_fixed:
            print(f'\n✅ BALANCE ISSUES FIXED ({len(results.balance_issues_fixed)}):')
            for fix in results.balance_issues_fixed:
                print(f'   • {fix}')
        
        if results.errors_found:
            print(f'\n❌ ERRORS FOUND ({len(results.errors_found)}):')
            for error in results.errors_found[:10]:  # Show first 10
                print(f'   • {error}')
        
        if results.warnings_found:
            print(f'\n⚠️  WARNINGS FOUND ({len(results.warnings_found)}):')
            for warning in results.warnings_found[:10]:  # Show first 10
                print(f'   • {warning}')
        
        if results.performance_issues:
            print(f'\n🐌 PERFORMANCE ISSUES ({len(results.performance_issues)}):')
            for issue in results.performance_issues[:10]:  # Show first 10
                print(f'   • {issue}')
        
        # Overall assessment
        if results.errors_found:
            print('\n⚠️  SIMULATION COMPLETED WITH ERRORS')
            print('Some issues remain to be addressed')
        elif results.warnings_found or results.performance_issues:
            print('\n✅ SIMULATION COMPLETED WITH WARNINGS')
            print('System is functional but has minor issues')
        else:
            print('\n✅ SIMULATION COMPLETED SUCCESSFULLY')
            print('System is ready for deployment')

async def run_fixed_simulation_test():
    """Run fixed simulation test"""
    print('=' * 80)
    print('FIXED HIGH-FREQUENCY ARBITRAGE SIMULATION TEST')
    print('=' * 80)
    
    tester = FixedSimulationTester()
    
    print('Starting fixed simulation test...')
    print('This will simulate 5 minutes of trading activity with fixed balance management...')
    
    # Run simulation
    results = await tester.run_fixed_simulation()
    
    # Print results
    tester.print_simulation_results(results)
    
    # Save results to file
    with open('fixed_simulation_results.json', 'w') as f:
        json.dump(asdict(results), f, indent=2)
    
    print(f'\n📄 Detailed results saved to: fixed_simulation_results.json')
    
    return results

if __name__ == "__main__":
    # Run fixed simulation test
    asyncio.run(run_fixed_simulation_test())
