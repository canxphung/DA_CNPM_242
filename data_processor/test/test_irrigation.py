"""
Script kiểm tra hệ thống tưới.
"""
import os
import sys
import json
import time
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

def test_water_pump_controller():
    """Kiểm tra bộ điều khiển máy bơm nước."""
    try:
        from src.adapters.cloud.adafruit.actuators import WaterPumpController
        
        pump_controller = WaterPumpController()
        
        # Lấy trạng thái hiện tại
        logger.info("Getting current pump status...")
        status = pump_controller.get_status()
        logger.info(f"Current status: {'ON' if status['is_on'] else 'OFF'}")
        
        # Nếu máy bơm đang bật, thử tắt nó
        if status["is_on"]:
            logger.info("Pump is currently ON. Turning it OFF...")
            result = pump_controller.turn_off(source="test")
            logger.info(f"Result: {json.dumps(result, indent=2, default=str)}")
            
            # Lấy trạng thái sau khi tắt
            time.sleep(2)  # Đợi 2 giây để Adafruit cập nhật
            status = pump_controller.get_status()
            logger.info(f"Status after turning OFF: {'ON' if status['is_on'] else 'OFF'}")
            
            if status["is_on"]:
                logger.error("❌ Failed to turn OFF pump")
                return False
        
        # Bật máy bơm trong 5 giây
        logger.info("Turning pump ON for 5 seconds...")
        result = pump_controller.turn_on(duration=5, source="test")
        logger.info(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        # Lấy trạng thái sau khi bật
        time.sleep(2)  # Đợi 2 giây để Adafruit cập nhật
        status = pump_controller.get_status()
        logger.info(f"Status after turning ON: {'ON' if status['is_on'] else 'OFF'}")
        
        if not status["is_on"]:
            logger.error("❌ Failed to turn ON pump")
            return False
            
        # Đợi máy bơm tự động tắt
        logger.info("Waiting for pump to turn OFF automatically...")
        time.sleep(6)  # Đợi 6 giây (5s + buffer)
        
        # Lấy trạng thái sau khi máy bơm tự động tắt
        status = pump_controller.get_status()
        logger.info(f"Status after auto-off: {'ON' if status['is_on'] else 'OFF'}")
        
        # Lấy thống kê
        stats = pump_controller.calculate_statistics()
        logger.info("Pump statistics:")
        logger.info(f"  Total runtime: {stats['total_runtime_seconds']:.1f} seconds")
        logger.info(f"  Total water used: {stats['total_water_used_liters']:.2f} liters")
        
        return not status["is_on"]  # Thành công nếu máy bơm đã tắt
    except Exception as e:
        logger.error(f"❌ Water pump controller test failed: {str(e)}")
        return False

def test_irrigation_scheduler():
    """Kiểm tra bộ lập lịch tưới."""
    try:
        from src.core.control.scheduling import IrrigationScheduler
        
        scheduler = IrrigationScheduler()
        
        # Lấy danh sách lịch trình hiện tại
        schedules = scheduler.get_schedules()
        logger.info(f"Current schedules: {len(schedules)}")
        
        # Tạo lịch trình mới
        new_schedule = {
            "name": "Test Schedule",
            "days": ["monday", "wednesday", "friday"],
            "start_time": datetime.now().strftime("%H:%M"),  # Thời gian hiện tại
            "duration": 10,  # 10 giây
            "description": "Created by test script"
        }
        
        logger.info(f"Creating new schedule: {json.dumps(new_schedule, indent=2)}")
        result = scheduler.add_schedule(new_schedule)
        
        if not result["success"]:
            logger.error(f"❌ Failed to create schedule: {result['message']}")
            return False
            
        logger.info(f"Schedule created with ID: {result['schedule']['id']}")
        
        # Lấy danh sách lịch trình sau khi tạo
        schedules = scheduler.get_schedules()
        logger.info(f"Schedules after creation: {len(schedules)}")
        
        # Kiểm tra thủ công lịch trình
        check_result = scheduler.check_schedules()
        logger.info(f"Manual schedule check result: {len(check_result['matched_schedules'])} matched schedules")
        
        if check_result['matched_schedules']:
            logger.info("Schedule matched!")
            for action in check_result['actions_taken']:
                logger.info(f"  Action: {action['action']} - {action['message']}")
        
        # Cập nhật lịch trình
        schedule_id = result['schedule']['id']
        update_data = {
            "name": "Updated Test Schedule",
            "duration": 15
        }
        
        logger.info(f"Updating schedule {schedule_id}: {json.dumps(update_data, indent=2)}")
        update_result = scheduler.update_schedule(schedule_id, update_data)
        
        if not update_result["success"]:
            logger.error(f"❌ Failed to update schedule: {update_result['message']}")
            return False
            
        logger.info("Schedule updated successfully")
        
        # Xóa lịch trình
        logger.info(f"Deleting schedule {schedule_id}")
        delete_result = scheduler.delete_schedule(schedule_id)
        
        if not delete_result["success"]:
            logger.error(f"❌ Failed to delete schedule: {delete_result['message']}")
            return False
            
        logger.info("Schedule deleted successfully")
        
        # Lấy danh sách lịch trình sau khi xóa
        schedules = scheduler.get_schedules()
        logger.info(f"Schedules after deletion: {len(schedules)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Irrigation scheduler test failed: {str(e)}")
        return False

def test_irrigation_decision_maker():
    """Kiểm tra hệ thống quyết định tưới tự động."""
    try:
        from src.core.control.irrigation import IrrigationDecisionMaker
        
        decision_maker = IrrigationDecisionMaker()
        
        # Lấy cấu hình hiện tại
        config = decision_maker.get_configuration()
        logger.info(f"Current configuration: {json.dumps(config, indent=2, default=str)}")
        
        # Bật tưới tự động
        logger.info("Enabling auto irrigation...")
        result = decision_maker.enable_auto_irrigation(True)
        logger.info(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        # Kiểm tra xem có thể đưa ra quyết định không
        logger.info("Checking if can make decision...")
        check_result = decision_maker.can_make_decision()
        logger.info(f"Can make decision: {check_result['can_decide']}")
        
        if not check_result['can_decide']:
            logger.info(f"Reason: {check_result['reason']}")
            
            if 'time_remaining' in check_result:
                logger.info(f"Time remaining: {check_result['time_remaining']:.1f} seconds")
        
        # Thử đưa ra quyết định
        logger.info("Making irrigation decision...")
        decision_result = decision_maker.make_decision()
        logger.info(f"Decision result: {json.dumps(decision_result, indent=2, default=str)}")
        
        # Lấy lịch sử quyết định
        history = decision_maker.get_decision_history()
        logger.info(f"Decision history: {len(history)} entries")
        
        if history:
            logger.info(f"Latest decision: {history[0]['timestamp']}")
            logger.info(f"  Needs water: {history[0]['needs_water']}")
            logger.info(f"  Reason: {history[0]['reason']}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Irrigation decision maker test failed: {str(e)}")
        return False

def test_irrigation_manager():
    """Kiểm tra trình quản lý tưới tổng hợp."""
    try:
        from src.core.control import IrrigationManager
        
        manager = IrrigationManager()
        
        # Lấy trạng thái hệ thống
        logger.info("Getting system status...")
        status = manager.get_system_status()
        logger.info(f"Pump status: {'ON' if status['pump']['is_on'] else 'OFF'}")
        logger.info(f"Auto irrigation: {'Enabled' if status['auto_irrigation']['enabled'] else 'Disabled'}")
        logger.info(f"Schedules: {status['scheduler']['schedules_count']}")
        
        # Lấy lịch sử tưới
        logger.info("Getting irrigation history...")
        history = manager.get_irrigation_history()
        logger.info(f"Irrigation events: {len(history['irrigation_events'])}")
        logger.info(f"Auto decisions: {len(history['auto_decisions'])}")
        
        # Thử kích hoạt quyết định tưới thủ công
        logger.info("Triggering manual decision...")
        result = manager.trigger_manual_decision()
        logger.info(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Irrigation manager test failed: {str(e)}")
        return False

def run_tests():
    """Chạy tất cả các kiểm tra hệ thống tưới."""
    logger.info("=== Testing Irrigation System Components ===\n")
    
    logger.info("1. Testing Water Pump Controller...")
    pump_result = test_water_pump_controller()
    
    logger.info("\n2. Testing Irrigation Scheduler...")
    scheduler_result = test_irrigation_scheduler()
    
    logger.info("\n3. Testing Irrigation Decision Maker...")
    decision_result = test_irrigation_decision_maker()
    
    logger.info("\n4. Testing Irrigation Manager...")
    manager_result = test_irrigation_manager()
    
    logger.info("\n=== Irrigation Test Results ===")
    logger.info(f"Water Pump Controller: {'✅ PASS' if pump_result else '❌ FAIL'}")
    logger.info(f"Irrigation Scheduler: {'✅ PASS' if scheduler_result else '❌ FAIL'}")
    logger.info(f"Irrigation Decision Maker: {'✅ PASS' if decision_result else '❌ FAIL'}")
    logger.info(f"Irrigation Manager: {'✅ PASS' if manager_result else '❌ FAIL'}")
    
    all_passed = pump_result and scheduler_result and decision_result and manager_result
    
    if all_passed:
        logger.info("\n🎉 All irrigation tests PASSED!")
    else:
        logger.info("\n⚠️ Some irrigation tests FAILED. Please check the logs above.")
        
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)