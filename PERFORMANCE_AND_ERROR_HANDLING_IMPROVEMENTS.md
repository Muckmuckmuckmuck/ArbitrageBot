# Performance & Error Handling Improvements

## 🚀 Performance Improvements

### 1. **Balance Caching with TTL**
**Current Issue**: Balance is fetched on every loop iteration (every 0.4s), causing unnecessary API calls.

**Solution**: Implement a balance cache with TTL (e.g., 2-5 seconds) per exchange.

```python
# In runner.py
class BalanceCache:
    def __init__(self, ttl_s: float = 3.0):
        self._cache: Dict[str, Tuple[Decimal, float]] = {}
        self._ttl_s = ttl_s
    
    async def get(self, client: RestExchangeClient, currency: str) -> Decimal:
        cache_key = f"{client._id}:{currency}"
        if cache_key in self._cache:
            balance, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._ttl_s:
                return balance
        # Fetch fresh balance
        balance = await self._fetch_fresh(client, currency)
        self._cache[cache_key] = (balance, time.time())
        return balance
```

**Impact**: Reduces API calls by ~75%, lowers rate limit risk, faster loop execution.

---

### 2. **Batch Market Evaluation with Semaphore**
**Current Issue**: Scanner evaluates markets sequentially, one at a time.

**Solution**: Use `asyncio.Semaphore` to limit concurrent evaluations (e.g., 10 at a time).

```python
# In discovery.py
async def refresh(self) -> List[PairSnapshot]:
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent evaluations
    
    async def _evaluate_with_limit(venue: str, symbol: str, client: RestExchangeClient):
        async with semaphore:
            return await self._evaluate_market(venue, symbol, client)
    
    # Use gather with semaphore-controlled tasks
    tasks = [_evaluate_with_limit(venue, symbol, client) 
             for symbol in candidates]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Impact**: 5-10x faster scanner refresh for large market lists.

---

### 3. **Order Book Caching**
**Current Issue**: Order book fetched every poll interval, even if unchanged.

**Solution**: Cache order book for 100-200ms, only fetch if cache expired or price moved significantly.

```python
# In market_data.py
class MarketDataPoller:
    def __init__(self, ...):
        self._cache_ttl = 0.15  # 150ms cache
        self._last_fetch = 0.0
        self._cached_book: Optional[Dict] = None
    
    async def _run(self) -> None:
        while self._running:
            now = time.time()
            # Only fetch if cache expired
            if now - self._last_fetch > self._cache_ttl:
                try:
                    book = await self._client.fetch_order_book(...)
                    self._cached_book = book
                    self._last_fetch = now
                except Exception:
                    # Use cached book if fetch fails
                    if self._cached_book:
                        book = self._cached_book
                    else:
                        await asyncio.sleep(self._interval_s)
                        continue
            else:
                book = self._cached_book
```

**Impact**: Reduces order book API calls by 30-50%, faster response times.

---

### 4. **Optimize Slippage Calculation**
**Current Issue**: `estimate_slippage_bps` called multiple times in `plan()` method.

**Solution**: Calculate once and reuse, or memoize based on order_value/depth.

```python
# In strategy.py
def plan(self, ...):
    # Calculate slippage once per tier evaluation
    slippage_cache: Dict[Decimal, Decimal] = {}
    
    def get_slippage(order_value: Decimal) -> Decimal:
        if order_value not in slippage_cache:
            slippage_cache[order_value] = estimate_slippage_bps(
                order_value, depth_usd, settings
            )
        return slippage_cache[order_value]
```

**Impact**: Reduces redundant calculations, faster planning.

---

### 5. **Parallel Balance Fetching**
**Current Issue**: Base and quote balances fetched sequentially.

**Solution**: Fetch both balances concurrently.

```python
# In runner.py
async def _fetch_balances(self, client: RestExchangeClient, pair: PairConfig) -> Tuple[Decimal, Decimal]:
    base_task = self._fetch_base_balance(client, pair.base)
    quote_task = self._fetch_stable_balance(client, pair.quote)
    base_bal, quote_bal = await asyncio.gather(base_task, quote_task)
    return base_bal, quote_bal
```

**Impact**: 2x faster balance fetching.

---

### 6. **Optimize Trade Fetching**
**Current Issue**: Fetches 100 trades every loop, even if only 1-2 new trades exist.

**Solution**: Use incremental pagination, track last trade ID, fetch only new trades.

```python
# In runner.py
async def _consume_trades(self, ...):
    # Track last trade ID instead of timestamp
    last_trade_id = state.last_trade_id
    try:
        # Fetch with limit=10, since=last_trade_id
        trades = await client.fetch_my_trades(
            pair.symbol, 
            since=None,  # Use since only if last_trade_id not available
            limit=10  # Reduced from 100
        )
        # Filter to only new trades
        new_trades = [t for t in trades if str(t.get("id")) != last_trade_id]
        if new_trades:
            state.last_trade_id = str(new_trades[-1].get("id"))
    except Exception:
        ...
