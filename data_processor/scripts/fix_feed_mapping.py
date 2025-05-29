#!/usr/bin/env python3
"""
Script để tạo hoặc verify các feeds trên Adafruit IO với tên đúng.
"""
import os
import sys
import time
from dotenv import load_dotenv

# Thêm project root vào Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Adafruit_IO import Client

# Load environment variables
load_dotenv()

# Định nghĩa mapping giữa tên logic và tên feed thực tế
FEED_MAPPINGS = {
    # Sensors
    "light": {
        "key": "light-sensor",
        "name": "Light Sensor",
        "description": "Light intensity sensor data"
    },
    "temperature": {
        "key": "dht20-temperature", 
        "name": "DHT20 Temperature",
        "description": "Temperature data from DHT20 sensor"
    },
    "humidity": {
        "key": "dht20-humidity",
        "name": "DHT20 Humidity", 
        "description": "Humidity data from DHT20 sensor"
    },
    "soil_moisture": {
        "key": "soil-moisture",
        "name": "Soil Moisture",
        "description": "Soil moisture sensor data"
    },
    # Actuators
    "water_pump": {
        "key": "water-pump-control",
        "name": "Water Pump Control",
        "description": "Control signal for water pump"
    }
}

def create_or_verify_feeds():
    """Tạo hoặc verify các feeds trên Adafruit IO."""
    username = os.getenv("ADAFRUIT_IO_USERNAME")
    key = os.getenv("ADAFRUIT_IO_KEY")
    
    if not username or not key:
        print("❌ Adafruit IO credentials not found")
        return False
    
    # Khởi tạo client
    client = Client(username, key)
    
    print("=== Creating/Verifying Adafruit IO Feeds ===\n")
    
    # Lấy danh sách feeds hiện có
    try:
        existing_feeds = client.feeds()
        existing_keys = [feed.key for feed in existing_feeds]
        print(f"Found {len(existing_feeds)} existing feeds:\n")
        for feed in existing_feeds:
            print(f"  - {feed.key} (name: {feed.name})")
    except Exception as e:
        print(f"❌ Error getting existing feeds: {str(e)}")
        return False
    
    print("\n=== Processing Required Feeds ===\n")
    
    created_count = 0
    verified_count = 0
    
    for logical_name, feed_info in FEED_MAPPINGS.items():
        feed_key = feed_info["key"]
        feed_name = feed_info["name"]
        feed_description = feed_info["description"]
        
        print(f"Processing {logical_name} -> {feed_key}")
        
        if feed_key in existing_keys:
            print(f"  ✅ Feed already exists: {feed_key}")
            verified_count += 1
        else:
            # Tạo feed mới
            try:
                from Adafruit_IO import Feed
                
                new_feed = Feed(
                    key=feed_key,
                    name=feed_name,
                    description=feed_description
                )
                
                created_feed = client.create_feed(new_feed)
                print(f"  ✅ Created new feed: {feed_key}")
                created_count += 1
                
                # Delay để tránh rate limit
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ Error creating feed {feed_key}: {str(e)}")
    
    print(f"\n=== Summary ===")
    print(f"Verified: {verified_count} feeds")
    print(f"Created: {created_count} feeds")
    print(f"Total: {verified_count + created_count}/{len(FEED_MAPPINGS)} feeds")
    
    # Cập nhật file config
    if created_count > 0:
        print("\n=== Updating Configuration File ===")
        update_config_file()
    
    return True

def update_config_file():
    """Cập nhật file adafruit_config.py với mapping đúng."""
    config_content = '''"""
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
'''
    
    config_path = os.path.join("config", "adafruit_config.py")
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        print(f"✅ Updated {config_path}")
    except Exception as e:
        print(f"❌ Error updating config file: {str(e)}")

def main():
    """Main function."""
    print("Adafruit IO Feed Setup Tool")
    print("=" * 50)
    
    # Kiểm tra credentials
    username = os.getenv("ADAFRUIT_IO_USERNAME")
    key = os.getenv("ADAFRUIT_IO_KEY")
    
    if not username or not key:
        print("\n❌ Error: Adafruit IO credentials not found!")
        print("\nPlease set the following environment variables:")
        print("  - ADAFRUIT_IO_USERNAME")
        print("  - ADAFRUIT_IO_KEY")
        sys.exit(1)
    
    print(f"\nUsing account: {username}")
    print("=" * 50)
    
    # Tạo hoặc verify feeds
    success = create_or_verify_feeds()
    
    if success:
        print("\n✅ Feed setup completed successfully!")
        print("\nNext steps:")
        print("1. Update your .env file with correct Firebase URL")
        print("2. Restart the application")
    else:
        print("\n❌ Feed setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()