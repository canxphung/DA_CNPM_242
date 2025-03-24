# services/data_processor.py
import json
import logging
import time
from datetime import datetime
from .mqtt_service import MQTTService
from .db_service import DatabaseService
from .ai_service import AIService

logger = logging.getLogger("data_processor.processor")

class DataProcessor:

    def __init__(self):

        # Khởi tạo các services
        self.db_service = DatabaseService()
        self.ai_service = AIService()
        self.mqtt_service = MQTTService(self.process_message)
        
        logger.info("Data Processor đã được khởi tạo")
    
    def start(self):
        try:
            # Bắt đầu MQTT service để lắng nghe dữ liệu
            self.mqtt_service.start()
            logger.info("Data Processing Service đã bắt đầu")
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động Data Processing Service: {e}")
            self.stop()
            raise
    
    def stop(self):
        logger.info("Dừng Data Processing Service...")
        
        # Dừng MQTT service
        try:
            self.mqtt_service.stop()
        except Exception as e:
            logger.error(f"Lỗi khi dừng MQTT Service: {e}")
        
        # Đóng kết nối database
        try:
            self.db_service.close()
        except Exception as e:
            logger.error(f"Lỗi khi đóng kết nối Database: {e}")
            
        logger.info("Data Processing Service đã dừng")
    
    def process_message(self, feed_key, payload):

        try:
            logger.info(f"Xử lý thông điệp từ feed {feed_key}: {payload}")
            
            # Xử lý dữ liệu
            processed_data = self.process_data(feed_key, payload)
            
            # Lưu vào database
            document_id = self.db_service.save_data(processed_data)
            logger.info(f"Đã lưu dữ liệu với ID: {document_id}")
            
            # Kiểm tra xem có nên gửi đến AI Service không
            if self.ai_service.should_process(feed_key, processed_data["data"]):
                ai_result = self.ai_service.send_for_analysis(processed_data)
                
                if ai_result:
                    # Lưu kết quả AI vào database
                    ai_result["original_data_id"] = document_id
                    ai_result["feed_key"] = feed_key
                    ai_result["timestamp"] = time.time()
                    
                    self.db_service.save_data({
                        "type": "ai_result",
                        "data": ai_result
                    })
                    
                    logger.info(f"Đã lưu kết quả AI cho {feed_key}")
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý thông điệp: {e}")
    
    def process_data(self, feed_key, payload):

        try:
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:

                data = {"value": payload}
            
            # Thêm metadata
            processed_data = {
                "type": "sensor_data",
                "feed_key": feed_key,
                "timestamp": time.time(),
                "datetime": datetime.now().isoformat(),
                "data": data
            }
            
            # Logic xử lý tùy chỉnh cho từng loại feed
            if feed_key == "temperature":
                if isinstance(data, dict) and "value" in data:
                    try:
                        temp_c = float(data["value"])
                        processed_data["data"]["value_fahrenheit"] = temp_c * 9/5 + 32
                    except (ValueError, TypeError):
                        pass
            
            elif feed_key == "humidity":
                # Phân loại độ ẩm
                if isinstance(data, dict) and "value" in data:
                    try:
                        humidity = float(data["value"])
                        if humidity < 30:
                            processed_data["data"]["humidity_level"] = "low"
                        elif humidity < 60:
                            processed_data["data"]["humidity_level"] = "normal"
                        else:
                            processed_data["data"]["humidity_level"] = "high"
                    except (ValueError, TypeError):
                        pass
            
            logger.debug(f"Dữ liệu sau khi xử lý: {processed_data}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý dữ liệu: {e}")
            return {
                "type": "error",
                "feed_key": feed_key,
                "timestamp": time.time(),
                "data": {"raw_payload": payload},
                "error": str(e)
            }