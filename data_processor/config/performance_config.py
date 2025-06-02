"""
Cấu hình performance và optimization.
"""

PERFORMANCE_CONFIG = {
    # Cache strategy
    "cache_strategy": {
        "mode": "cache_first",
        "stale_while_revalidate": True,
        "background_refresh": True
    },
    
    # Rate limiting cho Adafruit
    "adafruit_rate_limit": {
        "min_interval_seconds": 30,
        "max_retries": 2,
        "timeout_seconds": 5
    },
    
    # Thresholds
    "data_freshness": {
        "fresh": 300,      # 5 phút
        "stale": 600,      # 10 phút  
        "expired": 900     # 15 phút
    }
}