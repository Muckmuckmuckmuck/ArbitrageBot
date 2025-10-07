import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
from dynamic_balance_manager import DynamicBalanceManager
import logging

logger = logging.getLogger(__name__)

@dataclass
class AdaptiveProfitAnalysis:
    """Data class for adaptive profit analysis"""
    symbol: str
    tier: str
    current_balance_usd: float
    recommended_position_usd: float
    daily_opportunities: int
    avg_spread_percent: float
    gross_profit_per_trade: float
    trading_fees: float
    transfer_fees: float
    slippage_cost: float
    net_profit_per_trade: float
    daily_net_profit: float
    success_rate: float
    risk_level: str
    scalability_score: float

class AdaptiveProfitCalculator:
    """Adaptive profit calculator that adjusts to account balance"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.balance_manager = DynamicBalanceManager(exchange_manager)
        
        # Adaptive parameters
        self.adaptive_config = {
            'min_starting_balance': 100,      # Minimum $100 to start
            'balance_growth_threshold': 1.2,  # 20% growth to increase positions
            'max_balance_multiplier': 10,     # Max 10x starting balance
            'position_scaling_factor': 0.8,   # Conservative scaling
            'profit_reinvestment_rate': 0.5,  # Reinvest 50% of profits
        }
        
        # Performance tracking
        self.starting_balance = 0
        self.current_balance = 0
        self.balance_growth_history = {}
        self.profit_reinvestment_history = {}
        
    async def calculate_adaptive_profits(self) -> List[AdaptiveProfitAnalysis]:
        """Calculate adaptive profits based on current balance"""
        try:
            # Get current balance and allocations
            balance_optimization = await self.balance_manager.optimize_balance_allocation()
            position_allocations = await self.balance_manager.calculate_position_allocations()
            
            analyses = []
            
            # Calculate profits for each symbol
            for symbol in Config.CURRENCY_PAIRS:
                try:
                    allocation = position_allocations.get(symbol)
                    if allocation:
                        analysis = await self._calculate_adaptive_symbol_profit(symbol, allocation, balance_optimization)
                        if analysis:
                            analyses.append(analysis)
                            
                except Exception as e:
                    logger.error(f"Error calculating adaptive profit for {symbol}: {str(e)}")
                    continue
            
            return analyses
            
        except Exception as e:
            logger.error(f"Error calculating adaptive profits: {str(e)}")
            return []
    
    async def _calculate_adaptive_symbol_profit(self, symbol: str, allocation: dict, 
                                              balance_optimization: dict) -> Optional[AdaptiveProfitAnalysis]:
        """Calculate adaptive profit for a specific symbol"""
        try:
            # Get symbol configuration
            transfer_config = Config.TRANSFER_SPEEDS.get(symbol, {})
            min_spread = transfer_config.get('min_spread', 0.008)
            tier = self._get_symbol_tier(symbol)
            
            # Get current balance and position size
            current_balance_usd = balance_optimization.total_usd_value
            recommended_position_usd = allocation.recommended_position_usd
            
            # Calculate adaptive parameters
            daily_opportunities = self._calculate_adaptive_opportunities(tier, current_balance_usd)
            success_rate = self._calculate_adaptive_success_rate(tier, current_balance_usd)
            
            # Calculate spread (adjust based on balance size)
            avg_spread_percent = self._calculate_adaptive_spread(min_spread, current_balance_usd)
            
            # Calculate costs
            trading_fees = self._calculate_trading_fees(recommended_position_usd)
            transfer_fees = self._get_transfer_fees(symbol)
            slippage_cost = self._calculate_slippage_cost(recommended_position_usd, symbol)
            
            # Calculate profits
            gross_profit_per_trade = recommended_position_usd * avg_spread_percent
            net_profit_per_trade = gross_profit_per_trade - trading_fees - transfer_fees - slippage_cost
            
            # Daily profit
            successful_trades = daily_opportunities * success_rate
            daily_net_profit = net_profit_per_trade * successful_trades
            
            # Calculate scalability score
            scalability_score = self._calculate_scalability_score(symbol, current_balance_usd)
            
            # Determine risk level
            risk_level = allocation.risk_level
            
            return AdaptiveProfitAnalysis(
                symbol=symbol,
                tier=tier,
                current_balance_usd=current_balance_usd,
                recommended_position_usd=recommended_position_usd,
                daily_opportunities=daily_opportunities,
                avg_spread_percent=avg_spread_percent,
                gross_profit_per_trade=gross_profit_per_trade,
                trading_fees=trading_fees,
                transfer_fees=transfer_fees,
                slippage_cost=slippage_cost,
                net_profit_per_trade=net_profit_per_trade,
                daily_net_profit=daily_net_profit,
                success_rate=success_rate,
                risk_level=risk_level,
                scalability_score=scalability_score
            )
            
        except Exception as e:
            logger.error(f"Error calculating adaptive symbol profit for {symbol}: {str(e)}")
            return None
    
    def _get_symbol_tier(self, symbol: str) -> str:
        """Get tier for a symbol"""
        if symbol in Config.TIER1_ASSETS:
            return 'tier1'
        elif symbol in Config.TIER2_ASSETS:
            return 'tier2'
        elif symbol in Config.TIER3_ASSETS:
            return 'tier3'
        else:
            return 'tier3'
    
    def _calculate_adaptive_opportunities(self, tier: str, balance_usd: float) -> int:
        """Calculate consistent daily opportunities regardless of balance"""
        try:
            # Consistent opportunities regardless of balance size
            base_opportunities = {
                'tier1': 15, 'tier2': 8, 'tier3': 5
            }
            
            # No balance-based adjustment - consistent strategy
            return base_opportunities.get(tier, 5)
            
        except Exception as e:
            logger.error(f"Error calculating adaptive opportunities: {str(e)}")
            return 5
    
    def _calculate_adaptive_success_rate(self, tier: str, balance_usd: float) -> float:
        """Calculate consistent success rate regardless of balance"""
        try:
            # Consistent success rates regardless of balance size
            base_success_rates = {
                'tier1': 0.75, 'tier2': 0.65, 'tier3': 0.55
            }
            
            # No balance-based adjustment - consistent strategy
            return base_success_rates.get(tier, 0.55)
            
        except Exception as e:
            logger.error(f"Error calculating adaptive success rate: {str(e)}")
            return 0.6
    
    def _calculate_adaptive_spread(self, min_spread: float, balance_usd: float) -> float:
        """Calculate consistent spread regardless of balance"""
        try:
            # Consistent spread multiplier regardless of balance size
            # Use 1.2x minimum spread for all balances
            return min_spread * 1.2
            
        except Exception as e:
            logger.error(f"Error calculating adaptive spread: {str(e)}")
            return min_spread * 1.2
    
    def _calculate_trading_fees(self, position_size: float) -> float:
        """Calculate trading fees"""
        try:
            # Average fees from both exchanges
            avg_fee_rate = 0.003  # 0.3% total (buy + sell)
            return position_size * avg_fee_rate
            
        except Exception as e:
            logger.error(f"Error calculating trading fees: {str(e)}")
            return position_size * 0.003
    
    def _get_transfer_fees(self, symbol: str) -> float:
        """Get transfer fees for symbol"""
        try:
            base_currency = symbol.split('/')[0]
            return 0.01  # Default $0.01 transfer fee
            
        except Exception as e:
            logger.error(f"Error getting transfer fees: {str(e)}")
            return 0.01
    
    def _calculate_slippage_cost(self, position_size: float, symbol: str) -> float:
        """Calculate slippage cost"""
        try:
            # Slippage rates by asset
            slippage_rates = {
                'XRP/USDT': 0.05, 'XLM/USDT': 0.05, 'SOL/USDT': 0.08, 'BNB/USDT': 0.05,
                'TON/USDT': 0.10, 'USDC/USDT': 0.01, 'USDT/USDC': 0.01,
                'default': 0.10
            }
            
            slippage_rate = slippage_rates.get(symbol, slippage_rates['default'])
            return position_size * (slippage_rate / 100)
            
        except Exception as e:
            logger.error(f"Error calculating slippage cost: {str(e)}")
            return position_size * 0.001
    
    def _calculate_scalability_score(self, symbol: str, balance_usd: float) -> float:
        """Calculate consistent scalability score regardless of balance"""
        try:
            # Consistent scalability by tier regardless of balance
            tier_scores = {'tier1': 0.9, 'tier2': 0.7, 'tier3': 0.5}
            tier = self._get_symbol_tier(symbol)
            base_score = tier_scores.get(tier, 0.5)
            
            # No balance-based adjustment - consistent strategy
            return base_score
            
        except Exception as e:
            logger.error(f"Error calculating scalability score: {str(e)}")
            return 0.5
    
    async def get_adaptive_profit_summary(self) -> Dict:
        """Get adaptive profit summary"""
        try:
            analyses = await self.calculate_adaptive_profits()
            
            if not analyses:
                return {}
            
            # Calculate totals
            total_daily_net_profit = sum(a.daily_net_profit for a in analyses)
            total_daily_gross_profit = sum(a.gross_profit_per_trade * a.daily_opportunities * a.success_rate for a in analyses)
            total_trades = sum(a.daily_opportunities * a.success_rate for a in analyses)
            
            # Calculate balance growth potential
            current_balance = analyses[0].current_balance_usd if analyses else 0
            monthly_profit = total_daily_net_profit * 30
            yearly_profit = total_daily_net_profit * 365
            
            # Calculate growth rates
            monthly_growth_rate = (monthly_profit / current_balance * 100) if current_balance > 0 else 0
            yearly_growth_rate = (yearly_profit / current_balance * 100) if current_balance > 0 else 0
            
            # Find best performers
            best_performer = max(analyses, key=lambda x: x.daily_net_profit) if analyses else None
            worst_performer = min(analyses, key=lambda x: x.daily_net_profit) if analyses else None
            
            # Calculate average metrics
            avg_success_rate = sum(a.success_rate for a in analyses) / len(analyses)
            avg_scalability_score = sum(a.scalability_score for a in analyses) / len(analyses)
            
            # Tier breakdown
            tier_breakdown = {'tier1': 0, 'tier2': 0, 'tier3': 0}
            for analysis in analyses:
                tier_breakdown[analysis.tier] += analysis.daily_net_profit
            
            summary = {
                'current_balance_usd': current_balance,
                'total_daily_net_profit': total_daily_net_profit,
                'total_daily_gross_profit': total_daily_gross_profit,
                'monthly_net_profit': monthly_profit,
                'yearly_net_profit': yearly_profit,
                'monthly_growth_rate': monthly_growth_rate,
                'yearly_growth_rate': yearly_growth_rate,
                'total_daily_trades': total_trades,
                'total_assets': len(analyses),
                'avg_success_rate': avg_success_rate,
                'avg_scalability_score': avg_scalability_score,
                'tier_breakdown': tier_breakdown,
                'best_performer': {
                    'symbol': best_performer.symbol,
                    'daily_net_profit': best_performer.daily_net_profit,
                    'tier': best_performer.tier
                } if best_performer else None,
                'worst_performer': {
                    'symbol': worst_performer.symbol,
                    'daily_net_profit': worst_performer.daily_net_profit,
                    'tier': worst_performer.tier
                } if worst_performer else None,
                'detailed_analyses': analyses
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting adaptive profit summary: {str(e)}")
            return {}
    
    async def get_balance_scaling_recommendations(self) -> List[str]:
        """Get recommendations for scaling with balance growth"""
        try:
            summary = await self.get_adaptive_profit_summary()
            recommendations = []
            
            if not summary:
                return ["No profit data available for recommendations"]
            
            current_balance = summary['current_balance_usd']
            monthly_growth_rate = summary['monthly_growth_rate']
            yearly_growth_rate = summary['yearly_growth_rate']
            
            # Starting balance recommendations
            if current_balance < self.adaptive_config['min_starting_balance']:
                recommendations.append(f"Current balance (${current_balance:.2f}) below minimum "
                                     f"(${self.adaptive_config['min_starting_balance']}). "
                                     "Consider adding funds to start trading.")
            
            # Growth rate recommendations
            if monthly_growth_rate > 20:
                recommendations.append(f"Excellent monthly growth rate ({monthly_growth_rate:.1f}%). "
                                     "Consider increasing position sizes gradually.")
            elif monthly_growth_rate < 5:
                recommendations.append(f"Low monthly growth rate ({monthly_growth_rate:.1f}%). "
                                     "Consider optimizing strategy or increasing starting balance.")
            
            # Balance scaling recommendations
            if current_balance < 1000:
                recommendations.append("Small balance detected. Focus on high-probability, "
                                     "low-risk trades to build capital.")
            elif current_balance < 5000:
                recommendations.append("Medium balance detected. Good opportunity to diversify "
                                     "across multiple assets and strategies.")
            else:
                recommendations.append("Large balance detected. Consider implementing "
                                     "advanced strategies and larger position sizes.")
            
            # Scalability recommendations
            best_performer = summary.get('best_performer')
            if best_performer and best_performer['daily_net_profit'] > 50:
                recommendations.append(f"Best performer ({best_performer['symbol']}) showing "
                                     f"strong returns (${best_performer['daily_net_profit']:.2f}/day). "
                                     "Consider increasing allocation.")
            
            # Risk recommendations
            avg_scalability = summary['avg_scalability_score']
            if avg_scalability > 0.8:
                recommendations.append("High scalability score. Good opportunity for "
                                     "aggressive growth strategies.")
            elif avg_scalability < 0.4:
                recommendations.append("Low scalability score. Focus on conservative "
                                     "strategies and capital preservation.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting balance scaling recommendations: {str(e)}")
            return ["Error generating recommendations"]
    
    def print_adaptive_profit_report(self):
        """Print adaptive profit report"""
        try:
            summary = asyncio.run(self.get_adaptive_profit_summary())
            
            if not summary:
                print("No adaptive profit data available")
                return
            
            print("=" * 80)
            print("ADAPTIVE ARBITRAGE BOT PROFIT ANALYSIS")
            print("=" * 80)
            
            # Balance and growth summary
            print(f"\nBALANCE & GROWTH SUMMARY:")
            print(f"Current Balance: ${summary['current_balance_usd']:.2f}")
            print(f"Daily Net Profit: ${summary['total_daily_net_profit']:.2f}")
            print(f"Monthly Net Profit: ${summary['monthly_net_profit']:.2f}")
            print(f"Yearly Net Profit: ${summary['yearly_net_profit']:.2f}")
            print(f"Monthly Growth Rate: {summary['monthly_growth_rate']:.1f}%")
            print(f"Yearly Growth Rate: {summary['yearly_growth_rate']:.1f}%")
            
            # Performance metrics
            print(f"\nPERFORMANCE METRICS:")
            print(f"Total Daily Trades: {summary['total_daily_trades']:.0f}")
            print(f"Total Assets: {summary['total_assets']}")
            print(f"Average Success Rate: {summary['avg_success_rate']:.1%}")
            print(f"Average Scalability Score: {summary['avg_scalability_score']:.2f}")
            
            # Tier breakdown
            print(f"\nTIER BREAKDOWN:")
            tier_breakdown = summary['tier_breakdown']
            for tier, profit in tier_breakdown.items():
                print(f"{tier.upper()}: ${profit:.2f} daily profit")
            
            # Top performers
            if summary['best_performer'] and summary['worst_performer']:
                print(f"\nTOP PERFORMERS:")
                best = summary['best_performer']
                worst = summary['worst_performer']
                print(f"Best: {best['symbol']} (${best['daily_net_profit']:.2f} daily, {best['tier']})")
                print(f"Worst: {worst['symbol']} (${worst['daily_net_profit']:.2f} daily, {worst['tier']})")
            
            # Detailed analysis (top 10)
            print(f"\nDETAILED ANALYSIS (Top 10 Assets):")
            analyses = summary['detailed_analyses']
            sorted_analyses = sorted(analyses, key=lambda x: x.daily_net_profit, reverse=True)
            
            print(f"{'Symbol':<12} {'Balance':<10} {'Position':<10} {'Net Profit':<12} {'Success Rate':<12} {'Risk':<6}")
            print("-" * 80)
            
            for analysis in sorted_analyses[:10]:
                print(f"{analysis.symbol:<12} ${analysis.current_balance_usd:<9.0f} "
                      f"${analysis.recommended_position_usd:<9.0f} ${analysis.daily_net_profit:<11.2f} "
                      f"{analysis.success_rate:<11.1%} {analysis.risk_level:<5}")
            
            # Scaling recommendations
            print(f"\nBALANCE SCALING RECOMMENDATIONS:")
            recommendations = asyncio.run(self.get_balance_scaling_recommendations())
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
            
            print("=" * 80)
            
        except Exception as e:
            logger.error(f"Error printing adaptive profit report: {str(e)}")
            print(f"Error generating report: {str(e)}")

# Example usage and testing
if __name__ == "__main__":
    # Mock exchange manager for testing
    class MockExchangeManager:
        def get_exchange(self, name):
            return MockExchange()
    
    class MockExchange:
        async def get_balances(self):
            return {
                'USDT': {'free': 1000, 'used': 0, 'total': 1000},
                'XRP': {'free': 100, 'used': 0, 'total': 100},
                'BTC': {'free': 0.01, 'used': 0, 'total': 0.01}
            }
        
        async def get_ticker(self, symbol):
            return {'last': 0.6 if 'XRP' in symbol else 45000 if 'BTC' in symbol else 1.0}
    
    calculator = AdaptiveProfitCalculator(MockExchangeManager())
    calculator.print_adaptive_profit_report()
