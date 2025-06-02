"""
Cấu hình cho Redis.
"""

# Thời gian hết hạn mặc định cho dữ liệu cache (giây)
# Thời gian hết hạn tối ưu cho các loại dữ liệu
"""
Cấu hình cho Redis - Version tương thích với code hiện tại.
"""

# GIỮ NGUYÊN tên biến cũ để tương thích
DEFAULT_EXPIRATION = 3600  # 1 giờ

# Tiền tố khóa cho các loại dữ liệu khác nhau
KEY_PREFIXES = {
    "sensor_data": "sensor:",
    "environment_state": "env:",
    "irrigation_schedule": "schedule:",
    "water_pump_state": "pump:"
}

# THÊM MỚI: TTL tối ưu cho từng loại dữ liệu
OPTIMIZED_EXPIRATION = {
    "sensor_latest": 600,      # 10 phút cho latest reading
    "sensor_history": 86400,   # 24 giờ cho history
    "environment_snapshot": 120, # 2 phút cho snapshot
    "pump_state": 60,          # 1 phút cho pump state
    "schedules": 3600,         # 1 giờ cho schedules
    "last_decision": 1800,     # 30 phút
    "decision_history": 86400, # 24 giờ
    "system_config": 3600,     # 1 giờ
    "collection_stats": 300,   # 5 phút
}

# THÊM MỚI: Cache configuration
CACHE_CONFIG = {
    "enable_stale_while_revalidate": True,
    "stale_timeout": 300,  # 5 phút - data còn dùng được
    "max_stale_timeout": 900,  # 15 phút - quá cũ, cần refresh
    "default_ttl": 600,  # 10 phút - TTL mặc định cho sensor data
}

# THÊM MỚI: Helper function để lấy TTL phù hợp
def get_optimized_ttl(data_type: str, default: int = None) -> int:
    """
    Lấy TTL tối ưu cho loại dữ liệu.
    
    Args:
        data_type: Loại dữ liệu (sensor_latest, pump_state, etc.)
        default: Giá trị mặc định nếu không tìm thấy
        
    Returns:
        TTL tính bằng giây
    """
    if default is None:
        default = DEFAULT_EXPIRATION
        
    return OPTIMIZED_EXPIRATION.get(data_type, default)

# Performance monitoring keys
MONITORING_KEYS = {
    "cache_stats": "monitoring:cache_stats",
    "performance_metrics": "monitoring:performance",
    "adafruit_calls": "monitoring:adafruit_calls"
}
# Redis pool configuration
# REDIS_POOL_CONFIG = {
#     "max_connections": 50,
#     "socket_keepalive": True,
#     "socket_keepalive_options": {
#         1: 1,   # TCP_KEEPIDLE
#         2: 3,   # TCP_KEEPINTVL
#         3: 5,   # TCP_KEEPCNT
#     },
#     "retry_on_timeout": True,
#     "health_check_interval": 30
# }
