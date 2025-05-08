"""
Script kiểm tra thu thập dữ liệu từ các cảm biến.
"""
import os
import sys
import json
import logging
from dotenv import load_dotenv
from pprint import pprint

# Thiết lập logging cơ bản
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Tải biến môi trường
load_dotenv()

def test_adafruit_sensor_data():
    """Kiểm tra khả năng lấy dữ liệu cảm biến từ Adafruit IO."""
    try:
        from src.adapters.cloud.adafruit import AdafruitIOClient
        from src.infrastructure import ServiceFactory
        
        # Lấy thông tin đăng nhập Adafruit
        factory = ServiceFactory()
        config = factory.get_config_loader()
        credentials = config.get_adafruit_credentials()
        
        if not credentials['username'] or not credentials['key']:
            logger.error("❌ Adafruit IO credentials not found in environment variables")
            return False
            
        client = AdafruitIOClient(credentials['username'], credentials['key'])
        
        # Lấy danh sách feeds để kiểm tra
        try:
            feeds = client.client.feeds()
            logger.info(f"✅ Found {len(feeds)} feeds in Adafruit IO account")
            
            # Hiển thị thông tin feeds
            for feed in feeds:
                logger.info(f"  - Feed: {feed.key} ({feed.name})")
                
                # Thử lấy dữ liệu mới nhất
                data = client.get_last_data(feed.key)
                if data:
                    logger.info(f"    Latest value: {data.get('value')} at {data.get('created_at')}")
                else:
                    logger.warning(f"    No data available for feed: {feed.key}")
                    
            return True
        except Exception as e:
            logger.error(f"❌ Error getting feeds from Adafruit IO: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Adafruit IO test failed: {str(e)}")
        return False

def test_data_collectors():
    """Kiểm tra các bộ thu thập dữ liệu cảm biến."""
    try:
        from src.core.data.collectors import (
            LightCollector,
            TemperatureCollector,
            HumidityCollector,
            SoilMoistureCollector
        )
        
        collectors = [
            ("Light", LightCollector()),
            ("Temperature", TemperatureCollector()),
            ("Humidity", HumidityCollector()),
            ("Soil Moisture", SoilMoistureCollector())
        ]
        
        success_count = 0
        
        for name, collector in collectors:
            logger.info(f"Testing {name} collector...")
            
            try:
                # Thu thập dữ liệu mới nhất
                reading = collector.collect_latest_data()
                
                if reading:
                    logger.info(f"✅ {name}: {reading.value} {reading.unit} (Status: {reading.status})")
                    success_count += 1
                else:
                    logger.warning(f"⚠️ {name}: No data collected")
            except Exception as e:
                logger.error(f"❌ {name} collector error: {str(e)}")
                
        logger.info(f"\nCollector test results: {success_count}/{len(collectors)} successful")
        return success_count == len(collectors)
        
    except Exception as e:
        logger.error(f"❌ Data collectors test failed: {str(e)}")
        return False

def test_data_manager():
    """Kiểm tra DataManager."""
    try:
        from src.core.data import DataManager
        
        data_manager = DataManager()
        
        # Thu thập dữ liệu từ tất cả cảm biến
        logger.info("Testing DataManager.collect_all_latest_data()...")
        readings = data_manager.collect_all_latest_data()
        
        if readings:
            logger.info(f"✅ Collected data from {len(readings)} sensors")
            
            for sensor_type, reading in readings.items():
                logger.info(f"  - {sensor_type.value}: {reading.value} {reading.unit} (Status: {reading.status})")
                
            # Lấy snapshot
            logger.info("\nTesting DataManager.get_environment_snapshot()...")
            snapshot = data_manager.get_environment_snapshot(collect_if_needed=False)
            
            logger.info(f"✅ Environment snapshot created at {snapshot.timestamp}")
            logger.info(f"  Overall status: {snapshot.get_overall_status()}")
            
            if snapshot.light:
                logger.info(f"  Light: {snapshot.light.value} {snapshot.light.unit} (Status: {snapshot.light.status})")
            if snapshot.temperature:
                logger.info(f"  Temperature: {snapshot.temperature.value} {snapshot.temperature.unit} (Status: {snapshot.temperature.status})")
            if snapshot.humidity:
                logger.info(f"  Humidity: {snapshot.humidity.value} {snapshot.humidity.unit} (Status: {snapshot.humidity.status})")
            if snapshot.soil_moisture:
                logger.info(f"  Soil Moisture: {snapshot.soil_moisture.value} {snapshot.soil_moisture.unit} (Status: {snapshot.soil_moisture.status})")
                
            return True
        else:
            logger.warning("⚠️ No data collected by DataManager")
            return False
            
    except Exception as e:
        logger.error(f"❌ DataManager test failed: {str(e)}")
        return False

def run_tests():
    """Chạy tất cả các kiểm tra liên quan đến cảm biến."""
    logger.info("=== Testing Sensor Data Collection ===\n")
    
    logger.info("1. Testing Adafruit IO connectivity and sensor data...")
    adafruit_result = test_adafruit_sensor_data()
    
    logger.info("\n2. Testing individual data collectors...")
    collectors_result = test_data_collectors()
    
    logger.info("\n3. Testing DataManager...")
    manager_result = test_data_manager()
    
    logger.info("\n=== Sensor Test Results ===")
    logger.info(f"Adafruit IO: {'✅ PASS' if adafruit_result else '❌ FAIL'}")
    logger.info(f"Data Collectors: {'✅ PASS' if collectors_result else '❌ FAIL'}")
    logger.info(f"DataManager: {'✅ PASS' if manager_result else '❌ FAIL'}")
    
    all_passed = adafruit_result and collectors_result and manager_result
    
    if all_passed:
        logger.info("\n🎉 All sensor tests PASSED!")
    else:
        logger.info("\n⚠️ Some sensor tests FAILED. Please check the logs above.")
        
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)