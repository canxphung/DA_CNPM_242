# services/mqtt_service.py
import logging
import time
import paho.mqtt.client as mqtt
from config import Config

logger = logging.getLogger("data_processor.mqtt")

class MQTTService:
    
    def __init__(self, message_handler):

        self.message_handler = message_handler
        self.client = mqtt.Client()
        self.client.username_pw_set(Config.ADAFRUIT_IO_USERNAME, Config.ADAFRUIT_IO_KEY)
        
        # Đăng ký các callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        self.running = False
        self.connected = False
        
        logger.info("MQTT Service đã được khởi tạo")
    
    def start(self):
        try:
            logger.info(f"Kết nối đến Adafruit IO MQTT tại {Config.ADAFRUIT_IO_SERVER}:{Config.ADAFRUIT_IO_PORT}")
            self.client.connect(Config.ADAFRUIT_IO_SERVER, Config.ADAFRUIT_IO_PORT, 60)
            self.client.loop_start()
            self.running = True
            
            retries = 0
            while not self.connected and retries < Config.MAX_RECONNECT_ATTEMPTS:
                logger.info(f"Đang đợi kết nối MQTT... (lần thử {retries + 1}/{Config.MAX_RECONNECT_ATTEMPTS})")
                time.sleep(Config.RECONNECT_DELAY)
                retries += 1
            
            if not self.connected:
                raise ConnectionError("Không thể kết nối đến Adafruit IO MQTT sau nhiều lần thử")
                
            logger.info("MQTT Service đã khởi động thành công")
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động MQTT Service: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Dừng kết nối MQTT và dọn dẹp tài nguyên"""
        if self.running:
            logger.info("Dừng MQTT Service...")
            self.client.loop_stop()
            if self.connected:
                self.client.disconnect()
            self.running = False
            self.connected = False
            logger.info("MQTT Service đã dừng")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback khi kết nối MQTT thành công"""
        if rc == 0:
            logger.info("Đã kết nối đến Adafruit IO MQTT")
            self.connected = True
            
            # Đăng ký nhận dữ liệu từ tất cả các feeds đã cấu hình
            for feed_key in Config.ADAFRUIT_FEED_KEYS:
                topic = f"{Config.ADAFRUIT_IO_USERNAME}/feeds/{feed_key}"
                client.subscribe(topic)
                logger.info(f"Đã đăng ký nhận dữ liệu từ feed: {feed_key}")
        else:
            conn_result = {
                1: "Giao thức không đúng",
                2: "ID Client bị từ chối",
                3: "Server không khả dụng",
                4: "Tên đăng nhập/mật khẩu không đúng",
                5: "Không được phép kết nối"
            }
            logger.error(f"Không thể kết nối đến Adafruit IO MQTT: {conn_result.get(rc, f'Lỗi không xác định: {rc}')}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback khi mất kết nối MQTT"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Mất kết nối MQTT không mong muốn, mã lỗi: {rc}")
        else:
            logger.info("Ngắt kết nối MQTT thành công")
    
    def _on_message(self, client, userdata, msg):
        """Callback khi nhận được thông điệp MQTT"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Trích xuất feed_key từ topic
            # MQTT topic: username/feeds/feed_key
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                feed_key = topic_parts[-1]
            else:
                feed_key = "unknown"
            
            logger.debug(f"Nhận được thông điệp từ {feed_key}: {payload}")
            

            self.message_handler(feed_key, payload)
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý thông điệp MQTT: {e}")
    
    def publish(self, feed_key, message):
        
        if not self.connected:
            logger.error("Không thể gửi thông điệp: Không có kết nối MQTT")
            return False
        
        try:
            topic = f"{Config.ADAFRUIT_IO_USERNAME}/feeds/{feed_key}"
            result = self.client.publish(topic, message)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Đã gửi thông điệp đến {feed_key}: {message}")
                return True
            else:
                logger.error(f"Không thể gửi thông điệp đến {feed_key}, mã lỗi: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông điệp MQTT: {e}")
            return False