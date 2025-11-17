# 🔍 UNDERCUT DETECTION & ADAPTIVE QUOTING - IMPLEMENTATION GUIDE

## Date: 2025-01-27
## Purpose: Specific implementation for detecting when we get undercut and adjusting prices dynamically

---

## 🎯 PROBLEM STATEMENT

**Current Issue:**
- Our ask order is at $100.01
- Competitor places ask at $100.00 (undercuts us)
- Our order won't fill until theirs fills first
- We don't detect this for 400ms (polling interval)
- By the time we detect, opportunity might be gone

**Solution:**
- Detect undercuts in real-time (< 10ms)
- Automatically adjust price to beat competitor
- Ensure we stay competitive while maintaining profitability

---

## 📋 IMPLEMENTATION PLAN

### **STEP 1: Add Undercut Detection to MarketDataPoller**

```python
# File: scalper/market_data.py

class OrderBookSnapshot:
    # ... existing code ...
    
    def is_undercut(self, our_price: Decimal, side: str) -> Tuple[bool, Optional[Decimal]]:
        """
        Check if our price is undercut by the order book.
        Returns: (is_undercut, competitor_price)
        """
        if side == "sell":
            # For sell orders, we're undercut if best_ask < our_price
            if self.best_ask > 0 and self.best_ask < our_price:
                return True, self.best_ask
        elif side == "buy":
            # For buy orders, we're undercut if best_bid > our_price
            if self.best_bid > 0 and self.best_bid > our_price:
                return True, self.best_bid
        return False, None
    
    def get_queue_position(self, our_price: Decimal, side: str) -> int:
        """
        Get our position in the order book queue.
        Returns: 1 = first in queue, 2 = second, etc.
        """
        if side == "sell":
            # Count how many asks are better (lower price) than ours
            better = sum(1 for price, _ in self.asks if price < our_price)
            return better + 1
        else:  # buy
            # Count how many bids are better (higher price) than ours
            better = sum(1 for price, _ in self.bids if price > our_price)
            return better + 1
```

---

### **STEP 2: Add Undercut Detection to ExecutionManager**

