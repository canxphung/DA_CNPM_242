## 9. Kiểm Tra Toàn Bộ Hệ Thống

### Tạo tệp `test_system.py` tại thư mục gốc:

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
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

# Cấu hình API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
BASE_URL = f"http://{API_HOST}:{API_PORT}"

def test_api_health():
    """Kiểm tra endpoint health của API."""
    url = f"{BASE_URL}/health"
    
    try:
        logger.info(f"Testing API health at {url}")
        response = requests.get(url)
        
        logger.info(f"Status code: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            logger.info("✅ API health check passed")
            logger.info(f"API status: {data.get('status')}")
            logger.info(f"Sensor status: {data.get('sensors', {}).get('status')}")
            logger.info(f"Pump status: {data.get('irrigation', {}).get('pump_status')}")
            return True
        else:
            logger.error(f"❌ API health check failed: {data}")
            return False
    except Exception as e:
        logger.error(f"❌ API health check error: {str(e)}")
        return False

def test_sensors_endpoints():
    """Kiểm tra các endpoint liên quan đến cảm biến."""
    endpoints = [
        "/api/sensors",
        "/api/sensors/snapshot",
        "/api/sensors/analyze"
    ]
    
    success = True
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        try:
            logger.info(f"Testing endpoint: {url}")
            response = requests.get(url)
            
            logger.info(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Response: {json.dumps(data, indent=2, default=str)[:200]}...")
                logger.info(f"✅ Endpoint {endpoint} passed")
            else:
                logger.error(f"❌ Endpoint {endpoint} failed: {response.text}")
                success = False
        except Exception as e:
            logger.error(f"❌ Error testing endpoint {endpoint}: {str(e)}")
            success = False
            
    return success

def test_control_endpoints():
    """Kiểm tra các endpoint liên quan đến điều khiển."""
    endpoints = [
        "/api/control/status",
        "/api/control/history",
        "/api/control/schedules",
        "/api/control/auto"
    ]
    
    success = True
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        try:
            logger.info(f"Testing endpoint: {url}")
            response = requests.get(url)
            
            logger.info(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Response: {json.dumps(data, indent=2, default=str)[:200]}...")
                logger.info(f"✅ Endpoint {endpoint} passed")
            else:
                logger.error(f"❌ Endpoint {endpoint} failed: {response.text}")
                success = False
        except Exception as e:
            logger.error(f"❌ Error testing endpoint {endpoint}: {str(e)}")
            success = False
            
    return success

def test_system_endpoints():
    """Kiểm tra các endpoint liên quan đến hệ thống."""
    endpoints = [
        "/api/system/info",
        "/api/system/config",
        "/version"
    ]
    
    success = True
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        try:
            logger.info(f"Testing endpoint: {url}")
            response = requests.get(url)
            
            logger.info(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Response: {json.dumps(data, indent=2, default=str)[:200]}...")
                logger.info(f"✅ Endpoint {endpoint} passed")
            else:
                logger.error(f"❌ Endpoint {endpoint} failed: {response.text}")
                success = False
        except Exception as e:
            logger.error(f"❌ Error testing endpoint {endpoint}: {str(e)}")
            success = False
            
    return success

def test_pump_control():
    """Kiểm tra điều khiển máy bơm."""
    # Lấy trạng thái máy bơm
    url_status = f"{BASE_URL}/api/control/pump/status"
    
    try:
        logger.info(f"Getting pump status from {url_status}")
        response = requests.get(url_status)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to get pump status: {response.text}")
            return False
            
        pump_status = response.json()
        logger.info(f"Current pump status: {'ON' if pump_status.get('is_on') else 'OFF'}")
        
        # Nếu máy bơm đang bật, tắt trước
        if pump_status.get("is_on"):
            url_off = f"{BASE_URL}/api/control/pump/off"
            logger.info(f"Turning pump OFF: {url_off}")
            
            response = requests.post(url_off)
            if response.status_code != 200:
                logger.error(f"❌ Failed to turn pump OFF: {response.text}")
                return False
                
            logger.info("Pump turned OFF successfully")
            time.sleep(2)  # Đợi 2 giây
        
        # Bật máy bơm trong 5 giây
        url_on = f"{BASE_URL}/api/control/pump/on?duration=5"
        logger.info(f"Turning pump ON for 5 seconds: {url_on}")
        
        response = requests.post(url_on)
        if response.status_code != 200:
            logger.error(f"❌ Failed to turn pump ON: {response.text}")
            return False
            
        logger.info("Pump turned ON successfully")
        
        # Kiểm tra trạng thái sau khi bật
        response = requests.get(url_status)
        pump_status = response.json()
        
        if not pump_status.get("is_on"):
            logger.error("❌ Pump should be ON but status shows OFF")
            return False
            
        logger.info("Pump status correctly shows ON")
        
        # Đợi máy bơm tự động tắt
        logger.info("Waiting for pump to turn OFF automatically...")
        time.sleep(7)  # Đợi 7 giây (5s + buffer)
        
        # Kiểm tra trạng thái sau khi tự động tắt
        response = requests.get(url_status)
        pump_status = response.json()
        
        if pump_status.get("is_on"):
            logger.error("❌ Pump should be OFF but status still shows ON")
            return False
            
        logger.info("✅ Pump control test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Pump control test error: {str(e)}")
        return False

def test_schedule_management():
    """Kiểm tra quản lý lịch tưới."""
    base_url = f"{BASE_URL}/api/control/schedules"
    
    try:
        # Lấy danh sách lịch trình
        logger.info(f"Getting schedules from {base_url}")
        response = requests.get(base_url)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to get schedules: {response.text}")
            return False
            
        initial_schedules = response.json().get("schedules", [])
        logger.info(f"Current schedules: {len(initial_schedules)}")
        
        # Tạo lịch trình mới
        new_schedule = {
            "name": "Test Schedule",
            "days": ["monday", "wednesday", "friday"],
            "start_time": datetime.now().strftime("%H:%M"),
            "duration": 10,
            "description": "Created by test script"
        }
        
        logger.info(f"Creating new schedule: {json.dumps(new_schedule, indent=2)}")
        response = requests.post(base_url, json=new_schedule)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to create schedule: {response.text}")
            return False
            
        created_schedule = response.json().get("schedule", {})
        schedule_id = created_schedule.get("id")
        
        if not schedule_id:
            logger.error("❌ Created schedule has no ID")
            return False
            
        logger.info(f"Schedule created with ID: {schedule_id}")
        
        # Cập nhật lịch trình
        update_data = {
            "name": "Updated Test Schedule",
            "duration": 15
        }
        
        logger.info(f"Updating schedule {schedule_id}: {json.dumps(update_data, indent=2)}")
        response = requests.put(f"{base_url}/{schedule_id}", json=update_data)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to update schedule: {response.text}")
            return False
            
        logger.info("Schedule updated successfully")
        
        # Xóa lịch trình
        logger.info(f"Deleting schedule {schedule_id}")
        response = requests.delete(f"{base_url}/{schedule_id}")
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to delete schedule: {response.text}")
            return False
            
        logger.info("Schedule deleted successfully")
        
        # Kiểm tra lại danh sách sau khi xóa
        response = requests.get(base_url)
        final_schedules = response.json().get("schedules", [])
        
        if len(final_schedules) != len(initial_schedules):
            logger.error(f"❌ Schedule count mismatch after deletion: {len(final_schedules)} vs {len(initial_schedules)}")
            return False
            
        logger.info("✅ Schedule management test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Schedule management test error: {str(e)}")
        return False

def run_tests():
    """Chạy tất cả các bài kiểm tra."""
    logger.info("=== Running System Integration Tests ===\n")
    
    tests = [
        ("API Health", test_api_health),
        ("Sensors Endpoints", test_sensors_endpoints),
        ("Control Endpoints", test_control_endpoints),
        ("System Endpoints", test_system_endpoints),
        ("Pump Control", test_pump_control),
        ("Schedule Management", test_schedule_management)
    ]
    
    results = {}
    all_passed = True
    
    for name, test_func in tests:
        logger.info(f"\n--- Testing: {name} ---")
        
        try:
            result = test_func()
            results[name] = result
            
            if not result:
                all_passed = False
        except Exception as e:
            logger.error(f"❌ Unexpected error in {name} test: {str(e)}")
            results[name] = False
            all_passed = False
    
    logger.info("\n=== Test Results ===")
    
    for name, result in results.items():
        logger.info(f"{name}: {'✅ PASS' if result else '❌ FAIL'}")
    
    if all_passed:
        logger.info("\n🎉 All tests PASSED!")
    else:
        logger.info("\n⚠️ Some tests FAILED. Please check the logs above.")
        
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)