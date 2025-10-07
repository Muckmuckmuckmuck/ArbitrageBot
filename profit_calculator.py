import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProfitAnalysis:
    """Data class for profit analysis"""
    symbol: str
    tier: str
    daily_opportunities: int
    avg_spread_percent: float
    position_size_usd: float
    gross_profit_per_trade: float
    trading_fees: float
    transfer_fees: float
    slippage_cost: float
    net_profit_per_trade: float
    daily_gross_profit: float
    daily_net_profit: float
    success_rate: float
    risk_score: float

class ProfitCalculator:
    """Profit calculation and analysis system"""
    
    def __init__(self):
        # Trading fees (maker/taker fees)
        self.trading_fees = {
            'binance': {'maker': 0.001, 'taker': 0.001},  # 0.1%
            'kraken': {'maker': 0.0016, 'taker': 0.0026}  # 0.16% / 0.26%
        }
        
        # Transfer fees by network (in USD equivalent)
        self.transfer_fees = {
            # Ultra-fast networks
            'XRP': 0.01, 'XLM': 0.001, 'SOL': 0.001, 'EOS': 0.01, 'TRX': 0.01,
            'FTM': 0.001, 'NANO': 0.0, 'TON': 0.1, 'HBAR': 0.001, 'BNB': 0.05,
            'ALGO': 0.001, 'MATIC': 0.01, 'AVAX': 0.1, 'NEAR': 0.01, 'DOT': 0.1,
            
            # Fast networks
            'ICX': 0.01, 'ONT': 0.01, 'ZIL': 0.001, 'VET': 0.01, 'ADA': 1.0,
            'XTZ': 0.01, 'ATOM': 0.01, 'ARB': 0.01, 'OP': 0.01, 'LRC': 0.01,
            'AAVE': 0.01, 'COMP': 0.01, 'SUSHI': 0.01, 'GRT': 0.01, 'BAND': 0.01,
            'API3': 0.01, 'XMR': 0.01, 'BCH': 0.01, 'FIL': 0.01,
            
            # Slower networks
            'LTC': 0.01, 'DOGE': 0.01, 'DASH': 0.01, 'ZEC': 0.01, 'NEO': 0.01,
            'QTUM': 0.01, 'CHZ': 0.01, 'BAT': 0.01, 'ZRX': 0.01, 'KNC': 0.01,
            'REP': 0.01, 'MKR': 0.001, 'SNX': 0.01, 'YFI': 0.001, 'CRV': 0.01,
            '1INCH': 0.01, 'LQTY': 0.01, 'RNDR': 0.01, 'FLOW': 0.01, 'ICP': 0.01,
            'STORJ': 0.01, 'FET': 0.01, 'AGIX': 0.01, 'OCEAN': 0.01, 'SAND': 0.01,
            'MANA': 0.01, 'AXS': 0.01, 'ENJ': 0.01, 'ETC': 0.01, 'BSV': 0.01,
            'RVN': 0.01, 'SC': 0.01, 'ZEN': 0.01, 'BEAM': 0.01, 'GRIN': 0.01,
            'MWC': 0.01, 'PIVX': 0.01, 'DCR': 0.01, 'DGB': 0.01, 'VTC': 0.01, 'MONA': 0.01,
            
            # Stablecoins
            'USDC': 0.0, 'USDT': 0.0, 'DAI': 0.001, 'BUSD': 0.0,
            
            # Other major assets
            'UNI': 0.01, 'LINK': 0.01,
        }
        
        # Slippage estimates by asset (percentage)
        self.slippage_rates = {
            # High liquidity - low slippage
            'XRP/USDT': 0.05, 'XLM/USDT': 0.05, 'SOL/USDT': 0.08, 'BNB/USDT': 0.05,
            'LTC/USDT': 0.05, 'DOGE/USDT': 0.08, 'USDC/USDT': 0.01, 'USDT/USDC': 0.01,
            'DAI/USDT': 0.02, 'BUSD/USDT': 0.01, 'UNI/USDT': 0.08, 'LINK/USDT': 0.08,
            'ADA/USDT': 0.06, 'DOT/USDT': 0.08, 'AVAX/USDT': 0.08, 'TON/USDT': 0.10,
            'MATIC/USDT': 0.08, 'EOS/USDT': 0.08, 'TRX/USDT': 0.08,
            
            # Medium liquidity - medium slippage
            'ATOM/USDT': 0.12, 'XTZ/USDT': 0.12, 'AAVE/USDT': 0.15, 'COMP/USDT': 0.15,
            'BCH/USDT': 0.10, 'FIL/USDT': 0.12, 'XMR/USDT': 0.12, 'MKR/USDT': 0.15,
            
            # Lower liquidity - higher slippage
            'CRV/USDT': 0.20, 'SNX/USDT': 0.20, 'YFI/USDT': 0.25, '1INCH/USDT': 0.20,
            'VET/USDT': 0.15,
            
            # Default for other assets
            'default': 0.15
        }
        
        # Expected daily opportunities by tier (conservative estimates)
        self.daily_opportunities = {
            'tier1': 15,  # Ultra-fast assets - more opportunities
            'tier2': 8,   # Fast assets - moderate opportunities  
            'tier3': 5    # Acceptable assets - fewer opportunities
        }
        
        # Success rates by tier (accounting for market conditions, competition, etc.)
        self.success_rates = {
            'tier1': 0.75,  # 75% success rate for ultra-fast assets
            'tier2': 0.65,  # 65% success rate for fast assets
            'tier3': 0.55   # 55% success rate for acceptable assets
        }
        
    def calculate_daily_profits(self) -> List[ProfitAnalysis]:
        """Calculate expected daily profits for all assets"""
        try:
            analyses = []
            
            # Analyze Tier 1 assets (ultra-fast)
            tier1_analyses = self._analyze_tier(Config.TIER1_ASSETS, 'tier1')
            analyses.extend(tier1_analyses)
            
            # Analyze Tier 2 assets (fast)
            tier2_analyses = self._analyze_tier(Config.TIER2_ASSETS, 'tier2')
            analyses.extend(tier2_analyses)
            
            # Analyze Tier 3 assets (acceptable)
            tier3_analyses = self._analyze_tier(Config.TIER3_ASSETS, 'tier3')
            analyses.extend(tier3_analyses)
            
            return analyses
            
        except Exception as e:
            logger.error(f"Error calculating daily profits: {str(e)}")
            return []
    
    def _analyze_tier(self, assets: List[str], tier: str) -> List[ProfitAnalysis]:
        """Analyze a tier of assets"""
        analyses = []
        
        for asset in assets:
            try:
                analysis = self._analyze_asset(asset, tier)
                if analysis:
                    analyses.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing {asset}: {str(e)}")
                continue
        
        return analyses
    
    def _analyze_asset(self, symbol: str, tier: str) -> Optional[ProfitAnalysis]:
        """Analyze a single asset for profitability"""
        try:
            # Get asset configuration
            transfer_config = Config.TRANSFER_SPEEDS.get(symbol, {})
            position_limit = Config.POSITION_LIMITS.get(symbol, 1000)
            
            # Extract configuration
            min_spread = transfer_config.get('min_spread', 0.008)
            base_currency = symbol.split('/')[0]
            
            # Calculate expected spread (minimum + some buffer)
            avg_spread_percent = min_spread * 1.5  # 50% above minimum for realistic estimate
            
            # Position size (use smaller of position limit and conservative amount)
            position_size_usd = min(position_limit, 2000)  # Conservative $2000 max per trade
            
            # Daily opportunities
            daily_opportunities = self.daily_opportunities[tier]
            
            # Success rate
            success_rate = self.success_rates[tier]
            
            # Calculate costs per trade
            trading_fees = self._calculate_trading_fees(position_size_usd)
            transfer_fees = self.transfer_fees.get(base_currency, 0.01)
            slippage_cost = self._calculate_slippage_cost(position_size_usd, symbol)
            
            # Calculate profits
            gross_profit_per_trade = (position_size_usd * avg_spread_percent)
            net_profit_per_trade = gross_profit_per_trade - trading_fees - transfer_fees - slippage_cost
            
            # Daily calculations
            successful_trades = daily_opportunities * success_rate
            daily_gross_profit = gross_profit_per_trade * successful_trades
            daily_net_profit = net_profit_per_trade * successful_trades
            
            # Risk score (higher = riskier)
            risk_score = self._calculate_risk_score(symbol, tier, transfer_config)
            
            return ProfitAnalysis(
                symbol=symbol,
                tier=tier,
                daily_opportunities=daily_opportunities,
                avg_spread_percent=avg_spread_percent,
                position_size_usd=position_size_usd,
                gross_profit_per_trade=gross_profit_per_trade,
                trading_fees=trading_fees,
                transfer_fees=transfer_fees,
                slippage_cost=slippage_cost,
                net_profit_per_trade=net_profit_per_trade,
                daily_gross_profit=daily_gross_profit,
                daily_net_profit=daily_net_profit,
                success_rate=success_rate,
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing asset {symbol}: {str(e)}")
            return None
    
    def _calculate_trading_fees(self, position_size: float) -> float:
        """Calculate trading fees for both exchanges"""
        try:
            # Use average of maker and taker fees from both exchanges
            binance_avg_fee = (self.trading_fees['binance']['maker'] + self.trading_fees['binance']['taker']) / 2
            kraken_avg_fee = (self.trading_fees['kraken']['maker'] + self.trading_fees['kraken']['taker']) / 2
            
            # Total fees for buy and sell on both exchanges
            total_fee_rate = binance_avg_fee + kraken_avg_fee
            
            return position_size * total_fee_rate
            
        except Exception as e:
            logger.error(f"Error calculating trading fees: {str(e)}")
            return position_size * 0.004  # Default 0.4% total fees
    
    def _calculate_slippage_cost(self, position_size: float, symbol: str) -> float:
        """Calculate slippage cost"""
        try:
            slippage_rate = self.slippage_rates.get(symbol, self.slippage_rates['default'])
            return position_size * (slippage_rate / 100)
            
        except Exception as e:
            logger.error(f"Error calculating slippage cost: {str(e)}")
            return position_size * 0.001  # Default 0.1% slippage
    
    def _calculate_risk_score(self, symbol: str, tier: str, transfer_config: Dict) -> float:
        """Calculate risk score (0-1, higher = riskier)"""
        try:
            risk_factors = []
            
            # Transfer speed risk (faster = lower risk)
            transfer_speed = transfer_config.get('speed', 300)
            if transfer_speed <= 60:
                speed_risk = 0.2
            elif transfer_speed <= 300:
                speed_risk = 0.5
            else:
                speed_risk = 0.8
            risk_factors.append(speed_risk)
            
            # Tier risk
            tier_risks = {'tier1': 0.3, 'tier2': 0.5, 'tier3': 0.7}
            tier_risk = tier_risks.get(tier, 0.5)
            risk_factors.append(tier_risk)
            
            # Liquidity risk (based on position limits)
            position_limit = Config.POSITION_LIMITS.get(symbol, 1000)
            if position_limit >= 5000:
                liquidity_risk = 0.2
            elif position_limit >= 2000:
                liquidity_risk = 0.4
            else:
                liquidity_risk = 0.6
            risk_factors.append(liquidity_risk)
            
            # Calculate average risk
            return sum(risk_factors) / len(risk_factors)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 0.5
    
    def get_profit_summary(self) -> Dict:
        """Get comprehensive profit summary"""
        try:
            analyses = self.calculate_daily_profits()
            
            if not analyses:
                return {}
            
            # Calculate totals by tier
            tier_totals = {'tier1': {'net_profit': 0, 'trades': 0, 'assets': 0},
                          'tier2': {'net_profit': 0, 'trades': 0, 'assets': 0},
                          'tier3': {'net_profit': 0, 'trades': 0, 'assets': 0}}
            
            total_daily_net_profit = 0
            total_daily_gross_profit = 0
            total_trades = 0
            total_assets = len(analyses)
            
            for analysis in analyses:
                tier_totals[analysis.tier]['net_profit'] += analysis.daily_net_profit
                tier_totals[analysis.tier]['trades'] += analysis.daily_opportunities * analysis.success_rate
                tier_totals[analysis.tier]['assets'] += 1
                
                total_daily_net_profit += analysis.daily_net_profit
                total_daily_gross_profit += analysis.daily_gross_profit
                total_trades += analysis.daily_opportunities * analysis.success_rate
            
            # Calculate monthly and yearly projections
            monthly_net_profit = total_daily_net_profit * 30
            yearly_net_profit = total_daily_net_profit * 365
            
            # Calculate average metrics
            avg_success_rate = sum(a.success_rate for a in analyses) / len(analyses)
            avg_risk_score = sum(a.risk_score for a in analyses) / len(analyses)
            avg_position_size = sum(a.position_size_usd for a in analyses) / len(analyses)
            
            # Find best and worst performers
            best_performer = max(analyses, key=lambda x: x.daily_net_profit)
            worst_performer = min(analyses, key=lambda x: x.daily_net_profit)
            
            # Calculate profit margins
            total_costs = total_daily_gross_profit - total_daily_net_profit
            profit_margin = (total_daily_net_profit / total_daily_gross_profit * 100) if total_daily_gross_profit > 0 else 0
            
            summary = {
                'daily_net_profit': total_daily_net_profit,
                'daily_gross_profit': total_daily_gross_profit,
                'monthly_net_profit': monthly_net_profit,
                'yearly_net_profit': yearly_net_profit,
                'total_daily_trades': total_trades,
                'total_assets': total_assets,
                'profit_margin_percent': profit_margin,
                'avg_success_rate': avg_success_rate,
                'avg_risk_score': avg_risk_score,
                'avg_position_size': avg_position_size,
                'tier_breakdown': tier_totals,
                'best_performer': {
                    'symbol': best_performer.symbol,
                    'daily_net_profit': best_performer.daily_net_profit,
                    'tier': best_performer.tier
                },
                'worst_performer': {
                    'symbol': worst_performer.symbol,
                    'daily_net_profit': worst_performer.daily_net_profit,
                    'tier': worst_performer.tier
                },
                'detailed_analyses': analyses
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting profit summary: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on profit analysis"""
        try:
            summary = self.get_profit_summary()
            recommendations = []
            
            if not summary:
                return ["No profit data available for recommendations"]
            
            # Profit margin recommendations
            profit_margin = summary['profit_margin_percent']
            if profit_margin < 50:
                recommendations.append("Low profit margins - consider reducing fees or improving execution")
            elif profit_margin > 80:
                recommendations.append("High profit margins - good opportunity for scaling up")
            
            # Success rate recommendations
            success_rate = summary['avg_success_rate']
            if success_rate < 0.6:
                recommendations.append("Low success rate - consider improving entry criteria")
            elif success_rate > 0.8:
                recommendations.append("High success rate - consider increasing position sizes")
            
            # Risk recommendations
            risk_score = summary['avg_risk_score']
            if risk_score > 0.7:
                recommendations.append("High risk score - consider focusing on lower-risk assets")
            elif risk_score < 0.4:
                recommendations.append("Low risk score - good opportunity for larger positions")
            
            # Tier recommendations
            tier_breakdown = summary['tier_breakdown']
            tier1_profit = tier_breakdown['tier1']['net_profit']
            tier2_profit = tier_breakdown['tier2']['net_profit']
            tier3_profit = tier_breakdown['tier3']['net_profit']
            
            if tier1_profit > tier2_profit + tier3_profit:
                recommendations.append("Tier 1 assets are most profitable - focus on ultra-fast assets")
            elif tier3_profit > tier1_profit:
                recommendations.append("Tier 3 assets showing good returns - consider expanding acceptable assets")
            
            # Best performer recommendations
            best_performer = summary['best_performer']
            recommendations.append(f"Best performer: {best_performer['symbol']} - consider increasing allocation")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return ["Error generating recommendations"]
    
    def print_profit_report(self):
        """Print detailed profit report"""
        try:
            summary = self.get_profit_summary()
            
            if not summary:
                print("No profit data available")
                return
            
            print("=" * 80)
            print("ARBITRAGE BOT PROFIT ANALYSIS REPORT")
            print("=" * 80)
            
            # Overall summary
            print(f"\nOVERALL SUMMARY:")
            print(f"Daily Net Profit: ${summary['daily_net_profit']:.2f}")
            print(f"Daily Gross Profit: ${summary['daily_gross_profit']:.2f}")
            print(f"Monthly Net Profit: ${summary['monthly_net_profit']:.2f}")
            print(f"Yearly Net Profit: ${summary['yearly_net_profit']:.2f}")
            print(f"Profit Margin: {summary['profit_margin_percent']:.1f}%")
            print(f"Total Daily Trades: {summary['total_daily_trades']:.0f}")
            print(f"Total Assets: {summary['total_assets']}")
            print(f"Average Success Rate: {summary['avg_success_rate']:.1%}")
            print(f"Average Risk Score: {summary['avg_risk_score']:.2f}")
            
            # Tier breakdown
            print(f"\nTIER BREAKDOWN:")
            tier_breakdown = summary['tier_breakdown']
            for tier, data in tier_breakdown.items():
                print(f"{tier.upper()}: ${data['net_profit']:.2f} daily profit, {data['trades']:.0f} trades, {data['assets']} assets")
            
            # Top performers
            print(f"\nTOP PERFORMERS:")
            best = summary['best_performer']
            worst = summary['worst_performer']
            print(f"Best: {best['symbol']} (${best['daily_net_profit']:.2f} daily, {best['tier']})")
            print(f"Worst: {worst['symbol']} (${worst['daily_net_profit']:.2f} daily, {worst['tier']})")
            
            # Detailed analysis (top 10)
            print(f"\nDETAILED ANALYSIS (Top 10 Assets):")
            analyses = summary['detailed_analyses']
            sorted_analyses = sorted(analyses, key=lambda x: x.daily_net_profit, reverse=True)
            
            print(f"{'Symbol':<12} {'Tier':<6} {'Net Profit':<12} {'Gross Profit':<13} {'Success Rate':<12} {'Risk Score':<10}")
            print("-" * 80)
            
            for analysis in sorted_analyses[:10]:
                print(f"{analysis.symbol:<12} {analysis.tier:<6} ${analysis.daily_net_profit:<11.2f} "
                      f"${analysis.daily_gross_profit:<12.2f} {analysis.success_rate:<11.1%} {analysis.risk_score:<9.2f}")
            
            # Recommendations
            print(f"\nOPTIMIZATION RECOMMENDATIONS:")
            recommendations = self.get_optimization_recommendations()
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
            
            print("=" * 80)
            
        except Exception as e:
            logger.error(f"Error printing profit report: {str(e)}")
            print(f"Error generating report: {str(e)}")

# Example usage and testing
if __name__ == "__main__":
    calculator = ProfitCalculator()
    calculator.print_profit_report()

