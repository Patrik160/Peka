# ============================================================
#  performance_metrics.py  –  Monitoring & stats
# ============================================================
from typing import Any, Dict
from dataclasses import dataclass, field

@dataclass
class PerformanceMetrics:
    tool_calls: Dict[str, float] = field(default_factory=dict)
    total_calls: int = 0
    avg_response_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    connection_errors: int = 0
    audio_chunks_dropped: int = 0

    def record_call(self, tool_name: str, duration: float):
        self.tool_calls[tool_name] = self.tool_calls.get(tool_name, 0) + duration
        self.total_calls += 1
        self.avg_response_time = sum(self.tool_calls.values()) / max(1, self.total_calls)

    def get_cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "avg_response_time": self.avg_response_time,
            "cache_hit_rate": self.get_cache_hit_rate(),
            "connection_errors": self.connection_errors,
            "audio_drops": self.audio_chunks_dropped,
            "top_tools": dict(sorted(self.tool_calls.items(), key=lambda x: x[1], reverse=True)[:5])
        }

    def record_cache_hit(self):
        self.cache_hits += 1

    def record_cache_miss(self):
        self.cache_misses += 1

# Global instance
metrics = PerformanceMetrics()

def get_performance_metrics() -> Dict[str, Any]:
    return metrics.get_summary()