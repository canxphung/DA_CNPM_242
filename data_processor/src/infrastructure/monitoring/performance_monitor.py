"""
Performance monitoring cho tracking metrics.
"""
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Singleton class để monitor performance metrics."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PerformanceMonitor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "adafruit_calls": 0,
            "slow_operations": 0,
            "total_requests": 0,
            "errors": 0
        }
        
        self.operation_times = []
        self._initialized = True
    
    def record_cache_hit(self):
        self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        self.metrics["cache_misses"] += 1
    
    def record_adafruit_call(self):
        self.metrics["adafruit_calls"] += 1
    
    def record_operation(self, operation_name: str, duration: float):
        """Record operation time."""
        self.operation_times.append({
            "name": operation_name,
            "duration": duration,
            "timestamp": datetime.now()
        })
        
        # Log slow operations
        if duration > 2.0:
            self.metrics["slow_operations"] += 1
            logger.warning(f"Slow operation: {operation_name} took {duration:.2f}s")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        cache_hit_rate = (self.metrics["cache_hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.metrics,
            "cache_hit_rate": cache_hit_rate,
            "total_operations": len(self.operation_times)
        }

def monitor_performance(operation_name: str):
    """Decorator để monitor performance của functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                monitor = PerformanceMonitor()
                monitor.record_operation(operation_name, duration)
                
                return result
            except Exception as e:
                monitor = PerformanceMonitor()
                monitor.metrics["errors"] += 1
                raise
        return wrapper
    return decorator