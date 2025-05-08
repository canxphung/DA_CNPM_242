"""
Cấu hình cho Firebase.
"""

# Cấu trúc dữ liệu Realtime Database
DATABASE_STRUCTURE = {
    "sensor_data": {
        "light": {},
        "temperature": {},
        "humidity": {},
        "soil_moisture": {}
    },
    "irrigation_events": {},
    "system_status": {},
    "users": {}
}

# Cấu hình bảo mật
SECURITY_RULES = {
    "read_access": ["admin", "viewer"],
    "write_access": ["admin"]
}