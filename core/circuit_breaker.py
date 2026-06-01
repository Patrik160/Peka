# ============================================================
#  circuit_breaker.py  –  Resilience pattern
# ============================================================
"""
Circuit Breaker Implementation
==============================

Resilience pattern to prevent cascading failures.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Too many failures, reject requests fast
- HALF_OPEN: Testing recovery, allow one request

Behavior:
1. Track failures across tool calls
2. After threshold failures → OPEN state
3. Block requests during OPEN
4. After timeout → HALF_OPEN (test mode)
5. One success → CLOSED (recovered)
6. One failure → OPEN (still broken)

Configuration:
- failure_threshold: Number of failures before opening (default: 5)
- recovery_timeout: Seconds to wait before testing recovery (default: 60)

UPCOMING FEATURES:
- [ ] Sliding window failure tracking
- [ ] Dynamic threshold adjustment based on load
- [ ] Metrics collection per service
- [ ] Health check integration
- [ ] Service-level agreements (SLAs)
- [ ] Multi-level circuit breakers (per tool)
- [ ] Circuit breaker dashboard
- [ ] Automatic scaling on circuit open
- [ ] Event notifications on state change
- [ ] Circuit breaker strategy composition

NEXT UPDATE IDEAS:
- Add exponential backoff on repeated failures
- Implement bulkhead pattern (isolated resource pools)
- Support metrics export (Prometheus)
- Add circuit breaker statistics
- Implement health check patterns
- Support service mesh integration
- Add remediation actions (restart, reconnect, etc.)
"""

import threading
import time
from dataclasses import dataclass
from enum import Enum
from core.logging_setup import _log

class CircuitState(Enum):
    """
    Circuit breaker state enumeration.
    
    States:
    - CLOSED: Accept all requests (normal operation)
    - OPEN: Reject all requests fast (failure mode)
    - HALF_OPEN: Accept one request for testing (recovery mode)
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreaker:
    """
    Circuit breaker for resilience and failure prevention.
    
    Prevents cascading failures by fast-failing when a service is experiencing issues.
    
    Attributes:
        failure_threshold (int): Number of failures before opening circuit
        recovery_timeout (float): Seconds to wait before attempting recovery
        
    Thread Safety:
    - All state changes protected by lock
    - Safe for concurrent access from multiple tools
    
    Example:
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        assert circuit_breaker.get_state() == CircuitState.OPEN
        
        # After timeout
        time.sleep(61)
        assert circuit_breaker.can_execute() == True  # HALF_OPEN test allowed
    """
    failure_threshold: int = 5
    recovery_timeout: float = 60.0

    def __post_init__(self):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()

    def record_success(self):
        """
        Record a successful operation.
        
        Resets failure count and closes circuit if in HALF_OPEN state.
        """
        with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                _log("CIRCUIT", "Circuit breaker closed - service recovered")

    def record_failure(self):
        """
        Record a failed operation.
        
        Increments failure count and opens circuit if threshold exceeded.
        """
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                _log("CIRCUIT", f"Circuit breaker opened after {self._failure_count} failures", "WARNING")

    def can_execute(self) -> bool:
        """
        Check if a request should be executed.
        
        Returns:
            bool: True if request can proceed, False if should fail fast
            
        Logic:
        - CLOSED: Always allow (return True)
        - OPEN: Check timeout, transition to HALF_OPEN if timeout elapsed
        - HALF_OPEN: Allow one request for testing (return True)
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    _log("CIRCUIT", "Circuit breaker half-open - testing recovery")
                    return True
                return False
            return True  # HALF_OPEN allows one test call

    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        with self._lock:
            return self._state

# Global instance used everywhere
circuit_breaker = CircuitBreaker()