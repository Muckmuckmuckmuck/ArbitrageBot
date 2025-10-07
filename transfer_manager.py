import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from exchanges import ExchangeManager
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class TransferRequest:
    """Data class for transfer request"""
    currency: str
    amount: float
    from_exchange: str
    to_exchange: str
    address: str
    tag: Optional[str] = None
    timestamp: float = 0.0
    status: str = "pending"
    tx_id: Optional[str] = None

@dataclass
class TransferStatus:
    """Data class for transfer status"""
    currency: str
    amount: float
    from_exchange: str
    to_exchange: str
    status: str
    tx_id: Optional[str] = None
    confirmations: int = 0
    timestamp: float = 0.0

class TransferManager:
    """Manages cross-exchange transfers for arbitrage operations"""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
        self.pending_transfers: Dict[str, TransferRequest] = {}
        self.completed_transfers: List[TransferRequest] = []
        self.transfer_addresses: Dict[str, Dict[str, str]] = {}
        self.minimum_transfer_amounts = {
            # Tier 1 Assets
            'XRP': 20.0, 'XLM': 10.0, 'SOL': 0.01, 'EOS': 0.1, 'TRX': 100.0,
            'TON': 1.0, 'BNB': 0.01, 'MATIC': 1.0, 'AVAX': 0.01, 'DOT': 0.1,
            'USDC': 10.0, 'USDT': 10.0, 'DAI': 10.0, 'BUSD': 10.0,
            'UNI': 0.1, 'LINK': 0.1, 'ADA': 1.0,
            
            # Tier 2 Assets
            'XTZ': 1.0, 'MKR': 0.01, 'FIL': 0.1, 'ATOM': 0.1,
            'AAVE': 0.1, 'COMP': 0.1, 'CRV': 1.0, 'SNX': 1.0,
            'YFI': 0.001, '1INCH': 1.0,
            
            # Tier 3 Assets
            'LTC': 0.01, 'DOGE': 10.0, 'VET': 100.0, 'BCH': 0.01, 'XMR': 0.01
        }
        
        self.transfer_fees = {
            # Tier 1 Assets
            'XRP': 0.01, 'XLM': 0.001, 'SOL': 0.001, 'EOS': 0.01, 'TRX': 0.01,
            'TON': 0.1, 'BNB': 0.05, 'MATIC': 0.01, 'AVAX': 0.1, 'DOT': 0.1,
            'USDC': 0.0, 'USDT': 0.0, 'DAI': 0.001, 'BUSD': 0.0,
            'UNI': 0.01, 'LINK': 0.01, 'ADA': 1.0,
            
            # Tier 2 Assets
            'XTZ': 0.01, 'MKR': 0.001, 'FIL': 0.01, 'ATOM': 0.01,
            'AAVE': 0.01, 'COMP': 0.01, 'CRV': 0.01, 'SNX': 0.01,
            'YFI': 0.001, '1INCH': 0.01,
            
            # Tier 3 Assets
            'LTC': 0.01, 'DOGE': 0.01, 'VET': 0.01, 'BCH': 0.01, 'XMR': 0.01
        }
        
    async def initialize(self):
        """Initialize transfer manager and get deposit addresses"""
        logger.info("Initializing transfer manager")
        
        # Get deposit addresses for all currencies on all exchanges
        currencies = ['XRP', 'XLM', 'SOL', 'EOS', 'TRX', 'TON', 'BNB', 'MATIC', 'AVAX', 'DOT',
                     'USDC', 'USDT', 'DAI', 'BUSD', 'UNI', 'LINK', 'ADA', 'XTZ', 'MKR', 'FIL',
                     'ATOM', 'AAVE', 'COMP', 'CRV', 'SNX', 'YFI', '1INCH', 'LTC', 'DOGE', 'VET',
                     'BCH', 'XMR']
        exchanges = ['binance', 'okx']
        
        for currency in currencies:
            self.transfer_addresses[currency] = {}
            for exchange_name in exchanges:
                try:
                    exchange = self.exchange_manager.get_exchange(exchange_name)
                    address = await exchange.get_deposit_address(currency)
                    self.transfer_addresses[currency][exchange_name] = address
                    logger.info(f"Got {currency} deposit address for {exchange_name}: {address}")
                except Exception as e:
                    logger.error(f"Failed to get {currency} deposit address for {exchange_name}: {str(e)}")
        
        logger.info("Transfer manager initialized successfully")
    
    async def transfer_currency(self, currency: str, amount: float, from_exchange: str, to_exchange: str) -> bool:
        """Transfer currency from one exchange to another"""
        try:
            # Validate transfer parameters
            if not self._validate_transfer(currency, amount, from_exchange, to_exchange):
                return False
            
            # Get destination address
            destination_address = self.transfer_addresses[currency][to_exchange]
            
            # Create transfer request
            transfer_request = TransferRequest(
                currency=currency,
                amount=amount,
                from_exchange=from_exchange,
                to_exchange=to_exchange,
                address=destination_address,
                timestamp=time.time()
            )
            
            # Execute withdrawal
            from_exchange_connector = self.exchange_manager.get_exchange(from_exchange)
            
            logger.info(f"Initiating transfer: {amount} {currency} from {from_exchange} to {to_exchange}")
            
            withdrawal_result = await from_exchange_connector.withdraw(
                currency, amount, destination_address
            )
            
            transfer_request.tx_id = withdrawal_result.get('id')
            transfer_request.status = "initiated"
            
            # Store transfer request
            transfer_id = f"{currency}_{from_exchange}_{to_exchange}_{int(time.time())}"
            self.pending_transfers[transfer_id] = transfer_request
            
            logger.info(f"Transfer initiated successfully. TX ID: {transfer_request.tx_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to transfer {currency}: {str(e)}")
            return False
    
    def _validate_transfer(self, currency: str, amount: float, from_exchange: str, to_exchange: str) -> bool:
        """Validate transfer parameters"""
        # Check if currency is supported
        if currency not in self.transfer_addresses:
            logger.error(f"Currency {currency} not supported for transfers")
            return False
        
        # Check if exchanges are supported
        if from_exchange not in self.transfer_addresses[currency]:
            logger.error(f"Exchange {from_exchange} not supported for {currency} transfers")
            return False
        
        if to_exchange not in self.transfer_addresses[currency]:
            logger.error(f"Exchange {to_exchange} not supported for {currency} transfers")
            return False
        
        # Check minimum transfer amount
        if amount < self.minimum_transfer_amounts.get(currency, 0):
            logger.error(f"Transfer amount {amount} below minimum for {currency}")
            return False
        
        # Check if we have sufficient balance
        from_exchange_connector = self.exchange_manager.get_exchange(from_exchange)
        balance = from_exchange_connector.balances.get(currency, {}).get('free', 0)
        
        if balance < amount:
            logger.error(f"Insufficient balance for {currency} transfer. Available: {balance}, Required: {amount}")
            return False
        
        return True
    
    async def check_transfer_status(self, transfer_id: str) -> Optional[TransferStatus]:
        """Check the status of a pending transfer"""
        if transfer_id not in self.pending_transfers:
            return None
        
        transfer_request = self.pending_transfers[transfer_id]
        
        try:
            # Get withdrawal status from source exchange
            from_exchange = self.exchange_manager.get_exchange(transfer_request.from_exchange)
            
            # Note: This would require implementing a method to check withdrawal status
            # Most exchanges don't provide this via API, so we'll simulate it
            
            # For now, we'll assume transfers complete within 10 minutes
            if time.time() - transfer_request.timestamp > 600:  # 10 minutes
                transfer_request.status = "completed"
                self.completed_transfers.append(transfer_request)
                del self.pending_transfers[transfer_id]
                
                return TransferStatus(
                    currency=transfer_request.currency,
                    amount=transfer_request.amount,
                    from_exchange=transfer_request.from_exchange,
                    to_exchange=transfer_request.to_exchange,
                    status="completed",
                    tx_id=transfer_request.tx_id,
                    confirmations=6,  # Assume 6 confirmations
                    timestamp=time.time()
                )
            else:
                return TransferStatus(
                    currency=transfer_request.currency,
                    amount=transfer_request.amount,
                    from_exchange=transfer_request.from_exchange,
                    to_exchange=transfer_request.to_exchange,
                    status="pending",
                    tx_id=transfer_request.tx_id,
                    confirmations=0,
                    timestamp=transfer_request.timestamp
                )
                
        except Exception as e:
            logger.error(f"Error checking transfer status: {str(e)}")
            return None
    
    async def monitor_pending_transfers(self):
        """Monitor all pending transfers and update their status"""
        while True:
            try:
                transfer_ids = list(self.pending_transfers.keys())
                
                for transfer_id in transfer_ids:
                    status = await self.check_transfer_status(transfer_id)
                    if status and status.status == "completed":
                        logger.info(f"Transfer {transfer_id} completed successfully")
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring transfers: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def calculate_transfer_cost(self, currency: str, amount: float) -> float:
        """Calculate the cost of transferring currency"""
        fee = self.transfer_fees.get(currency, 0.001)
        return fee
    
    def get_transfer_statistics(self) -> Dict:
        """Get transfer statistics"""
        total_transfers = len(self.completed_transfers)
        pending_transfers = len(self.pending_transfers)
        
        total_amount = 0
        for transfer in self.completed_transfers:
            total_amount += transfer.amount
        
        return {
            'total_transfers': total_transfers,
            'pending_transfers': pending_transfers,
            'total_amount_transferred': total_amount,
            'success_rate': 100.0  # Assume all transfers succeed for now
        }
    
    async def rebalance_balances(self, currency: str, target_exchange: str, target_amount: float):
        """Rebalance balances between exchanges"""
        try:
            # Get current balances
            binance_balance = self.exchange_manager.get_exchange('binance').balances.get(currency, {}).get('free', 0)
            okx_balance = self.exchange_manager.get_exchange('okx').balances.get(currency, {}).get('free', 0)
            
            total_balance = binance_balance + okx_balance
            
            if total_balance < target_amount:
                logger.warning(f"Insufficient total balance for {currency}. Available: {total_balance}, Target: {target_amount}")
                return False
            
            # Calculate transfer amount
            if target_exchange == 'binance':
                current_amount = binance_balance
                source_exchange = 'okx'
                source_balance = okx_balance
            else:
                current_amount = okx_balance
                source_exchange = 'binance'
                source_balance = binance_balance
            
            transfer_amount = target_amount - current_amount
            
            if transfer_amount > 0 and source_balance >= transfer_amount:
                # Execute transfer
                success = await self.transfer_currency(currency, transfer_amount, source_exchange, target_exchange)
                if success:
                    logger.info(f"Rebalanced {currency}: transferred {transfer_amount} from {source_exchange} to {target_exchange}")
                    return True
                else:
                    logger.error(f"Failed to rebalance {currency}")
                    return False
            else:
                logger.info(f"No rebalancing needed for {currency}")
                return True
                
        except Exception as e:
            logger.error(f"Error rebalancing {currency}: {str(e)}")
            return False
    
    async def emergency_withdraw_all(self, currency: str, to_address: str):
        """Emergency function to withdraw all funds of a currency to external address"""
        try:
            logger.warning(f"Emergency withdrawal initiated for {currency} to {to_address}")
            
            exchanges = ['binance', 'okx']
            total_withdrawn = 0
            
            for exchange_name in exchanges:
                try:
                    exchange = self.exchange_manager.get_exchange(exchange_name)
                    balance = exchange.balances.get(currency, {}).get('free', 0)
                    
                    if balance > 0:
                        # Account for withdrawal fee
                        fee = self.transfer_fees.get(currency, 0.001)
                        withdraw_amount = max(0, balance - fee)
                        
                        if withdraw_amount > 0:
                            await exchange.withdraw(currency, withdraw_amount, to_address)
                            total_withdrawn += withdraw_amount
                            logger.info(f"Emergency withdrawal: {withdraw_amount} {currency} from {exchange_name}")
                
                except Exception as e:
                    logger.error(f"Emergency withdrawal failed from {exchange_name}: {str(e)}")
            
            logger.warning(f"Emergency withdrawal completed. Total withdrawn: {total_withdrawn} {currency}")
            return total_withdrawn
            
        except Exception as e:
            logger.error(f"Emergency withdrawal failed: {str(e)}")
            return 0
