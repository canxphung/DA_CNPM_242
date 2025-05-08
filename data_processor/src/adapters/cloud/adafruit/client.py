"""
Module kết nối với Adafruit IO thông qua cả HTTP API và MQTT
"""
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
import threading

# Import thư viện Adafruit
from Adafruit_IO import Client, Feed, Data, RequestError
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class AdafruitIOClient:
    """
    Lớp kết nối đến Adafruit IO qua cả HTTP API và MQTT
    """
    
    def __init__(self, username: str, key: str, 
                 max_retries: int = 3, 
                 retry_delay: float = 1.0,
                 mqtt_server: str = "io.adafruit.com",
                 mqtt_port: int = 1883):
        """
        Khởi tạo kết nối đến Adafruit IO.
        
        Args:
            username: Tên người dùng Adafruit IO
            key: Khóa API Adafruit IO
            max_retries: Số lần thử lại tối đa khi gặp lỗi kết nối
            retry_delay: Thời gian chờ giữa các lần thử lại (giây)
            mqtt_server: Địa chỉ máy chủ MQTT
            mqtt_port: Cổng máy chủ MQTT
        """
        self.username = username
        self.key = key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port
        
        # Khởi tạo client HTTP API
        self.http_client = Client(username, key)
        logger.info(f"Adafruit IO HTTP client initialized for user: {username}")
        
        # Khởi tạo client MQTT
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.username_pw_set(username, key)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        self.mqtt_running = False
        self.mqtt_connected = False
        self.message_handlers = {}  # Dict để lưu các hàm xử lý thông điệp theo feed
        logger.info(f"Adafruit IO MQTT client initialized for user: {username}")
        
    def start_mqtt(self):
        """Bắt đầu kết nối MQTT"""
        try:
            logger.info(f"Connecting to Adafruit IO MQTT at {self.mqtt_server}:{self.mqtt_port}")
            self.mqtt_client.connect(self.mqtt_server, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            self.mqtt_running = True
            # Tạo feed test để kiểm tra kết nối
            test_feed = self.create_feed_if_not_exists("test_feed")
            if not test_feed:
                logger.warning("Could not create test feed")
            retries = 0
            while not self.mqtt_connected and retries < self.max_retries:
                logger.info(f"Waiting for MQTT connection... (attempt {retries + 1}/{self.max_retries})")
                time.sleep(self.retry_delay)
                retries += 1
            
            if not self.mqtt_connected:
                logger.warning("Could not connect to Adafruit IO MQTT after multiple attempts")
                # Không raise lỗi vì vẫn có thể sử dụng HTTP API
            else:
                logger.info("MQTT connection established successfully")
                
        except Exception as e:
            logger.error(f"Error starting MQTT connection: {e}")
            self.stop_mqtt()
    
    def stop_mqtt(self):
        """Dừng kết nối MQTT"""
        if self.mqtt_running:
            logger.info("Stopping MQTT connection...")
            self.mqtt_client.loop_stop()
            if self.mqtt_connected:
                self.mqtt_client.disconnect()
            self.mqtt_running = False
            self.mqtt_connected = False
            logger.info("MQTT connection stopped")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback khi kết nối MQTT thành công"""
        if rc == 0:
            logger.info("Connected to Adafruit IO MQTT")
            self.mqtt_connected = True
            
            # Đăng ký nhận dữ liệu từ tất cả các feeds đã đăng ký handler
            for feed_key in self.message_handlers.keys():
                topic = f"{self.username}/feeds/{feed_key}"
                client.subscribe(topic)
                logger.info(f"Subscribed to feed: {feed_key}")
        else:
            conn_result = {
                1: "Incorrect protocol",
                2: "Client ID rejected",
                3: "Server unavailable",
                4: "Incorrect username/password",
                5: "Not authorized"
            }
            logger.error(f"Could not connect to Adafruit IO MQTT: {conn_result.get(rc, f'Unknown error: {rc}')}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback khi mất kết nối MQTT"""
        self.mqtt_connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection, error code: {rc}")
            # Thử kết nối lại
            threading.Timer(self.retry_delay, self.start_mqtt).start()
        else:
            logger.info("MQTT disconnected successfully")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Callback khi nhận được thông điệp MQTT"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Trích xuất feed_key từ topic (MQTT topic: username/feeds/feed_key)
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                feed_key = topic_parts[-1]
            else:
                feed_key = "unknown"
            
            logger.debug(f"Received message from {feed_key}: {payload}")
            
            # Gọi handler nếu có
            if feed_key in self.message_handlers:
                self.message_handlers[feed_key](feed_key, payload)
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def register_feed_handler(self, feed_key: str, handler: Callable[[str, str], None]):
        """
        Đăng ký hàm xử lý khi nhận dữ liệu từ feed
        
        Args:
            feed_key: Khóa của feed
            handler: Hàm xử lý với 2 tham số (feed_key, payload)
        """
        self.message_handlers[feed_key] = handler
        
        # Đăng ký subscribe ngay nếu đã kết nối MQTT
        if self.mqtt_connected:
            topic = f"{self.username}/feeds/{feed_key}"
            self.mqtt_client.subscribe(topic)
            logger.info(f"Subscribed to feed: {feed_key}")
    
    def publish(self, feed_key: str, value: Union[str, int, float, bool]) -> bool:
        """
        Gửi dữ liệu đến feed qua MQTT (nếu kết nối) hoặc HTTP API (nếu MQTT không khả dụng)
        
        Args:
            feed_key: Khóa của feed
            value: Giá trị cần gửi
            
        Returns:
            bool: Thành công hay thất bại
        """
        # Chuyển đổi giá trị thành string
        if isinstance(value, bool):
            value = "1" if value else "0"
        elif not isinstance(value, str):
            value = str(value)
        if not self.mqtt_connected:
            logger.warning("MQTT not connected. Using HTTP API instead")
        # Thử gửi qua MQTT trước
        if self.mqtt_connected:
            try:
                topic = f"{self.username}/feeds/{feed_key}"
                result = self.mqtt_client.publish(topic, value)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"Sent message to {feed_key} via MQTT: {value}")
                    return True
                else:
                    logger.warning(f"Failed to send message via MQTT, error code: {result.rc}")
                    # Tiếp tục thử với HTTP API
            except Exception as e:
                logger.warning(f"Error sending message via MQTT: {e}")
                # Tiếp tục thử với HTTP API
        
        # Thử gửi qua HTTP API nếu MQTT không thành công
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Sending data to feed {feed_key} via HTTP API: {value}")
                self.http_client.send_data(feed_key, value)
                logger.debug(f"Sent message to {feed_key} via HTTP API: {value}")
                return True
            except Exception as e:
                logger.error(f"Error sending data to feed {feed_key} via HTTP API: {str(e)}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                return False
    
    def get_feed(self, feed_key: str) -> Optional[Feed]:
        """
        Lấy thông tin về feed.
        
        Args:
            feed_key: Khóa của feed
            
        Returns:
            Feed object hoặc None nếu không tìm thấy
        """
        for attempt in range(self.max_retries):
            try:
                return self.http_client.feeds(feed_key)
            except RequestError as e:
                # Kiểm tra xem đối tượng lỗi có thuộc tính status_code không
                if hasattr(e, 'status_code'):
                    if e.status_code == 404:
                        logger.warning(f"Feed not found: {feed_key}")
                        return None
                    else:
                        logger.error(f"Error getting feed {feed_key}: HTTP {e.status_code} - {str(e)}")
                        # Thử lại nếu không phải là lần cuối cùng
                        if attempt < self.max_retries - 1:
                            logger.info(f"Retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                            time.sleep(self.retry_delay)
                            continue
                        raise
                else:
                    logger.error(f"Network error getting feed {feed_key}: {str(e)}")
                    if attempt < self.max_retries - 1:
                        logger.info(f"Retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(self.retry_delay)
                        continue
                    raise
            except Exception as e:
                logger.error(f"Error getting feed {feed_key}: {str(e)}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                raise
            
    def create_feed_if_not_exists(self, feed_key: str, retries: int = 3) -> Optional[Feed]:
        """
        Tạo feed nếu nó chưa tồn tại.
        
        Args:
            feed_key: Khóa của feed
            retries: Số lần thử lại tối đa
            
        Returns:
            Feed object hoặc None nếu không thể tạo
        """
        for attempt in range(retries):
            try:
                try:
                    # Thử kiểm tra xem feed đã tồn tại chưa
                    feed = self.http_client.feeds(feed_key)
                    logger.info(f"Feed '{feed_key}' already exists")
                    return feed
                except RequestError as e:
                    # Nếu lỗi 404, feed chưa tồn tại, cần tạo
                    if hasattr(e, 'status_code') and e.status_code == 404:
                        logger.info(f"Feed '{feed_key}' not found, creating new feed")
                        
                        # Tạo cấu trúc Feed với các thuộc tính rõ ràng
                        feed_obj = Feed()
                        feed_obj.key = feed_key
                        feed_obj.name = feed_key
                        feed_obj.description = f"Auto-created feed for {feed_key}"
                        
                        # Tạo feed mới
                        feed = self.http_client.create_feed(feed_obj)
                        logger.info(f"Successfully created feed '{feed_key}'")
                        return feed
                    else:
                        # Lỗi khác, truyền lại ngoại lệ
                        raise
            except Exception as e:
                logger.error(f"Failed to create feed '{feed_key}': {str(e)}")
                if attempt < retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Giving up creating feed '{feed_key}' after {retries} attempts")
                    return None
        return None
    
    def initialize_feeds(self, feed_keys: List[str]):
        """
        Khởi tạo danh sách các feed cần thiết.
        
        Args:
            feed_keys: Danh sách khóa của các feed
        """
        success_count = 0
        error_count = 0
        
        for key in feed_keys:
            try:
                feed = self.create_feed_if_not_exists(key)
                if feed:
                    logger.info(f"Feed '{key}' initialized successfully")
                    success_count += 1
                else:
                    logger.error(f"Failed to initialize feed '{key}'")
                    error_count += 1
            except Exception as e:
                logger.error(f"Critical error initializing feed '{key}': {str(e)}")
                error_count += 1
                
        if error_count > 0:
            logger.warning(f"Initialized {success_count}/{len(feed_keys)} feeds with {error_count} errors")
        else:
            logger.info(f"All {success_count} required feeds initialized successfully")
    
    def get_data(self, feed_key: str, limit: int = 1, auto_create: bool = True) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu từ feed.
        
        Args:
            feed_key: Khóa của feed
            limit: Số lượng điểm dữ liệu tối đa
            auto_create: Tự động tạo feed nếu không tồn tại
            
        Returns:
            List các điểm dữ liệu
        """
        for attempt in range(self.max_retries):
            try:
                data = self.http_client.data(feed_key, limit)
                result = []
                
                for d in data:
                    # Chuyển đổi thành dict và xử lý giá trị
                    item = {
                        'id': d.id,
                        'value': d.value,
                        'created_at': d.created_at
                    }
                    
                    # Thử chuyển đổi giá trị thành số
                    try:
                        if '.' in d.value:
                            item['value_converted'] = float(d.value)
                        else:
                            item['value_converted'] = int(d.value)
                    except (ValueError, TypeError):
                        pass
                        
                    result.append(item)
                    
                return result
            except RequestError as e:
                if hasattr(e, 'status_code') and e.status_code == 404:
                    logger.warning(f"Feed not found: {feed_key}")
                    
                    # Tự động tạo feed nếu được yêu cầu
                    if auto_create:
                        try:
                            logger.info(f"Attempting to create feed '{feed_key}' automatically")
                            self.create_feed_if_not_exists(feed_key)
                            # Sau khi tạo feed, feed sẽ chưa có dữ liệu nên vẫn trả về danh sách rỗng
                            logger.info(f"Feed '{feed_key}' created successfully, but it has no data yet")
                        except Exception as create_error:
                            logger.error(f"Failed to auto-create feed '{feed_key}': {str(create_error)}")
                    
                    return []
                else:
                    logger.error(f"Error getting data from feed {feed_key}: {str(e)}")
                    if attempt < self.max_retries - 1:
                        logger.info(f"Retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(self.retry_delay)
                        continue
                    return []
            except Exception as e:
                logger.error(f"Error getting data from feed {feed_key}: {str(e)}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                return []
            
    def get_last_data(self, feed_key: str, auto_create: bool = True) -> Optional[Dict[str, Any]]:
        """
        Lấy điểm dữ liệu mới nhất từ feed.
        
        Args:
            feed_key: Khóa của feed
            auto_create: Tự động tạo feed nếu không tồn tại
            
        Returns:
            Dict chứa dữ liệu mới nhất hoặc None nếu không có dữ liệu
        """
        data = self.get_data(feed_key, 1, auto_create=auto_create)
        return data[0] if data else None
            
    def turn_actuator_on(self, feed_key: str, auto_create: bool = True) -> bool:
        """
        Bật thiết bị điều khiển (gửi giá trị '1').
        
        Args:
            feed_key: Khóa của feed điều khiển
            auto_create: Tự động tạo feed nếu không tồn tại
            
        Returns:
            bool: Thành công hay thất bại
        """
        # Tạo feed nếu không tồn tại và auto_create = True
        try:
            if auto_create:
                # Sử dụng create_feed_if_not_exists trực tiếp để kiểm tra và tạo nếu cần
                feed = self.create_feed_if_not_exists(feed_key)
                if feed is None:
                    logger.error(f"Failed to ensure feed '{feed_key}' exists for actuator control")
                    return False
        except Exception as e:
            logger.error(f"Error checking/creating feed '{feed_key}': {str(e)}")

        # Gửi giá trị '1' để bật thiết bị
        result = self.publish(feed_key, "1")
        if result:
            logger.info(f"Turned ON actuator: {feed_key}")
        return result
            
    def turn_actuator_off(self, feed_key: str, auto_create: bool = True) -> bool:
        """
        Tắt thiết bị điều khiển (gửi giá trị '0').
        
        Args:
            feed_key: Khóa của feed điều khiển
            auto_create: Tự động tạo feed nếu không tồn tại
            
        Returns:
            bool: Thành công hay thất bại
        """
        # Tạo feed nếu không tồn tại và auto_create = True
        try:
            if auto_create:
                # Sử dụng create_feed_if_not_exists trực tiếp để kiểm tra và tạo nếu cần
                feed = self.create_feed_if_not_exists(feed_key)
                if feed is None:
                    logger.error(f"Failed to ensure feed '{feed_key}' exists for actuator control")
                    return False
        except Exception as e:
            logger.error(f"Error checking/creating feed '{feed_key}': {str(e)}")
            
        # Gửi giá trị '0' để tắt thiết bị
        result = self.publish(feed_key, "0")
        if result:
            logger.info(f"Turned OFF actuator: {feed_key}")
        return result
            
    def get_actuator_state(self, feed_key: str, auto_create: bool = True) -> Optional[bool]:
        """
        Lấy trạng thái hiện tại của thiết bị điều khiển.
        
        Args:
            feed_key: Khóa của feed điều khiển
            auto_create: Tự động tạo feed nếu không tồn tại
            
        Returns:
            bool: True nếu đang bật, False nếu đang tắt, None nếu không xác định
        """
        for attempt in range(self.max_retries):
            try:
                data = self.get_last_data(feed_key, auto_create=auto_create)
                if data:
                    # Trạng thái bật: "1", "ON", "TRUE", v.v.
                    value = data.get('value', '').strip().upper()
                    if value in ('1', 'ON', 'TRUE', 'YES'):
                        return True
                    # Trạng thái tắt: "0", "OFF", "FALSE", v.v.
                    elif value in ('0', 'OFF', 'FALSE', 'NO'):
                        return False
                return None
            except Exception as e:
                logger.error(f"Error getting actuator state for {feed_key}: {str(e)}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                return None


# End of AdafruitIOClient class