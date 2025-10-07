#!/usr/bin/env python3
"""
Balance scaling demonstration for arbitrage bot
Shows how profit calculations adapt to different starting balances
"""

import asyncio
from adaptive_profit_calculator import AdaptiveProfitCalculator

class MockExchangeManager:
    """Mock exchange manager for testing"""
    def get_exchange(self, name):
        return MockExchange()

class MockExchange:
    """Mock exchange for testing"""
    
    def __init__(self, starting_balance=500):
        self.starting_balance = starting_balance
    
    async def get_balances(self):
        return {
            'USDT': {'free': self.starting_balance, 'used': 0, 'total': self.starting_balance},
            'XRP': {'free': self.starting_balance / 5, 'used': 0, 'total': self.starting_balance / 5},
            'BTC': {'free': self.starting_balance / 45000, 'used': 0, 'total': self.starting_balance / 45000},
        }
    
    async def get_ticker(self, symbol):
        prices = {
            'XRP/USDT': 0.6,
            'BTC/USDT': 45000,
            'SOL/USDT': 100,
            'TON/USDT': 2.5,
            'USDC/USDT': 1.0,
        }
        return {'last': prices.get(symbol, 1.0)}

async def test_balance_scaling():
    """Test balance scaling with different starting amounts"""
    
    test_scenarios = [
        ("SMALL BALANCE", 100),      # $100 - minimum viable
        ("SMALL BALANCE", 500),      # $500 - conservative start
        ("MEDIUM BALANCE", 2000),    # $2,000 - good starting point
        ("LARGE BALANCE", 10000),    # $10,000 - substantial capital
        ("VERY LARGE", 50000),       # $50,000 - significant investment
    ]
    
    print("=" * 80)
    print("ARBITRAGE BOT - BALANCE SCALING ANALYSIS")
    print("=" * 80)
    
    for scenario_name, balance in test_scenarios:
        print(f"\n{scenario_name}: ${balance:,}")
        print("-" * 60)
        
        # Create calculator with specific balance
        exchange_manager = MockExchangeManager()
        calculator = AdaptiveProfitCalculator(exchange_manager)
        
        # Override the exchange to use specific balance
        exchange_manager.get_exchange = lambda x: MockExchange(balance)
        
        # Get adaptive profit summary
        summary = await calculator.get_adaptive_profit_summary()
        
        if summary:
            # Key metrics
            current_balance = summary.get('current_balance_usd', 0)
            daily_profit = summary.get('total_daily_net_profit', 0)
            monthly_profit = summary.get('monthly_net_profit', 0)
            yearly_profit = summary.get('yearly_net_profit', 0)
            monthly_growth = summary.get('monthly_growth_rate', 0)
            avg_success_rate = summary.get('avg_success_rate', 0)
            scalability_score = summary.get('avg_scalability_score', 0)
            
            print(f"Current Balance: ${current_balance:,.2f}")
            print(f"Daily Net Profit: ${daily_profit:,.2f}")
            print(f"Monthly Net Profit: ${monthly_profit:,.2f}")
            print(f"Yearly Net Profit: ${yearly_profit:,.2f}")
            print(f"Monthly Growth Rate: {monthly_growth:.1f}%")
            print(f"Average Success Rate: {avg_success_rate:.1%}")
            print(f"Scalability Score: {scalability_score:.2f}")
            
            # Top performers
            best_performer = summary.get('best_performer')
            if best_performer:
                print(f"Best Performer: {best_performer['symbol']} (${best_performer['daily_net_profit']:.2f}/day)")
            
            # Tier breakdown
            tier_breakdown = summary.get('tier_breakdown', {})
            print(f"Tier 1 Profit: ${tier_breakdown.get('tier1', 0):.2f}")
            print(f"Tier 2 Profit: ${tier_breakdown.get('tier2', 0):.2f}")
            print(f"Tier 3 Profit: ${tier_breakdown.get('tier3', 0):.2f}")
            
            # Recommendations
            recommendations = await calculator.get_balance_scaling_recommendations()
            if recommendations:
                print("Key Recommendations:")
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"  {i}. {rec}")
        
        print()

def print_scaling_insights():
    """Print insights about balance scaling"""
    print("=" * 80)
    print("BALANCE SCALING INSIGHTS")
    print("=" * 80)
    
    insights = [
        "1. MINIMUM VIABLE BALANCE: $100-$500",
        "   - Bot can start with small amounts",
        "   - Focus on ultra-fast assets (Tier 1)",
        "   - Conservative position sizing",
        "",
        "2. GROWTH PHASE: $500-$5,000",
        "   - Diversification across all tiers",
        "   - Balanced risk management",
        "   - Steady profit accumulation",
        "",
        "3. SCALING PHASE: $5,000-$50,000",
        "   - Larger position sizes",
        "   - Advanced strategies enabled",
        "   - Higher absolute profits",
        "",
        "4. OPTIMIZATION FEATURES:",
        "   - Dynamic position sizing based on balance",
        "   - Automatic rebalancing recommendations",
        "   - Risk-adjusted allocation",
        "   - Performance tracking and scaling",
        "",
        "5. KEY BENEFITS:",
        "   - Start with any amount",
        "   - Automatic scaling as balance grows",
        "   - Conservative risk management",
        "   - Continuous optimization",
        "",
        "6. RECOMMENDED APPROACH:",
        "   - Start with $500-$1,000",
        "   - Let profits compound",
        "   - Add funds gradually based on performance",
        "   - Monitor and adjust allocations",
    ]
    
    for insight in insights:
        print(insight)

if __name__ == "__main__":
    # Run the balance scaling test
    asyncio.run(test_balance_scaling())
    
    # Print insights
    print_scaling_insights()