```

**Impact**: 10x fewer trades processed, faster trade consumption.

---

### 7. **Reduce Lock Contention**
**Current Issue**: `ExecutionManager._lock` held during entire order submission (network I/O).

**Solution**: Release lock before network calls, re-acquire only for dictionary updates.

```python
# In execution.py
async def sync_quotes(self, intent: QuoteIntent) -> None:
    # Calculate desired orders while holding lock
    async with self._lock:
        desired = {...}  # Calculate desired orders
        to_cancel = [...]  # Identify orders to cancel
    
    # Release lock during network I/O
    if to_cancel:
        await self._cancel_orders(to_cancel)
    
    # Re-acquire lock only for dictionary updates
    async with self._lock:
        for oid in to_cancel:
            self._quote_orders.pop(oid, None)
        # Submit new orders (these will acquire lock internally)
```

**Impact**: Reduces lock contention, allows parallel order operations.

---

### 8. **Request Batching for Exchange API**
**Current Issue**: Each API call is independent, no batching.

**Solution**: Batch multiple requests where possible (e.g., fetch multiple order books in one call if exchange supports it).

**Note**: This depends on exchange API capabilities. For now, use connection pooling.

```python
# In exchange.py
import aiohttp

class RestExchangeClient:
    def __init__(self, ...):
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                connector=aiohttp.TCPConnector(limit=10)  # Connection pooling
            )
        return self._session
```

**Impact**: Faster API calls, better connection reuse.

---

## 🛡️ Error Handling Improvements

### 1. **Exponential Backoff for Rate Limits**
**Current Issue**: No backoff strategy when hitting rate limits.

**Solution**: Implement exponential backoff with jitter.

```python
# In exchange.py
import random

class RestExchangeClient:
    async def _request_with_backoff(self, func, *args, max_retries=3, **kwargs):
        base_delay = 1.0
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except ccxt.RateLimitExceeded as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Rate limit hit, backing off {delay:.2f}s")
                await asyncio.sleep(delay)
            except ccxt.NetworkError as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
