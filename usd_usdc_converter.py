"""
USD to USDC Conversion System
Automatically converts USD to USDC when needed for trading
"""

import logging
import asyncio
from typing import Dict, Optional, Tuple
from coinbase_gemini_exchanges import ExchangeManager

logger = logging.getLogger(__name__)

class USDUSDCConverter:
    """Handles automatic USD to USDC conversion"""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
        self.conversion_fees = {
            'coinbase': 0.0,  # Free conversion on Coinbase
            'gemini': 0.0,    # Free conversion on Gemini
        }
        
    async def check_and_convert_usd_to_usdc(self, exchange_id: str, required_usdc: float) -> bool:
        """
        Check if USD needs to be converted to USDC and perform conversion
        
        Args:
            exchange_id: 'coinbase' or 'gemini'
            required_usdc: Amount of USDC needed
            
        Returns:
            bool: True if conversion was successful or not needed
        """
        try:
            exchange = self.exchange_manager.exchanges[exchange_id]
            
            # Get current balances
            balance = await self._safe_fetch_balance(exchange)
            if not balance:
                logger.error(f"❌ Failed to fetch balance from {exchange_id}")
                return False
                
            usd_balance = self._get_balance_amount(balance, 'USD')
            usdc_balance = self._get_balance_amount(balance, 'USDC')
            
            logger.info(f"💰 {exchange_id} balances: USD=${usd_balance:.2f}, USDC=${usdc_balance:.2f}")
            
            # Check if we have enough USDC
            if usdc_balance >= required_usdc:
                logger.info(f"✅ {exchange_id} has sufficient USDC: ${usdc_balance:.2f} >= ${required_usdc:.2f}")
                return True
                
            # Calculate how much USD to convert
            usd_needed = required_usdc - usdc_balance
            if usd_balance < usd_needed:
                logger.warning(f"⚠️ {exchange_id} insufficient USD: ${usd_balance:.2f} < ${usd_needed:.2f}")
                return False
                
            # Perform conversion
            conversion_amount = min(usd_balance, usd_needed + 1.0)  # Convert a bit extra
            logger.info(f"🔄 Converting ${conversion_amount:.2f} USD to USDC on {exchange_id}")
            
            success = await self._convert_usd_to_usdc(exchange, conversion_amount)
            if success:
                logger.info(f"✅ Successfully converted ${conversion_amount:.2f} USD to USDC on {exchange_id}")
                return True
            else:
                logger.error(f"❌ Failed to convert USD to USDC on {exchange_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in USD to USDC conversion on {exchange_id}: {e}")
            return False
            
    async def _safe_fetch_balance(self, exchange) -> Optional[Dict]:
        """Safely fetch balance with error handling"""
        try:
            balance = exchange.fetch_balance()
            if hasattr(balance, '__await__'):
                balance = await balance
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return None
            
    def _get_balance_amount(self, balance: Dict, currency: str) -> float:
        """Extract balance amount for a currency"""
        try:
            if 'free' in balance and currency in balance['free']:
                return float(balance['free'][currency])
            elif currency in balance:
                return float(balance[currency])
            else:
                return 0.0
        except (KeyError, ValueError, TypeError):
            return 0.0
            
    async def _convert_usd_to_usdc(self, exchange, amount: float) -> bool:
        """
        Convert USD to USDC on the exchange
        
        Args:
            exchange: Exchange instance
            amount: Amount of USD to convert
            
        Returns:
            bool: True if conversion successful
        """
        try:
            # For Coinbase, we can use a market buy order for USD/USDC
            if exchange.id == 'coinbase':
                return await self._coinbase_usd_to_usdc(exchange, amount)
            elif exchange.id == 'gemini':
                return await self._gemini_usd_to_usdc(exchange, amount)
            else:
                logger.error(f"❌ Unknown exchange for conversion: {exchange.id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in USD to USDC conversion: {e}")
            return False
            
    async def _coinbase_usd_to_usdc(self, exchange, amount: float) -> bool:
        """Convert USD to USDC on Coinbase"""
        try:
            # Get current USD/USDC price
            ticker = exchange.fetch_ticker('USD/USDC')
            if hasattr(ticker, '__await__'):
                ticker = await ticker
                
            price = float(ticker['last'])
            usdc_amount = amount / price
            
            # Create market buy order (buy USDC with USD)
            order = exchange.create_market_buy_order('USD/USDC', usdc_amount)
            if hasattr(order, '__await__'):
                order = await order
                
            logger.info(f"✅ Coinbase USD to USDC conversion: {amount} USD -> {usdc_amount:.6f} USDC @ {price}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Coinbase USD to USDC conversion failed: {e}")
            return False
            
    async def _gemini_usd_to_usdc(self, exchange, amount: float) -> bool:
        """Convert USD to USDC on Gemini"""
        try:
            # Gemini might not have USD/USDC pair, so we'll use a different approach
            # For now, we'll try to create a market buy order for USDC using USD
            # This might need to be adjusted based on Gemini's actual API
            
            # Get current USDC price in USD (should be ~1.00)
            ticker = exchange.fetch_ticker('USDC/USD')
            if hasattr(ticker, '__await__'):
                ticker = await ticker
                
            price = float(ticker['last'])
            usdc_amount = amount / price
            
            # Create market buy order
            order = exchange.create_market_buy_order('USDC/USD', usdc_amount)
            if hasattr(order, '__await__'):
                order = await order
                
            logger.info(f"✅ Gemini USD to USDC conversion: {amount} USD -> {usdc_amount:.6f} USDC @ {price}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Gemini USD to USDC conversion failed: {e}")
            # Fallback: try alternative approach
            return await self._gemini_usd_to_usdc_fallback(exchange, amount)
            
    async def _gemini_usd_to_usdc_fallback(self, exchange, amount: float) -> bool:
        """Fallback method for Gemini USD to USDC conversion"""
        try:
            # If direct conversion fails, we might need to use a different approach
            # For now, we'll log this and return False
            logger.warning(f"⚠️ Gemini USD to USDC conversion not implemented, skipping conversion of ${amount}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Gemini USD to USDC fallback failed: {e}")
            return False
            
    async def ensure_usdc_balance(self, exchange_id: str, required_usdc: float) -> bool:
        """
        Ensure sufficient USDC balance for trading
        
        Args:
            exchange_id: 'coinbase' or 'gemini'
            required_usdc: Amount of USDC needed
            
        Returns:
            bool: True if sufficient USDC is available
        """
        try:
            exchange = self.exchange_manager.exchanges[exchange_id]
            
            # Get current USDC balance
            balance = await self._safe_fetch_balance(exchange)
            if not balance:
                return False
                
            usdc_balance = self._get_balance_amount(balance, 'USDC')
            
            if usdc_balance >= required_usdc:
                return True
                
            # Try to convert USD to USDC
            return await self.check_and_convert_usd_to_usdc(exchange_id, required_usdc)
            
        except Exception as e:
            logger.error(f"❌ Error ensuring USDC balance on {exchange_id}: {e}")
            return False
            
    async def get_available_usdc(self, exchange_id: str) -> float:
        """Get available USDC balance on exchange"""
        try:
            exchange = self.exchange_manager.exchanges[exchange_id]
            balance = await self._safe_fetch_balance(exchange)
            if not balance:
                return 0.0
                
            return self._get_balance_amount(balance, 'USDC')
            
        except Exception as e:
            logger.error(f"❌ Error getting USDC balance from {exchange_id}: {e}")
            return 0.0
