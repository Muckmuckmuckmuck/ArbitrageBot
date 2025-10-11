#!/usr/bin/env python3
"""
Transfer Manager - Automated Cross-Exchange Transfers
Handles crypto and stablecoin transfers between Pionex.US and Coinbase Pro
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TransferResult:
    """Result of a transfer operation"""
    success: bool
    from_exchange: str
    to_exchange: str
    currency: str
    amount: float
    tx_id: Optional[str] = None
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def duration_seconds(self) -> float:
        """Calculate transfer duration"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

class TransferManager:
    """Manages automated transfers between exchanges"""
    
    def __init__(self, exchanges: Dict[str, Any], config: Any):
        """Initialize transfer manager"""
        self.exchanges = exchanges
        self.config = config
        
        # Track pending transfers
        self.pending_transfers = []
        
        # Deposit addresses cache
        self.deposit_addresses = {}
        
        # Transfer statistics
        self.stats = {
            'total_transfers': 0,
            'successful_transfers': 0,
            'failed_transfers': 0,
            'total_transfer_time': 0.0,
            'by_currency': {},
        }
        
        logger.info("Transfer Manager initialized")
    
    async def get_deposit_address(self, exchange_name: str, currency: str) -> str:
        """Get deposit address for a currency on an exchange"""
        
        # Check cache first
        cache_key = f"{exchange_name}:{currency}"
        if cache_key in self.deposit_addresses:
            return self.deposit_addresses[cache_key]
        
        try:
            exchange = self.exchanges[exchange_name]
            
            # Fetch deposit address
            address_info = await exchange.fetch_deposit_address(currency)
            
            if 'address' in address_info:
                address = address_info['address']
                tag = address_info.get('tag', None)
                
                # Cache the address
                self.deposit_addresses[cache_key] = address
                
                logger.info(f"Got deposit address for {currency} on {exchange_name}: {address[:10]}...")
                if tag:
                    logger.info(f"  Memo/Tag: {tag}")
                
                return address
            else:
                raise ValueError(f"No address returned for {currency} on {exchange_name}")
                
        except Exception as e:
            logger.error(f"Error getting deposit address for {currency} on {exchange_name}: {e}")
            raise
    
    async def transfer_crypto(self, from_exchange: str, to_exchange: str, 
                             currency: str, amount: float) -> TransferResult:
        """Transfer cryptocurrency from one exchange to another"""
        
        started_at = datetime.now()
        
        try:
            logger.info(f"Starting transfer: {amount} {currency} from {from_exchange} → {to_exchange}")
            
            # Get deposit address on destination exchange
            deposit_address = await self.get_deposit_address(to_exchange, currency)
            
            # Get tag/memo if needed
            address_info = await self.exchanges[to_exchange].fetch_deposit_address(currency)
            tag = address_info.get('tag', None)
            
            # Execute withdrawal from source exchange
            logger.info(f"Withdrawing {amount} {currency} from {from_exchange}...")
            
            withdrawal_params = {
                'address': deposit_address,
            }
            
            if tag:
                withdrawal_params['tag'] = tag
            
            withdrawal = await self.exchanges[from_exchange].withdraw(
                currency,
                amount,
                deposit_address,
                tag,
                withdrawal_params
            )
            
            tx_id = withdrawal.get('id', withdrawal.get('txid', None))
            logger.info(f"Withdrawal initiated: {tx_id}")
            
            # Track pending transfer
            transfer = TransferResult(
                success=False,  # Not confirmed yet
                from_exchange=from_exchange,
                to_exchange=to_exchange,
                currency=currency,
                amount=amount,
                tx_id=tx_id,
                status='pending',
                started_at=started_at
            )
            self.pending_transfers.append(transfer)
            
            # Wait for deposit to be confirmed
            logger.info(f"Waiting for {currency} deposit on {to_exchange}...")
            confirmed = await self._wait_for_deposit(
                to_exchange, currency, amount, tx_id, 
                max_wait_seconds=300  # 5 minute timeout
            )
            
            completed_at = datetime.now()
            
            if confirmed:
                transfer.success = True
                transfer.status = 'completed'
                transfer.completed_at = completed_at
                
                duration = transfer.duration_seconds()
                
                logger.info(f"✅ Transfer completed in {duration:.1f}s: "
                          f"{amount} {currency} from {from_exchange} → {to_exchange}")
                
                # Update statistics
                self.stats['total_transfers'] += 1
                self.stats['successful_transfers'] += 1
                self.stats['total_transfer_time'] += duration
                
                if currency not in self.stats['by_currency']:
                    self.stats['by_currency'][currency] = {
                        'count': 0,
                        'total_time': 0.0,
                        'avg_time': 0.0
                    }
                
                self.stats['by_currency'][currency]['count'] += 1
                self.stats['by_currency'][currency]['total_time'] += duration
                self.stats['by_currency'][currency]['avg_time'] = \
                    self.stats['by_currency'][currency]['total_time'] / \
                    self.stats['by_currency'][currency]['count']
                
                return transfer
            else:
                transfer.success = False
                transfer.status = 'failed'
                transfer.error_message = 'Deposit not confirmed within timeout'
                transfer.completed_at = completed_at
                
                logger.error(f"❌ Transfer failed: {currency} from {from_exchange} → {to_exchange}")
                
                self.stats['total_transfers'] += 1
                self.stats['failed_transfers'] += 1
                
                return transfer
                
        except Exception as e:
            logger.error(f"Error during transfer: {e}", exc_info=True)
            
            self.stats['total_transfers'] += 1
            self.stats['failed_transfers'] += 1
            
            return TransferResult(
                success=False,
                from_exchange=from_exchange,
                to_exchange=to_exchange,
                currency=currency,
                amount=amount,
                status='error',
                started_at=started_at,
                completed_at=datetime.now(),
                error_message=str(e)
            )
    
    async def _wait_for_deposit(self, exchange_name: str, currency: str, 
                               expected_amount: float, tx_id: Optional[str],
                               max_wait_seconds: int = 300) -> bool:
        """Wait for a deposit to be confirmed"""
        
        start_time = datetime.now()
        check_interval = 5  # Check every 5 seconds
        
        # Get initial balance
        initial_balance = await self._get_balance(exchange_name, currency)
        
        logger.info(f"Waiting for {expected_amount} {currency} on {exchange_name} "
                   f"(initial: {initial_balance:.8f})")
        
        while True:
            # Check if timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > max_wait_seconds:
                logger.error(f"Timeout waiting for deposit ({elapsed:.0f}s > {max_wait_seconds}s)")
                return False
            
            # Check current balance
            current_balance = await self._get_balance(exchange_name, currency)
            
            # Check if deposit received (with 1% tolerance for fees)
            received_amount = current_balance - initial_balance
            
            if received_amount >= expected_amount * 0.99:
                logger.info(f"✅ Deposit confirmed: {received_amount:.8f} {currency} "
                          f"(expected: {expected_amount:.8f})")
                return True
            
            # Log progress
            if received_amount > 0:
                logger.info(f"Partial deposit: {received_amount:.8f}/{expected_amount:.8f} {currency}")
            
            # Wait before checking again
            await asyncio.sleep(check_interval)
    
    async def _get_balance(self, exchange_name: str, currency: str) -> float:
        """Get balance of a currency on an exchange"""
        try:
            exchange = self.exchanges[exchange_name]
            balance = await exchange.fetch_balance()
            
            # Get free (available) balance
            free_balance = balance.get(currency, {}).get('free', 0.0)
            
            return float(free_balance)
            
        except Exception as e:
            logger.error(f"Error fetching balance for {currency} on {exchange_name}: {e}")
            return 0.0
    
    async def rebalance_account(self, from_exchange: str, to_exchange: str,
                               min_rebalance_usd: float = 100.0) -> Optional[TransferResult]:
        """Rebalance USDT between exchanges if needed"""
        
        try:
            # Check USDT balances on both exchanges
            from_usdt = await self._get_balance(from_exchange, 'USDT')
            to_usdt = await self._get_balance(to_exchange, 'USDT')
            
            total_usdt = from_usdt + to_usdt
            target_per_exchange = total_usdt / 2
            
            # Check if rebalancing needed
            imbalance = abs(from_usdt - target_per_exchange)
            
            if imbalance < min_rebalance_usd:
                logger.info(f"Rebalancing not needed: imbalance ${imbalance:.2f} < ${min_rebalance_usd}")
                return None
            
            # Determine transfer direction
            if from_usdt > to_usdt:
                # Transfer from → to
                transfer_amount = imbalance
                
                logger.info(f"Rebalancing: Transfer ${transfer_amount:.2f} USDT "
                          f"from {from_exchange} → {to_exchange}")
                
                return await self.transfer_crypto(from_exchange, to_exchange, 'USDT', transfer_amount)
            else:
                # Transfer to → from
                transfer_amount = imbalance
                
                logger.info(f"Rebalancing: Transfer ${transfer_amount:.2f} USDT "
                          f"from {to_exchange} → {from_exchange}")
                
                return await self.transfer_crypto(to_exchange, from_exchange, 'USDT', transfer_amount)
                
        except Exception as e:
            logger.error(f"Error during rebalancing: {e}", exc_info=True)
            return None
    
    def get_transfer_statistics(self) -> Dict[str, Any]:
        """Get transfer statistics"""
        
        avg_time = 0.0
        if self.stats['successful_transfers'] > 0:
            avg_time = self.stats['total_transfer_time'] / self.stats['successful_transfers']
        
        return {
            'total_transfers': self.stats['total_transfers'],
            'successful': self.stats['successful_transfers'],
            'failed': self.stats['failed_transfers'],
            'success_rate': self.stats['successful_transfers'] / self.stats['total_transfers'] 
                           if self.stats['total_transfers'] > 0 else 0,
            'avg_transfer_time_seconds': avg_time,
            'by_currency': self.stats['by_currency']
        }
    
    def get_pending_transfers(self) -> list:
        """Get list of pending transfers"""
        return [t for t in self.pending_transfers if t.status == 'pending']
    
    def clear_completed_transfers(self):
        """Clear completed transfers from pending list"""
        self.pending_transfers = [t for t in self.pending_transfers 
                                 if t.status == 'pending']
        logger.info(f"Cleared completed transfers. {len(self.pending_transfers)} pending remaining")