```python
# File: scalper/execution.py

class ExecutionManager:
    # ... existing code ...
    
    async def check_undercuts(self, snapshot: Optional[OrderBookSnapshot]) -> List[Dict]:
        """
        Check all our quote orders for undercuts.
        Returns list of orders that need repricing.
        """
        if not snapshot:
            return []
        
        undercut_orders = []
        async with self._lock:
            for order_id, meta in list(self._quote_orders.items()):
                side = str(meta.get("side", "")).lower()
                our_price = Decimal(str(meta.get("price", 0)))
                
                if our_price <= 0:
                    continue
                
                is_undercut, competitor_price = snapshot.is_undercut(our_price, side)
                if is_undercut and competitor_price:
                    queue_position = snapshot.get_queue_position(our_price, side)
                    
                    # Only reprice if we're not first in queue
                    # (If we're first, we're competitive, no need to reprice)
                    if queue_position > 1:
                        undercut_orders.append({
                            "order_id": order_id,
                            "side": side,
                            "our_price": our_price,
                            "competitor_price": competitor_price,
                            "queue_position": queue_position,
                            "meta": meta,
                        })
        
        return undercut_orders
    
    async def reprice_undercut_order(
        self,
        order_id: str,
        side: str,
        competitor_price: Decimal,
        min_profitable_price: Optional[Decimal] = None,
        max_profitable_price: Optional[Decimal] = None,
    ) -> Optional[str]:
        """
        Reprice an order that was undercut.
        Adjusts to beat competitor by 1 tick while staying profitable.
        """
        # Get tick size (minimum price increment)
        tick_size = self._get_tick_size()
        if tick_size is None:
            tick_size = Decimal("0.01")  # Default fallback
        
        # Calculate new price to beat competitor
        if side == "sell":
            # Beat competitor by 1 tick (lower price)
            new_price = competitor_price - tick_size
            
            # Ensure we're still profitable
            if min_profitable_price and new_price < min_profitable_price:
                # Can't beat competitor profitably, cancel order
                logger.warning(
                    "[UNDERCUT] %s %s sell order %s can't beat competitor %s profitably (min=%s), canceling",
                    self._symbol,
                    order_id,
                    competitor_price,
                    new_price,
                    min_profitable_price,
                )
                await self._cancel_orders([order_id])
                self._quote_orders.pop(order_id, None)
                return None
        else:  # buy
            # Beat competitor by 1 tick (higher price)
            new_price = competitor_price + tick_size
            
            # Ensure we're still profitable
            if max_profitable_price and new_price > max_profitable_price:
                # Can't beat competitor profitably, cancel order
                logger.warning(
                    "[UNDERCUT] %s %s buy order %s can't beat competitor %s profitably (max=%s), canceling",
                    self._symbol,
                    order_id,
                    competitor_price,
                    new_price,
                    max_profitable_price,
                )
                await self._cancel_orders([order_id])
                self._quote_orders.pop(order_id, None)
                return None
        
        # Get current order amount
        meta = self._quote_orders.get(order_id)
        if not meta:
            return None
        
        amount = Decimal(str(meta.get("amount", 0)))
        if amount <= 0:
            return None
        
        # Cancel old order and place new one
        try:
            await self._cancel_orders([order_id])
            self._quote_orders.pop(order_id, None)
            
            # Place new order at better price
            new_order_id = await self._submit(
                side,
                amount,
                new_price,
                tag="quote",
            )
            
            if new_order_id:
                logger.info(
                    "[UNDERCUT] %s %s %s order repriced from %s to %s (competitor=%s, queue_pos=%s)",
                    self._symbol,
                    order_id,
                    side.upper(),
                    meta.get("price"),
                    new_price,
                    competitor_price,
                    snapshot.get_queue_position(our_price, side) if snapshot else "?",
                )
            
            return new_order_id
        except Exception as exc:
            logger.error(
                "[UNDERCUT] Failed to reprice %s %s %s: %s",
                self._symbol,
                order_id,
                side,
                exc,
                exc_info=True,
            )
            return None
    
    def _get_tick_size(self) -> Optional[Decimal]:
        """Get the minimum price increment (tick size) for this symbol."""
        try:
            market = self._client._client.market(self._symbol)
            if market:
                # Try to get tick size from market info
                tick_size = market.get("precision", {}).get("price")
                if tick_size:
                    return Decimal(str(tick_size))
                # Fallback: use price precision
                price_precision = market.get("precision", {}).get("price")
                if price_precision:
                    return Decimal("10") ** (-price_precision)
        except Exception:
            pass
        return None
```

---

### **STEP 3: Integrate Undercut Detection into Runner**

```python
# File: scalper/runner.py

async def _run_pair(self, pair_key: str) -> None:
    # ... existing code ...
    
    try:
        while self._running:
            # ... existing code ...
            
            # NEW: Check for undercuts before planning new quotes
            snapshot = poller.latest()
            if snapshot:
                undercut_orders = await execution.check_undercuts(snapshot)
                if undercut_orders:
                    # Calculate min/max profitable prices for each order
                    for undercut_info in undercut_orders:
                        order_id = undercut_info["order_id"]
                        side = undercut_info["side"]
                        competitor_price = undercut_info["competitor_price"]
                        meta = undercut_info["meta"]
                        
                        # Calculate profitable price range
                        # For sell: min_price = entry_price + fees + buffer
                        # For buy: max_price = entry_price - fees - buffer
                        min_profitable_price = None
                        max_profitable_price = None
                        
                        if side == "sell":
                            # If this is a hedge protecting a buy fill, use min_price
                            if "min_price" in meta:
                                min_profitable_price = Decimal(str(meta["min_price"]))
                            else:
                                # Calculate from current market and fees
                                # min_price = best_bid * (1 + fees + buffer)
                                fee_bps = Decimal(pair.maker_fee_bps)
                                buffer_bps = Decimal(self._config.settings.hedge_buffer_bps)
                                total_bps = fee_bps + buffer_bps
                                min_profitable_price = snapshot.best_bid * (
                                    Decimal("1") + total_bps / Decimal("10000")
                                )
                        else:  # buy
                            # Calculate max_price from current market and fees
                            fee_bps = Decimal(pair.maker_fee_bps)
                            buffer_bps = Decimal(self._config.settings.hedge_buffer_bps)
                            total_bps = fee_bps + buffer_bps
                            max_profitable_price = snapshot.best_ask * (
                                Decimal("1") - total_bps / Decimal("10000")
                            )
                        
                        # Reprice the order
                        await execution.reprice_undercut_order(
                            order_id,
                            side,
                            competitor_price,
                            min_profitable_price,
                            max_profitable_price,
                        )
            
            # ... rest of existing code ...
```