```

**Impact**: Prevents rate limit bans, handles transient network errors.

---

### 2. **Circuit Breaker Pattern**
**Current Issue**: Continues trying failed exchanges indefinitely.

**Solution**: Implement circuit breaker to temporarily disable failing exchanges.

```python
# In runner.py
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60.0):
        self._failures = 0
        self._failure_threshold = failure_threshold
        self._timeout = timeout
        self._opened_at: Optional[float] = None
        self._state = "closed"  # closed, open, half_open
    
    def record_success(self):
        self._failures = 0
        self._state = "closed"
        self._opened_at = None
    
    def record_failure(self):
        self._failures += 1
        if self._failures >= self._failure_threshold:
            self._state = "open"
            self._opened_at = time.time()
    
    def can_proceed(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "open":
            if time.time() - self._opened_at > self._timeout:
                self._state = "half_open"
                return True
            return False
        return True  # half_open
    
    def is_open(self) -> bool:
        return self._state == "open"

# Usage in runner
self._circuit_breakers: Dict[str, CircuitBreaker] = {}

async def _client_for(self, exchange: str) -> RestExchangeClient:
    breaker = self._circuit_breakers.get(exchange)
    if breaker and breaker.is_open():
        raise RuntimeError(f"Circuit breaker open for {exchange}")
    # ... existing code ...
```

**Impact**: Prevents wasting time on failing exchanges, faster recovery.

---

### 3. **Specific Exception Handling**
**Current Issue**: Generic `except Exception` catches everything, losing context.

**Solution**: Handle specific exceptions with appropriate recovery.

```python
# In execution.py
async def _submit(self, ...):
    try:
        order = await self._client.create_limit_order(...)
    except InsufficientFunds as e:
        logger.warning(f"[EXECUTE] Insufficient funds: {e}")
        # Update balance cache, skip this order
        return None
    except ccxt.InvalidOrder as e:
        logger.error(f"[EXECUTE] Invalid order: {e}")
        # Don't retry, order parameters are wrong
        return None
    except ccxt.NetworkError as e:
        logger.warning(f"[EXECUTE] Network error: {e}")
        # Retry with backoff
        return await self._submit_with_retry(...)
    except ccxt.ExchangeError as e:
        logger.error(f"[EXECUTE] Exchange error: {e}")
        # May need circuit breaker
        raise
    except Exception as e:
        logger.exception(f"[EXECUTE] Unexpected error: {e}")
        # Last resort catch-all
        return None
```

**Impact**: Better error recovery, more actionable logs.

---

### 4. **Timeout Handling**
**Current Issue**: No timeouts on API calls, can hang indefinitely.

**Solution**: Add timeouts to all API calls.

```python
# In exchange.py
import asyncio

async def fetch_order_book(self, symbol: str, depth: int = 5) -> Dict[str, Any]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(self._client.fetch_order_book, symbol, depth),
            timeout=5.0  # 5 second timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching order book for {symbol}")
        raise ccxt.RequestTimeout(f"Order book fetch timeout for {symbol}")
```

**Impact**: Prevents hanging, faster failure detection.

---

### 5. **Graceful Degradation**
**Current Issue**: Bot stops working if one component fails.

**Solution**: Continue operating with degraded functionality.

```python
# In runner.py
async def _run_pair(self, pair_key: str) -> None:
    try:
        snapshot = poller.latest()
        if not snapshot:
            # Use last known snapshot if available
            snapshot = state.last_snapshot
            if not snapshot:
                await asyncio.sleep(self._config.settings.poll_interval_s)
                continue
    except Exception as e:
        logger.warning(f"Failed to get snapshot, using cached: {e}")
        snapshot = state.last_snapshot
        if not snapshot:
            continue
    
    # Continue with degraded snapshot
    state.last_snapshot = snapshot
```

**Impact**: Bot continues operating during partial failures.

---

### 6. **Retry Logic with Exponential Backoff**
**Current Issue**: No retries for transient failures.

**Solution**: Retry critical operations with exponential backoff.

```python
# In runner.py
async def _fetch_with_retry(
    self,
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs
) -> Any:
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except (ccxt.NetworkError, ccxt.RequestTimeout) as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            logger.debug(f"Retry {attempt + 1}/{max_retries} after {delay:.2f}s: {e}")
            await asyncio.sleep(delay)
        except Exception as e:
            # Don't retry non-transient errors
            raise
```

**Impact**: Handles transient network issues automatically.

---

### 7. **Error Recovery for Stuck Orders**
**Current Issue**: If order submission fails mid-process, state can be inconsistent.

**Solution**: Transaction-like behavior with rollback.

```python
# In execution.py
async def sync_quotes(self, intent: QuoteIntent) -> None:
    # Track what we're about to change
    old_orders = dict(self._quote_orders)
    try:
        # ... cancellation and submission logic ...
    except Exception as e:
        logger.error(f"Failed to sync quotes, rolling back: {e}")
        # Attempt to restore previous state
        self._quote_orders = old_orders
        raise
```

**Impact**: Prevents inconsistent state, better recovery.

---

### 8. **Health Monitoring**
**Current Issue**: No visibility into system health.

**Solution**: Track error rates, latency, success rates.

```python
# In runner.py
class HealthMonitor:
    def __init__(self):
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._success_counts: Dict[str, int] = defaultdict(int)
    
    def record_error(self, operation: str):
        self._error_counts[operation] += 1
    
    def record_success(self, operation: str, latency_ms: float):
        self._success_counts[operation] += 1
        self._latencies[operation].append(latency_ms)
        # Keep only last 100
        if len(self._latencies[operation]) > 100:
            self._latencies[operation].pop(0)
    
    def get_health(self) -> Dict[str, Any]:
        return {
            "error_rates": dict(self._error_counts),
            "avg_latencies": {
                op: sum(lats) / len(lats) if lats else 0
                for op, lats in self._latencies.items()
            },
            "success_rates": dict(self._success_counts)
        }
```

**Impact**: Better observability, proactive issue detection.

---

## 📊 Priority Ranking

### High Priority (Implement First)
1. **Balance Caching** - Immediate 75% reduction in API calls
2. **Exponential Backoff** - Prevents rate limit bans
3. **Specific Exception Handling** - Better error recovery
4. **Timeout Handling** - Prevents hanging

### Medium Priority
5. **Batch Market Evaluation** - Faster scanner
6. **Circuit Breaker** - Better resilience
7. **Parallel Balance Fetching** - 2x speedup
8. **Retry Logic** - Handles transient errors

### Low Priority (Nice to Have)
9. **Order Book Caching** - Minor improvement
10. **Slippage Optimization** - Small CPU savings
11. **Reduce Lock Contention** - Complex, marginal benefit
12. **Health Monitoring** - Observability only

---

## 🎯 Implementation Order

1. **Week 1**: Balance caching, exponential backoff, timeout handling
2. **Week 2**: Specific exception handling, retry logic, parallel balance fetching
3. **Week 3**: Circuit breaker, batch market evaluation
4. **Week 4**: Order book caching, health monitoring, optimizations

---

## 📈 Expected Impact

- **API Call Reduction**: 60-75% fewer calls
- **Latency Reduction**: 30-50% faster loop execution
- **Error Recovery**: 90%+ of transient errors handled automatically
- **Uptime**: 99.5%+ uptime even with exchange issues
- **Rate Limit Risk**: Near-zero risk of bans

