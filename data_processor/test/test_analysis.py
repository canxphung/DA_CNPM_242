"""
Script kiểm tra các analyzer môi trường.
"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pprint import pprint
from dotenv import load_dotenv

# Thiết lập logging cơ bản
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Tải biến môi trường
load_dotenv()

def test_individual_analyzers():
    """Kiểm tra hoạt động của từng analyzer riêng lẻ."""
    try:
        from src.core.data.models import (
            SensorType,
            LightReading,
            TemperatureReading,
            HumidityReading,
            SoilMoistureReading
        )
        from src.core.environment.analyzers import (
            LightAnalyzer,
            TemperatureAnalyzer,
            HumidityAnalyzer,
            SoilMoistureAnalyzer
        )
        
        # Tạo dữ liệu mẫu
        now = datetime.now()
        
        # Độ ẩm đất cực thấp
        soil_reading_dry = SoilMoistureReading(
            sensor_type=SensorType.SOIL_MOISTURE,
            value=15.0,
            unit="%",
            timestamp=now
        )
        
        # Độ ẩm đất bình thường
        soil_reading_normal = SoilMoistureReading(
            sensor_type=SensorType.SOIL_MOISTURE,
            value=55.0,
            unit="%",
            timestamp=now
        )
        
        # Nhiệt độ cao
        temp_reading_high = TemperatureReading(
            sensor_type=SensorType.TEMPERATURE,
            value=38.0,
            unit="°C",
            timestamp=now
        )
        
        # Độ ẩm không khí thấp
        humidity_reading_low = HumidityReading(
            sensor_type=SensorType.HUMIDITY,
            value=25.0,
            unit="%",
            timestamp=now
        )
        
        # Ánh sáng tối
        light_reading_low = LightReading(
            sensor_type=SensorType.LIGHT,
            value=100.0,
            unit="lux",
            timestamp=now
        )
        
        # Khởi tạo các analyzer
        soil_analyzer = SoilMoistureAnalyzer()
        temp_analyzer = TemperatureAnalyzer()
        humidity_analyzer = HumidityAnalyzer()
        light_analyzer = LightAnalyzer()
        
        # Phân tích từng loại dữ liệu
        logger.info("=== Testing Soil Moisture Analyzer ===")
        soil_result_dry = soil_analyzer.analyze(soil_reading_dry)
        logger.info(f"Soil Moisture (Dry): {soil_reading_dry.value}%")
        logger.info(f"Analysis: {json.dumps(soil_result_dry, indent=2, default=str)}")
        
        soil_result_normal = soil_analyzer.analyze(soil_reading_normal)
        logger.info(f"\nSoil Moisture (Normal): {soil_reading_normal.value}%")
        logger.info(f"Analysis: {json.dumps(soil_result_normal, indent=2, default=str)}")
        
        logger.info("\n=== Testing Temperature Analyzer ===")
        temp_result = temp_analyzer.analyze(temp_reading_high)
        logger.info(f"Temperature (High): {temp_reading_high.value}°C")
        logger.info(f"Analysis: {json.dumps(temp_result, indent=2, default=str)}")
        
        logger.info("\n=== Testing Humidity Analyzer ===")
        humidity_result = humidity_analyzer.analyze(humidity_reading_low)
        logger.info(f"Humidity (Low): {humidity_reading_low.value}%")
        logger.info(f"Analysis: {json.dumps(humidity_result, indent=2, default=str)}")
        
        logger.info("\n=== Testing Light Analyzer ===")
        light_result = light_analyzer.analyze(light_reading_low)
        logger.info(f"Light (Low): {light_reading_low.value} lux")
        logger.info(f"Analysis: {json.dumps(light_result, indent=2, default=str)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Individual analyzers test failed: {str(e)}")
        return False

def test_environment_analyzer():
    """Kiểm tra hoạt động của EnvironmentAnalyzer."""
    try:
        from src.core.data.models import (
            SensorType,
            LightReading,
            TemperatureReading,
            HumidityReading,
            SoilMoistureReading,
            EnvironmentSnapshot
        )
        from src.core.environment import EnvironmentAnalyzer
        
        # Tạo dữ liệu mẫu
        now = datetime.now()
        
        # Tạo snapshot với các điều kiện khô hạn
        dry_snapshot = EnvironmentSnapshot(
            timestamp=now,
            light=LightReading(
                sensor_type=SensorType.LIGHT,
                value=8000.0,
                unit="lux",
                timestamp=now
            ),
            temperature=TemperatureReading(
                sensor_type=SensorType.TEMPERATURE,
                value=35.0,
                unit="°C",
                timestamp=now
            ),
            humidity=HumidityReading(
                sensor_type=SensorType.HUMIDITY,
                value=30.0,
                unit="%",
                timestamp=now
            ),
            soil_moisture=SoilMoistureReading(
                sensor_type=SensorType.SOIL_MOISTURE,
                value=18.0,
                unit="%",
                timestamp=now
            )
        )
        
        # Tạo snapshot với các điều kiện bình thường
        normal_snapshot = EnvironmentSnapshot(
            timestamp=now,
            light=LightReading(
                sensor_type=SensorType.LIGHT,
                value=3000.0,
                unit="lux",
                timestamp=now
            ),
            temperature=TemperatureReading(
                sensor_type=SensorType.TEMPERATURE,
                value=25.0,
                unit="°C",
                timestamp=now
            ),
            humidity=HumidityReading(
                sensor_type=SensorType.HUMIDITY,
                value=60.0,
                unit="%",
                timestamp=now
            ),
            soil_moisture=SoilMoistureReading(
                sensor_type=SensorType.SOIL_MOISTURE,
                value=50.0,
                unit="%",
                timestamp=now
            )
        )
        
        # Khởi tạo EnvironmentAnalyzer
        env_analyzer = EnvironmentAnalyzer()
        
        # Phân tích snapshot điều kiện khô hạn
        logger.info("=== Testing EnvironmentAnalyzer with Dry Conditions ===")
        dry_result = env_analyzer.analyze_snapshot(dry_snapshot)
        logger.info(f"Overall Status: {dry_snapshot.get_overall_status()}")
        logger.info(f"Soil Moisture: {dry_snapshot.soil_moisture.value}%")
        logger.info(f"Temperature: {dry_snapshot.temperature.value}°C")
        logger.info(f"Humidity: {dry_snapshot.humidity.value}%")
        logger.info(f"Light: {dry_snapshot.light.value} lux")
        logger.info("\nIrrigation Recommendation:")
        logger.info(f"  Needs Water: {dry_result['irrigation_recommendation']['needs_water']}")
        logger.info(f"  Urgency: {dry_result['irrigation_recommendation']['urgency']}")
        logger.info(f"  Reason: {dry_result['irrigation_recommendation']['reason']}")
        logger.info(f"  Water Amount: {dry_result['irrigation_recommendation']['recommended_water_amount']}")
        
        logger.info("\nAction Items:")
        for item in dry_result['action_items']:
            logger.info(f"  - {item['action']} (Priority: {item['priority']})")
            logger.info(f"    {item['details']}")
        
        # Phân tích snapshot điều kiện bình thường
        logger.info("\n=== Testing EnvironmentAnalyzer with Normal Conditions ===")
        normal_result = env_analyzer.analyze_snapshot(normal_snapshot)
        logger.info(f"Overall Status: {normal_snapshot.get_overall_status()}")
        logger.info(f"Soil Moisture: {normal_snapshot.soil_moisture.value}%")
        logger.info(f"Temperature: {normal_snapshot.temperature.value}°C")
        logger.info(f"Humidity: {normal_snapshot.humidity.value}%")
        logger.info(f"Light: {normal_snapshot.light.value} lux")
        logger.info("\nIrrigation Recommendation:")
        logger.info(f"  Needs Water: {normal_result['irrigation_recommendation']['needs_water']}")
        logger.info(f"  Urgency: {normal_result['irrigation_recommendation']['urgency']}")
        logger.info(f"  Reason: {normal_result['irrigation_recommendation']['reason']}")
        logger.info(f"  Water Amount: {normal_result['irrigation_recommendation']['recommended_water_amount']}")
        
        logger.info("\nAction Items:")
        if normal_result['action_items']:
            for item in normal_result['action_items']:
                logger.info(f"  - {item['action']} (Priority: {item['priority']})")
                logger.info(f"    {item['details']}")
        else:
            logger.info("  No action items needed")
        
        return True
    except Exception as e:
        logger.error(f"❌ Environment analyzer test failed: {str(e)}")
        return False

def test_real_data_analysis():
    """Kiểm tra phân tích dữ liệu thực từ Adafruit."""
    try:
        from src.core.data import DataManager
        from src.core.environment import EnvironmentAnalyzer
        
        # Khởi tạo DataManager và EnvironmentAnalyzer
        data_manager = DataManager()
        env_analyzer = EnvironmentAnalyzer()
        
        # Thu thập dữ liệu mới nhất
        logger.info("=== Testing Analysis with Real Sensor Data ===")
        logger.info("Collecting latest sensor data...")
        
        readings = data_manager.collect_all_latest_data()
        if not readings:
            logger.warning("No sensor data available from Adafruit")
            return False
            
        # Tạo snapshot
        snapshot = data_manager.get_environment_snapshot(collect_if_needed=False)
        
        # Phân tích snapshot
        logger.info("Analyzing environment snapshot...")
        analysis = env_analyzer.analyze_snapshot(snapshot)
        
        # Hiển thị kết quả
        logger.info(f"Overall Status: {snapshot.get_overall_status()}")
        
        if snapshot.soil_moisture:
            logger.info(f"Soil Moisture: {snapshot.soil_moisture.value}%")
        if snapshot.temperature:
            logger.info(f"Temperature: {snapshot.temperature.value}°C")
        if snapshot.humidity:
            logger.info(f"Humidity: {snapshot.humidity.value}%")
        if snapshot.light:
            logger.info(f"Light: {snapshot.light.value} lux")
            
        logger.info("\nIrrigation Recommendation:")
        logger.info(f"  Needs Water: {analysis['irrigation_recommendation']['needs_water']}")
        logger.info(f"  Urgency: {analysis['irrigation_recommendation']['urgency']}")
        logger.info(f"  Reason: {analysis['irrigation_recommendation']['reason']}")
        logger.info(f"  Water Amount: {analysis['irrigation_recommendation']['recommended_water_amount']}")
        
        logger.info("\nAction Items:")
        if analysis['action_items']:
            for item in analysis['action_items']:
                logger.info(f"  - {item['action']} (Priority: {item['priority']})")
                logger.info(f"    {item['details']}")
        else:
            logger.info("  No action items needed")
        
        return True
    except Exception as e:
        logger.error(f"❌ Real data analysis test failed: {str(e)}")
        return False

def run_tests():
    """Chạy tất cả các kiểm tra phân tích."""
    logger.info("=== Testing Environment Analysis Components ===\n")
    
    logger.info("1. Testing Individual Analyzers...")
    individual_result = test_individual_analyzers()
    
    logger.info("\n2. Testing Environment Analyzer...")
    env_analyzer_result = test_environment_analyzer()
    
    logger.info("\n3. Testing Real Data Analysis...")
    real_data_result = test_real_data_analysis()
    
    logger.info("\n=== Analysis Test Results ===")
    logger.info(f"Individual Analyzers: {'✅ PASS' if individual_result else '❌ FAIL'}")
    logger.info(f"Environment Analyzer: {'✅ PASS' if env_analyzer_result else '❌ FAIL'}")
    logger.info(f"Real Data Analysis: {'✅ PASS' if real_data_result else '❌ FAIL'}")
    
    all_passed = individual_result and env_analyzer_result and real_data_result
    
    if all_passed:
        logger.info("\n🎉 All analysis tests PASSED!")
    else:
        logger.info("\n⚠️ Some analysis tests FAILED. Please check the logs above.")
        
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)