---

### **STEP 4: Add Real-Time Monitoring (WebSocket - Future)**

```python
# File: scalper/market_data.py (Future WebSocket Implementation)

class WebSocketMarketDataPoller:
    """WebSocket-based market data for real-time undercut detection."""
    
    async def _on_order_book_update(self, update: Dict):
        """
        Called when order book updates via WebSocket.
        Check for undercuts immediately.
        """
        snapshot = self._parse_order_book_update(update)
        if snapshot:
            self._latest_book = snapshot
            
            # Immediately check for undercuts
            # This happens in < 10ms instead of 400ms!
            await self._check_undercuts_immediately(snapshot)
    
    async def _check_undercuts_immediately(self, snapshot: OrderBookSnapshot):
        """
        Check for undercuts immediately when order book updates.
        This is called from WebSocket callback, so it's real-time.
        """
        # This would need access to ExecutionManager
        # Could be done via callback or shared state
        pass
```

---

### **STEP 5: Add Adaptive Aggressiveness**

```python
# File: scalper/strategy.py

class QuotePlanner:
    # ... existing code ...
    
    def _calculate_aggressiveness(
        self,
        state: PairRuntimeState,
        net_edge_bps: Decimal,
        settings: EngineSettings,
    ) -> Decimal:
        """
        Calculate how aggressive to be with price improvement.
        Returns multiplier (1.0 = normal, >1.0 = more aggressive, <1.0 = less aggressive)
        """
        base_aggressiveness = Decimal("1.0")
        
        # More aggressive if high win rate
        if state.fill_count > 10:
            win_rate = Decimal(state.win_count) / Decimal(state.fill_count)
            if win_rate > Decimal("0.7"):
                base_aggressiveness *= Decimal("1.2")  # 20% more aggressive
            elif win_rate < Decimal("0.4"):
                base_aggressiveness *= Decimal("0.8")  # 20% less aggressive
        
        # More aggressive if high edge
        if net_edge_bps > Decimal("150"):
            base_aggressiveness *= Decimal("1.15")  # 15% more aggressive
        elif net_edge_bps < Decimal("80"):
            base_aggressiveness *= Decimal("0.9")  # 10% less aggressive
        
        # More aggressive if low competition (fewer market makers)
        # This would require tracking competitor count (future enhancement)
        
        # Less aggressive if high inventory
        if state.inventory:
            inv_pressure = len(state.inventory) / Decimal("5")  # Normalize
            if inv_pressure > Decimal("1.0"):
                base_aggressiveness *= Decimal("0.9")  # 10% less aggressive
        
        return base_aggressiveness
    
    def plan(self, ...):
        # ... existing code ...
        
        # Calculate aggressiveness
        aggressiveness = self._calculate_aggressiveness(state, net_edge, settings)
        
        # Apply aggressiveness to price adjustments
        available_adjust = net_edge - min_profit_bps
        if available_adjust > 0:
            # Scale adjustments by aggressiveness
            buy_adjust = min(
                (available_adjust / Decimal("2")) * aggressiveness,
                Decimal(settings.max_bid_improve_bps)
            )
            sell_adjust = min(
                (available_adjust - buy_adjust) * aggressiveness,
                Decimal(settings.max_sell_reduce_bps)
            )
            # ... rest of existing code ...
```

---

### **STEP 6: Add Fill Rate Based Adjustment**

