#!/usr/bin/env python3
"""
Script để kiểm tra và verify cấu hình hệ thống.
"""
import os
import sys
from dotenv import load_dotenv
import requests
import firebase_admin
from firebase_admin import credentials, db

# Thêm project root vào Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def check_env_vars():
    """Kiểm tra các biến môi trường cần thiết."""
    print("=== Checking Environment Variables ===")
    
    required_vars = [
        "ADAFRUIT_IO_USERNAME",
        "ADAFRUIT_IO_KEY",
        "FIREBASE_DATABASE_URL",
        "FIREBASE_CREDENTIALS_PATH",
        "REDIS_HOST",
        "REDIS_PORT"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: NOT SET")
        else:
            # Ẩn sensitive data
            if "KEY" in var or "PASSWORD" in var:
                display_value = value[:5] + "..." if len(value) > 5 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
    
    return len(missing_vars) == 0

def check_adafruit_feeds():
    """Kiểm tra các feeds trên Adafruit IO."""
    print("\n=== Checking Adafruit IO Feeds ===")
    
    username = os.getenv("ADAFRUIT_IO_USERNAME")
    key = os.getenv("ADAFRUIT_IO_KEY")
    
    if not username or not key:
        print("❌ Adafruit IO credentials not found")
        return False
    
    try:
        # Lấy danh sách feeds
        headers = {"X-AIO-Key": key}
        response = requests.get(
            f"https://io.adafruit.com/api/v2/{username}/feeds",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get feeds: {response.status_code}")
            return False
        
        feeds = response.json()
        feed_keys = [feed['key'] for feed in feeds]
        
        print(f"Found {len(feeds)} feeds:")
        for feed in feeds:
            print(f"  - {feed['key']} (name: {feed['name']})")
        
        # Kiểm tra required feeds từ config
        from config.adafruit_config import ADAFRUIT_CONFIG
        
        print("\nChecking required sensor feeds:")
        for sensor_type, feed_key in ADAFRUIT_CONFIG['sensor_feeds'].items():
            if feed_key in feed_keys:
                print(f"  ✅ {sensor_type}: {feed_key}")
            else:
                print(f"  ❌ {sensor_type}: {feed_key} NOT FOUND")
        
        print("\nChecking required actuator feeds:")
        for actuator_type, feed_key in ADAFRUIT_CONFIG['actuator_feeds'].items():
            if feed_key in feed_keys:
                print(f"  ✅ {actuator_type}: {feed_key}")
            else:
                print(f"  ❌ {actuator_type}: {feed_key} NOT FOUND")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Adafruit feeds: {str(e)}")
        return False

def check_firebase_connection():
    """Kiểm tra kết nối Firebase."""
    print("\n=== Checking Firebase Connection ===")
    
    db_url = os.getenv("FIREBASE_DATABASE_URL")
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    
    if not db_url or not cred_path:
        print("❌ Firebase configuration not found")
        return False
    
    # Kiểm tra format URL
    if "console.firebase.google.com" in db_url:
        print(f"❌ Invalid Firebase URL: {db_url}")
        print("   Should be: https://[project-id].firebaseio.com")
        return False
    
    try:
        # Khởi tạo Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': db_url
            })
        
        # Test connection
        ref = db.reference('test')
        ref.set({'timestamp': 'test'})
        data = ref.get()
        ref.delete()
        
        print(f"✅ Firebase connection successful")
        print(f"   URL: {db_url}")
        return True
        
    except Exception as e:
        print(f"❌ Firebase connection failed: {str(e)}")
        return False

def check_redis_connection():
    """Kiểm tra kết nối Redis."""
    print("\n=== Checking Redis Connection ===")
    
    import redis
    
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", 6379))
    password = os.getenv("REDIS_PASSWORD")
    
    try:
        client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True
        )
        
        # Test connection
        client.ping()
        
        print(f"✅ Redis connection successful")
        print(f"   Host: {host}:{port}")
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {str(e)}")
        return False

def main():
    """Main function."""
    print("Core Operations Service - Configuration Verification")
    print("=" * 50)
    
    results = {
        "env_vars": check_env_vars(),
        "adafruit": check_adafruit_feeds(),
        "firebase": check_firebase_connection(),
        "redis": check_redis_connection()
    }
    
    print("\n=== Summary ===")
    all_passed = all(results.values())
    
    for component, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{component}: {status}")
    
    if all_passed:
        print("\n✅ All checks passed! The system is ready to run.")
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()