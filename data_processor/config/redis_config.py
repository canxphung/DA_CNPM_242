"""
Cấu hình cho Redis.
"""

# Thời gian hết hạn mặc định cho dữ liệu cache (giây)
DEFAULT_EXPIRATION = 3600  # 1 giờ

# Tiền tố khóa cho các loại dữ liệu khác nhau
KEY_PREFIXES = {
    "sensor_data": "sensor:",
    "environment_state": "env:",
    "irrigation_schedule": "schedule:",
    "water_pump_state": "pump:"
}