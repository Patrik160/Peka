# ============================================================
#  ttl_cache.py  –  Thread-safe TTL cache
# ============================================================
"""
Time-To-Live Cache Implementation
==================================

Provides efficient caching of expensive operations with automatic expiration.

Features:
- Thread-safe access with lock
- Automatic TTL expiration
- LRU eviction when cache is full
- Simple key-value interface

Use Cases:
- Cache tool results (weather, flights, web search)
- Reduce redundant API calls
- Improve response latency

Configuration:
- ttl: Seconds before entry expires (default: 300 = 5 minutes)
- max_size: Maximum cached entries (default: 100)

UPCOMING FEATURES:
- [ ] Distributed caching (Redis backend)
- [ ] Automatic cache warming
- [ ] Cache hit/miss analytics
- [ ] Partitioned caches by tool
- [ ] Memcached/Memorystore integration
- [ ] Cache invalidation patterns
- [ ] Compression for large values
- [ ] Persistent cache to disk
- [ ] Cache versioning
- [ ] Cache serialization for distributed systems
- [ ] Bloom filters for negative caching
- [ ] Cache coherence mechanisms

NEXT UPDATE IDEAS:
- Add cache statistics (hits, misses, evictions)
- Implement LFU (least frequently used) eviction
- Support selective cache busting
- Add cache warming from config
- Implement cache preloading on startup
- Add cache health monitoring
- Support cache keys with patterns (wildcards)
- Implement cache sharing between instances
- Add cache compression for bandwidth savings
- Support probabilistic expiration (stale-while-revalidate)
"""

import threading
import time
from typing import Any, Dict, Optional

class TTLCache:
    """
    Time-to-live cache with thread-safe access.
    
    Stores key-value pairs that expire after a configured TTL.
    Automatically evicts oldest entries when max size is reached.
    
    Attributes:
        ttl (float): Seconds before entry expires
        max_size (int): Maximum number of cached entries
        
    Thread Safety:
    - All operations protected by lock
    - Safe for concurrent access from multiple threads
    
    Performance:
    - O(1) get/set in average case
    - O(n) eviction on cache full
    - O(1) cleanup on access
    
    Example:
        cache = TTLCache(ttl=300, max_size=100)
        
        cache.set("weather:NYC", {"temp": 72, "condition": "sunny"})
        result = cache.get("weather:NYC")
        assert result == {"temp": 72, "condition": "sunny"}
        
        # After TTL expires
        time.sleep(301)
        result = cache.get("weather:NYC")
        assert result is None
    
    UPCOMING:
    - [ ] Add cache statistics
    - [ ] Support custom eviction policies
    - [ ] Add metrics reporting
    """
    def __init__(self, ttl: float = 300.0, max_size: int = 100):
        """
        Initialize TTL cache.
        
        Args:
            ttl (float): Time-to-live in seconds
            max_size (int): Maximum cache entries
        """
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.monotonic() - timestamp < self._ttl:
                    return value
                del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        """
        Store value in cache.
        
        Evicts oldest entry if cache is at max capacity.
        
        Args:
            key (str): Cache key
            value (Any): Value to cache (any type)
        """
        with self._lock:
            if len(self._cache) >= self._max_size:
                # Evict oldest entry (LRU)
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (value, time.monotonic())

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

# Global tool‑result cache
tool_cache = TTLCache(ttl=60.0, max_size=50)