```python
# File: scalper/state.py

class PairRuntimeState:
    # ... existing code ...
    
    def calculate_fill_rate(self, time_window_s: float = 300.0) -> Decimal:
        """
        Calculate fill rate (orders filled / orders placed) in time window.
        """
        now = time.time()
        window_start = now - time_window_s
        
        # Count orders placed and filled in window
        orders_placed = sum(
            1 for ts in self.recent_order_placements
            if ts >= window_start
        )
        orders_filled = sum(
            1 for ts in self.recent_order_fills
            if ts >= window_start
        )
        
        if orders_placed > 0:
            return Decimal(orders_filled) / Decimal(orders_placed)
        return Decimal("0")
```

```python
# File: scalper/strategy.py

def plan(self, ...):
    # ... existing code ...
    
    # Adjust aggressiveness based on fill rate
    fill_rate = state.calculate_fill_rate(time_window_s=300.0)
    if fill_rate < Decimal("0.3"):  # Less than 30% fill rate
        # Too conservative, be more aggressive
        aggressiveness *= Decimal("1.2")
    elif fill_rate > Decimal("0.8"):  # More than 80% fill rate
        # Too aggressive, be less aggressive (widen spread)
        aggressiveness *= Decimal("0.9")
```

---

## 🧪 TESTING

### **Test Cases:**

1. **Basic Undercut Detection**
   - Place sell order at $100.01
   - Competitor places sell at $100.00
   - Verify: System detects undercut and reprices to $99.99

2. **Profitability Check**
   - Place sell order at $100.01 (min profitable = $100.00)
   - Competitor places sell at $99.99
   - Verify: System cancels order (can't beat profitably)

3. **Queue Position**
   - Place sell order at $100.01
   - Two competitors place sells at $100.00 and $99.99
   - Verify: System detects queue position = 3 and reprices

4. **Fill Rate Adjustment**
   - Fill rate < 30% → Verify: More aggressive pricing
   - Fill rate > 80% → Verify: Less aggressive pricing

---

## 📊 EXPECTED IMPROVEMENTS

### **Fill Rate:**
- **Before:** 30-50% of orders fill
- **After:** 60-80% of orders fill
- **Improvement:** 2x more fills

### **Response Time:**
- **Before:** 400ms (polling interval)
- **After:** < 10ms (real-time detection)
- **Improvement:** 40x faster

### **Profitability:**
- **Before:** Miss opportunities due to uncompetitive prices
- **After:** Stay competitive while maintaining profitability
- **Improvement:** 20-30% more profitable trades

---

## 🚀 IMPLEMENTATION PRIORITY

### **Phase 1: Basic Undercut Detection (1 week)**
- Add `is_undercut()` to `OrderBookSnapshot`
- Add `check_undercuts()` to `ExecutionManager`
- Integrate into `_run_pair()` loop
- **Impact:** 30-50% more fills

### **Phase 2: Smart Repricing (1 week)**
- Add `reprice_undercut_order()` with profitability checks
- Add tick size detection
- **Impact:** Stay competitive while profitable

### **Phase 3: Adaptive Aggressiveness (1 week)**
- Add fill rate tracking
- Add aggressiveness calculation
- **Impact:** 20-30% better pricing

### **Phase 4: WebSocket Real-Time (2-3 weeks)**
- Replace REST polling with WebSocket
- Real-time undercut detection
- **Impact:** 40x faster response

---

## 📝 NOTES

1. **Tick Size:** Different exchanges have different tick sizes. Need to handle this per exchange.

2. **Profitability:** Always ensure repriced orders are still profitable. Don't race to the bottom.

3. **Rate Limits:** Frequent repricing might hit rate limits. Need to throttle if necessary.

4. **Order Modification:** Some exchanges support order modification (change price without canceling). Use this if available for faster repricing.

5. **WebSocket Priority:** WebSocket is critical for real-time undercut detection. REST polling is too slow.

---

## ✅ SUCCESS METRICS

- **Fill Rate:** Increase from 30-50% to 60-80%
- **Response Time:** Decrease from 400ms to < 10ms
- **Queue Position:** Stay at position #1 more often
- **Profitability:** Maintain profitability while staying competitive

---

**This implementation will ensure our money goes to good use by:**
1. ✅ Detecting when we get undercut immediately
2. ✅ Adjusting prices to stay competitive
3. ✅ Maintaining profitability while competing
4. ✅ Maximizing fill rates
5. ✅ Adapting aggressiveness based on performance

