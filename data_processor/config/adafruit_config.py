"""
Cấu hình cho kết nối Adafruit IO và định nghĩa các feeds.
"""

# Cấu hình kết nối Adafruit IO
ADAFRUIT_CONFIG = {
    # Thông tin kết nối sẽ được lấy từ biến môi trường
    
    # Định nghĩa các feed cảm biến
    "sensor_feeds": {
        "light": "light-sensor",
        "temperature": "dht20-temperature",
        "humidity": "dht20-humidity",
        "soil_moisture": "soil-moisture"
    },
    
    # Định nghĩa các feed điều khiển
    "actuator_feeds": {
        "water_pump": "water-pump-control"
    },
    
    # Cấu hình thu thập dữ liệu
    "data_collection": {
        "default_limit": 10,  # Số lượng điểm dữ liệu mặc định khi truy vấn
        "interval": 60,  # Thời gian giữa các lần thu thập dữ liệu (giây)
    }
}