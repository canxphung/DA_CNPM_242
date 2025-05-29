import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Union, Callable
import threading

from Adafruit_IO import Client, Feed, Group, Data, RequestError # Added Group
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

class AdafruitIOClient:
    AIO_BASE_URL = "https://io.adafruit.com/api/v2"

    def __init__(self, username: str, key: str,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 mqtt_server: str = "io.adafruit.com",
                 mqtt_port: int = 1883):
        self.username = username
        self.key = key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port

        if not username or not key:
            msg = "Adafruit IO username and key must be provided."
            logger.critical(msg)
            raise ValueError(msg)

        self.http_client = Client(username, key)
        logger.info(f"Adafruit IO HTTP client initialized for user: {username}")

        mqtt_client_id = f"aio_client_{username}_{os.getpid()}_{time.time_ns()}"
        self.mqtt_client = mqtt.Client(client_id=mqtt_client_id)
        self.mqtt_client.username_pw_set(username, key)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.on_message = self._on_mqtt_message

        self.mqtt_running = False
        self.mqtt_connected = False
        self.message_handlers: Dict[str, Callable[[str, str], None]] = {}
        self.subscribed_mqtt_feeds: set[str] = set()
        logger.info(f"Adafruit IO MQTT client initialized for user: {username}, client_id: {mqtt_client_id}")

    # ... (MQTT methods: start_mqtt, stop_mqtt, _on_mqtt_connect, _on_mqtt_disconnect, _on_mqtt_message - can remain largely the same) ...
    def start_mqtt(self):
        if self.mqtt_running and self.mqtt_connected:
            logger.info("MQTT client is already running and connected.")
            return
        if self.mqtt_running and not self.mqtt_connected:
            logger.info("MQTT client is running but not connected, attempting to reconnect logic might be active or use stop then start.")
            # Potentially stop and restart if stuck
            # self.stop_mqtt()
            # time.sleep(1)

        try:
            logger.info(f"Connecting to Adafruit IO MQTT at {self.mqtt_server}:{self.mqtt_port}")
            self.mqtt_client.connect(self.mqtt_server, self.mqtt_port, 60)
            self.mqtt_client.loop_start() # Starts a new thread
            self.mqtt_running = True

            wait_time = 0
            max_wait_duration = self.max_retries * (self.retry_delay + 1)
            while not self.mqtt_connected and wait_time < max_wait_duration:
                logger.info(f"Waiting for MQTT connection... ({int(wait_time / self.retry_delay) + 1})")
                time.sleep(self.retry_delay)
                wait_time += self.retry_delay

            if not self.mqtt_connected:
                logger.warning(f"Could not establish MQTT connection after {max_wait_duration:.1f}s. MQTT features may be unavailable. Check credentials and network.")
            else:
                logger.info("MQTT connection process initiated successfully (on_connect will confirm).")

        except Exception as e:
            logger.error(f"Error starting MQTT connection: {e}", exc_info=True)
            self.stop_mqtt()

    def stop_mqtt(self):
        if self.mqtt_running:
            logger.info("Stopping MQTT connection...")
            self.mqtt_client.loop_stop()
            if self.mqtt_connected:
                try:
                    self.mqtt_client.disconnect()
                except Exception as e:
                    logger.warning(f"Error during MQTT disconnect: {e}")
            self.mqtt_running = False
            self.mqtt_connected = False
            self.subscribed_mqtt_feeds.clear()
            logger.info("MQTT connection stopped.")

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Successfully connected to Adafruit IO MQTT (RC=0). Flags: {flags}")
            self.mqtt_connected = True
            current_handlers_keys = list(self.message_handlers.keys())
            for feed_key in current_handlers_keys:
                if feed_key not in self.subscribed_mqtt_feeds:
                    topic = f"{self.username}/feeds/{feed_key}" # Standard feed topic for MQTT
                    # If using group-specific topics for MQTT (less common for Adafruit IO general feeds):
                    # topic = f"{self.username}/groups/{group_key_if_known}/feeds/{feed_key}"
                    sub_result, mid = client.subscribe(topic)
                    if sub_result == mqtt.MQTT_ERR_SUCCESS:
                        self.subscribed_mqtt_feeds.add(feed_key)
                        logger.info(f"MQTT: Re/Subscribed to feed: {feed_key} (mid: {mid})")
                    else:
                        logger.warning(f"MQTT: Failed to re/subscribe to feed {feed_key}, result code: {sub_result}")
        else:
            conn_rc_codes = {1: "Incorrect protocol version", 2: "Invalid client identifier",
                             3: "Server unavailable", 4: "Bad username or password (AIO Key)",
                             5: "Not authorized"}
            logger.error(f"MQTT Connection Failed: RC={rc} - {conn_rc_codes.get(rc, 'Unknown error')}. "
                         "Please check Adafruit IO Username and Key.")
            self.mqtt_connected = False

    def _on_mqtt_disconnect(self, client, userdata, rc):
        self.mqtt_connected = False
        self.subscribed_mqtt_feeds.clear()
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (RC={rc}). Reconnection might be attempted by application logic.")
        else:
            logger.info("MQTT disconnected successfully (RC=0).")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            # Topic parsing for username/feeds/feed_key or username/groups/group_key/feeds/feed_key
            topic_parts = topic.split('/')
            feed_key = "unknown"
            if 'feeds' in topic_parts:
                feed_key_index = topic_parts.index('feeds') + 1
                if feed_key_index < len(topic_parts):
                    feed_key = topic_parts[feed_key_index]

            logger.debug(f"MQTT: Received from '{feed_key}' (topic: {topic}): {payload}")
            if feed_key in self.message_handlers:
                self.message_handlers[feed_key](feed_key, payload)
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)


    def create_group_if_not_exists(self, group_key: str, group_name: Optional[str] = None,
                                   description: Optional[str] = None, retries: Optional[int] = None) -> Optional[Group]:
        """
        Creates a group on Adafruit IO if it doesn't exist.
        """
        num_retries = retries if retries is not None else self.max_retries
        actual_group_name = group_name if group_name else group_key
        actual_description = description if description else f"Auto-created group {group_key}"

        for attempt in range(num_retries):
            try:
                logger.debug(f"HTTP: Checking if group '{group_key}' exists (Attempt {attempt + 1}/{num_retries})...")
                existing_group = self.http_client.groups(group_key) # GET /api/v2/{username}/groups/{group_key}
                logger.info(f"HTTP: Group '{group_key}' (Name: {existing_group.name}) already exists.")
                return existing_group
            except RequestError as e:
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
                    logger.info(f"HTTP: Group '{group_key}' not found. Attempting to create (Attempt {attempt + 1}/{num_retries})...")
                    try:
                        # The library can take a Group object or just name/key for simple creation
                        group_to_create = Group(key=group_key, name=actual_group_name, description=actual_description)
                        created_group = self.http_client.create_group(group_to_create) # POST /api/v2/{username}/groups
                        logger.info(f"HTTP: Successfully created group '{created_group.key}' (Name: {created_group.name}).")
                        return created_group
                    except RequestError as create_e:
                        # Handle specific errors like 401 (auth), 404 (still means auth/user issue on POST)
                        self._handle_request_error(create_e, f"create group '{group_key}'", attempt, num_retries)
                        if hasattr(create_e, 'response') and create_e.response and \
                           create_e.response.status_code in [401, 404]: # Fatal for this op
                            return None
                    except Exception as general_create_e:
                        logger.error(f"HTTP: Unexpected error creating group '{group_key}' (Attempt {attempt + 1}/{num_retries}): {general_create_e}", exc_info=True)
                else: # Other RequestError during GET (not 404)
                    self._handle_request_error(e, f"check group '{group_key}'", attempt, num_retries)
                    if hasattr(e, 'response') and e.response and e.response.status_code == 401: # Fatal
                        return None
            except Exception as ex:
                logger.error(f"HTTP: General error with group '{group_key}' (Attempt {attempt + 1}/{num_retries}): {ex}", exc_info=True)

            if attempt < num_retries - 1:
                logger.info(f"Retrying operation for group '{group_key}' in {self.retry_delay}s...")
                time.sleep(self.retry_delay)
            else:
                logger.error(f"Failed to ensure group '{group_key}' exists or is creatable after {num_retries} attempts.")
                return None
        return None

    def _handle_request_error(self, e: RequestError, action_description: str, attempt: int, num_retries: int):
        """Helper to log RequestError details."""
        err_msg = str(e)
        logger.error(f"HTTP: Failed to {action_description} (Attempt {attempt + 1}/{num_retries}): {err_msg}")
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            response_text = e.response.text[:500]
            logger.error(f"HTTP Response: Status {status_code}, Body: {response_text}")
            if status_code == 401:
                logger.critical(f"CRITICAL HTTP 401 UNAUTHORIZED while trying to {action_description}: Adafruit IO Username or Key is incorrect.")
            elif status_code == 404 and "create" in action_description.lower(): # 404 on a POST usually means auth issue
                logger.critical(f"CRITICAL HTTP 404 NOT FOUND on {action_description.upper()}: "
                                f"This usually indicates an issue with Adafruit IO Username ('{self.username}') or AIO Key.")
        return

    def create_feed_if_not_exists(self, feed_key: str, feed_name: Optional[str] = None,
                              description: Optional[str] = None, group_key: Optional[str] = None,
                              retries: Optional[int] = None) -> Optional[Feed]:
        """
        Creates a feed on Adafruit IO if it doesn't exist.
        
        The key fix here is to check the error message content when we can't 
        reliably access the status code from the RequestError.
        """
        num_retries = retries if retries is not None else self.max_retries
        actual_feed_name = feed_name if feed_name else feed_key
        actual_description = description if description else f"Auto-created feed for {feed_key}"

        # If a group_key is provided, ensure the group exists first
        if group_key:
            logger.info(f"Feed '{feed_key}' is intended for group '{group_key}'. Ensuring group exists...")
            target_group = self.create_group_if_not_exists(group_key, group_name=group_key)
            if not target_group:
                logger.error(f"Failed to create or find group '{group_key}'. Cannot create feed '{feed_key}' in this group.")
                return None
            logger.info(f"Group '{group_key}' confirmed or created.")
        else:
            target_group = None

        for attempt in range(num_retries):
            try:
                # Try to get the existing feed
                logger.debug(f"HTTP: Checking if feed '{feed_key}' exists (Attempt {attempt + 1}/{num_retries})...")
                existing_feed = self.http_client.feeds(feed_key)
                logger.info(f"HTTP: Feed '{feed_key}' (Name: {existing_feed.name}) already exists.")
                return existing_feed
                
            except RequestError as e:
                error_message = str(e).lower()
                
                # Check if this is a "not found" error by examining the error message
                # This is more reliable than checking response.status_code
                is_not_found = (
                    "404" in error_message or 
                    "not found" in error_message or 
                    f"no feed with the key '{feed_key}'" in error_message
                )
                
                if is_not_found:
                    logger.info(f"HTTP: Feed '{feed_key}' not found. Attempting to create (Attempt {attempt + 1}/{num_retries})...")
                    try:
                        # Create the feed
                        feed_to_create = Feed(key=feed_key, name=actual_feed_name, description=actual_description)
                        
                        # Include group_key if we have one
                        if group_key and target_group:
                            created_feed = self.http_client.create_feed(feed_to_create, group_key=group_key)
                            logger.info(f"HTTP: Successfully created feed '{created_feed.key}' (Name: {created_feed.name}) in group '{group_key}'.")
                        else:
                            created_feed = self.http_client.create_feed(feed_to_create)
                            logger.info(f"HTTP: Successfully created feed '{created_feed.key}' (Name: {created_feed.name}).")
                        
                        return created_feed
                        
                    except RequestError as create_e:
                        # Log the creation error with full details
                        self._handle_request_error(create_e, f"create feed '{feed_key}'", attempt, num_retries)
                        
                        # Check if this is a fatal error (auth issues)
                        create_error_msg = str(create_e).lower()
                        if "401" in create_error_msg or "unauthorized" in create_error_msg:
                            logger.critical("Authentication failed. Check your Adafruit IO username and key.")
                            return None
                            
                    except Exception as general_create_e:
                        logger.error(f"HTTP: Unexpected error creating feed '{feed_key}' (Attempt {attempt + 1}/{num_retries}): {general_create_e}", exc_info=True)
                else:
                    # Not a 404 error - handle other RequestErrors
                    self._handle_request_error(e, f"check feed '{feed_key}'", attempt, num_retries)
                    
                    # Check for authentication errors
                    if "401" in error_message or "unauthorized" in error_message:
                        return None
                        
            except Exception as ex:
                logger.error(f"HTTP: General error with feed '{feed_key}' (Attempt {attempt + 1}/{num_retries}): {ex}", exc_info=True)

            # Retry logic
            if attempt < num_retries - 1:
                logger.info(f"Retrying operation for feed '{feed_key}' in {self.retry_delay}s...")
                time.sleep(self.retry_delay)
            else:
                logger.error(f"Failed to ensure feed '{feed_key}' exists or is creatable after {num_retries} attempts.")
                return None
                
        return None

    # Methods like register_feed_handler, publish, initialize_feeds, etc.
    # will now correctly pass group_key to create_feed_if_not_exists.
    # (Code for these methods is mostly the same as in the previous good version,
    # just ensure group_key is threaded through if applicable)

    def register_feed_handler(self, feed_key: str, handler: Callable[[str, str], None],
                              feed_name: Optional[str] = None, description: Optional[str] = None,
                              group_key: Optional[str] = None) -> bool:
        # Ensure feed (and its group if specified) exists
        feed_obj = self.create_feed_if_not_exists(feed_key, feed_name=feed_name, description=description, group_key=group_key)
        if not feed_obj:
            logger.error(f"Failed to ensure feed '{feed_key}' (in group '{group_key if group_key else 'N/A'}') exists. Cannot register handler.")
            return False

        self.message_handlers[feed_key] = handler
        logger.info(f"Registered handler for feed '{feed_key}'.")

        if self.mqtt_connected:
            if feed_key not in self.subscribed_mqtt_feeds:
                # MQTT subscriptions are typically to global feed keys or specific group feed topics
                # Adafruit IO's standard MQTT feed topic is {username}/feeds/{feed_key}
                # If you use groups, ensure your feed_key is unique or your MQTT topic structure accounts for groups
                # e.g., {username}/groups/{group_key}/feeds/{feed_key}
                # For simplicity, sticking to standard feed topic for now.
                topic = f"{self.username}/feeds/{feed_key}"
                sub_result, _ = self.mqtt_client.subscribe(topic)
                if sub_result == mqtt.MQTT_ERR_SUCCESS:
                    self.subscribed_mqtt_feeds.add(feed_key)
                    logger.info(f"MQTT: Subscribed to feed: {feed_key} (topic: {topic})")
                else:
                    logger.warning(f"MQTT: Failed to subscribe to feed {feed_key} (topic: {topic}), result code: {sub_result}")
        else:
            logger.info(f"MQTT not connected. Subscription for '{feed_key}' will occur upon (re)connection.")
        return True

    def publish(self, feed_key: str, value: Union[str, int, float, bool],
                feed_name: Optional[str] = None, description: Optional[str] = None,
                group_key: Optional[str] = None) -> bool:
        feed_obj = self.create_feed_if_not_exists(feed_key, feed_name=feed_name, description=description, group_key=group_key)
        if not feed_obj:
            logger.error(f"Failed to ensure feed '{feed_key}' (in group '{group_key if group_key else 'N/A'}') exists. Cannot publish data.")
            return False

        payload_str = str(value)
        mqtt_topic = f"{self.username}/feeds/{feed_key}" # Default MQTT topic
        # If publishing to a feed specifically known to be in a group via MQTT,
        # and your topic scheme is different, adjust mqtt_topic here.
        # e.g., if group_key and feed_obj.group_id: mqtt_topic = f"{self.username}/groups/{group_key}/feeds/{feed_key}"

        if self.mqtt_connected:
            try:
                pub_result, _ = self.mqtt_client.publish(mqtt_topic, payload_str, qos=1)
                if pub_result == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"MQTT: Sent '{payload_str}' to '{feed_key}' (topic: {mqtt_topic}).")
                    return True
                else:
                    logger.warning(f"MQTT: Failed to publish to '{feed_key}' (topic: {mqtt_topic}), error code: {pub_result}. Falling back to HTTP.")
            except Exception as e:
                logger.warning(f"MQTT: Error publishing to '{feed_key}' (topic: {mqtt_topic}): {e}. Falling back to HTTP.", exc_info=True)
        else:
            logger.info(f"MQTT not connected. Publishing to '{feed_key}' via HTTP API.")

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"HTTP: Sending data to '{feed_key}': {value} (Attempt {attempt + 1})")
                # HTTP send_data uses feed_key. If feed is in a group, this still works.
                # To send data to a feed explicitly via its group:
                # self.http_client.send_data_to_feed_in_group(group_key, feed_key, value)
                # But send_data(feed_key, value) is usually sufficient.
                self.http_client.send_data(feed_key, value)
                logger.info(f"HTTP: Successfully sent data to '{feed_key}': {value}")
                return True
            except RequestError as e:
                self._handle_request_error(e, f"send data to '{feed_key}'", attempt, self.max_retries)
                if hasattr(e, 'response') and e.response and e.response.status_code in [401, 404]:
                    return False # Fatal for this operation
                if attempt < self.max_retries - 1: time.sleep(self.retry_delay)
                else: return False
            except Exception as e_gen:
                logger.error(f"HTTP: Unexpected error sending data to '{feed_key}' (Attempt {attempt + 1}): {e_gen}", exc_info=True)
                if attempt < self.max_retries - 1: time.sleep(self.retry_delay)
                else: return False
        return False


    def initialize_feeds(self, feed_configs: Union[List[str], List[Dict[str, Optional[str]]], Dict[str, Dict[str, Optional[str]]]]):
        success_count = 0
        error_count = 0
        
        processed_configs: List[Dict[str, Any]] = []
        # ... (parsing logic for feed_configs as in previous version, ensuring 'group_key' is extracted) ...
        if isinstance(feed_configs, list):
            for item in feed_configs:
                if isinstance(item, str): # Simple feed key
                    processed_configs.append({"key": item, "name": item, "description": f"Feed for {item}", "group_key": None})
                elif isinstance(item, dict): # Dictionary with feed details
                    if "key" not in item:
                        logger.error(f"Feed configuration missing 'key': {item}")
                        error_count += 1
                        continue
                    processed_configs.append({
                        "key": item["key"],
                        "name": item.get("name", item["key"]),
                        "description": item.get("description", f"Feed for {item['key']}"),
                        "group_key": item.get("group_key") # This is the important part
                    })
                else:
                    logger.error(f"Invalid item type in feed_configs list: {type(item)}")
                    error_count += 1
        elif isinstance(feed_configs, dict): # Dict where keys are feed_keys
            for key, config_val in feed_configs.items():
                processed_configs.append({
                    "key": key,
                    "name": config_val.get("name", key),
                    "description": config_val.get("description", f"Feed for {key}"),
                    "group_key": config_val.get("group_key") # And here
                })
        else:
            logger.error("Invalid feed_configs format. Must be list or dict.")
            return False
            
        total_feeds_to_process = len(processed_configs)
        if total_feeds_to_process == 0 and error_count == 0 :
            logger.info("No feeds specified for initialization.")
            return True

        for config in processed_configs:
            feed = self.create_feed_if_not_exists(
                config["key"],
                feed_name=config["name"],
                description=config["description"],
                group_key=config.get("group_key") # Pass it on
            )
            if feed:
                group_info = f" in group '{config['group_key']}'" if config.get('group_key') else ""
                logger.info(f"Feed '{config['key']}' (Name: {feed.name}){group_info} initialized successfully.")
                success_count += 1
            else:
                logger.error(f"Failed to initialize feed '{config['key']}'. Check logs.")
                error_count += 1
                
        if error_count > 0:
            logger.warning(f"Initialized {success_count}/{total_feeds_to_process + error_count} feeds with {error_count} errors.")
        else:
            logger.info(f"All {success_count}/{total_feeds_to_process} required feeds initialized successfully.")
        return error_count == 0

    # get_data, get_last_data, turn_actuator_on/off, get_actuator_state can remain similar
    # If you need to interact with feeds *strictly* within a group context (e.g. if feed keys are not globally unique)
    # you would use specific group-related methods from self.http_client, like:
    # - self.http_client.receive_feed_in_group_data(group_key, feed_key)
    # - self.http_client.send_data_to_feed_in_group(group_key, feed_key, value)
    # For now, assuming feed_keys are unique enough for global operations after creation.
    def get_data(self, feed_key: str, limit: int = 1, auto_create: bool = True, 
             group_key_for_create: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu từ feed với xử lý lỗi 'link' header.
        
        Phương pháp xử lý:
        1. Thử lấy dữ liệu bình thường
        2. Nếu gặp lỗi 'link', thử các cách khác
        3. Nếu vẫn không được, trả về danh sách rỗng
        """
        # Đảm bảo feed tồn tại nếu auto_create = True
        if auto_create:
            feed = self.create_feed_if_not_exists(feed_key, group_key=group_key_for_create)
            if not feed:
                logger.warning(f"Cannot get data for '{feed_key}', feed could not be ensured.")
                return []
        
        for attempt in range(self.max_retries):
            try:
                # Phương pháp 1: Thử gọi API bình thường
                try:
                    data_list_aio = self.http_client.data(feed_key, max_results=limit)
                except KeyError as ke:
                    # Nếu gặp lỗi 'link' header, thử cách khác
                    if "'link'" in str(ke) or "link" in str(ke):
                        logger.debug(f"Encountered 'link' header error for feed '{feed_key}'. Trying alternative method...")
                        
                        # Phương pháp 2: Thử lấy tất cả dữ liệu rồi cắt
                        try:
                            # Lấy feed object để có thể truy cập dữ liệu
                            feed_obj = self.http_client.feeds(feed_key)
                            
                            # Thử lấy dữ liệu gần nhất qua API khác
                            # Adafruit IO có API endpoint: /feeds/{feed_key}/data/last
                            if limit == 1:
                                # Nếu chỉ cần 1 giá trị, dùng API lấy giá trị cuối
                                last_data = self.http_client.receive(feed_key)
                                if last_data:
                                    data_list_aio = [last_data]
                                else:
                                    data_list_aio = []
                            else:
                                # Nếu cần nhiều giá trị, thử không dùng max_results
                                # hoặc dùng giá trị nhỏ hơn
                                try:
                                    data_list_aio = self.http_client.data(feed_key)
                                    # Giới hạn số lượng kết quả
                                    if len(data_list_aio) > limit:
                                        data_list_aio = data_list_aio[:limit]
                                except:
                                    # Nếu vẫn lỗi, có thể feed thực sự rỗng
                                    logger.info(f"Feed '{feed_key}' appears to be empty or has issues.")
                                    return []
                                    
                        except Exception as alt_error:
                            logger.debug(f"Alternative method also failed: {alt_error}")
                            # Feed có thể thực sự rỗng
                            return []
                    else:
                        # Không phải lỗi 'link', ném lại exception
                        raise
                
                # Xử lý dữ liệu đã lấy được
                result = []
                for d_aio in data_list_aio:
                    item = {
                        'id': d_aio.id,
                        'value': d_aio.value,
                        'created_at': d_aio.created_at,
                        'lat': getattr(d_aio, 'lat', None),  # Dùng getattr để tránh lỗi nếu không có
                        'lon': getattr(d_aio, 'lon', None),
                        'ele': getattr(d_aio, 'ele', None),
                        'feed_id': getattr(d_aio, 'feed_id', None),
                        'group_id': getattr(d_aio, 'group_id', None)
                    }
                    
                    # Thử chuyển đổi sang số nếu có thể
                    try:
                        if isinstance(d_aio.value, str):
                            # Kiểm tra xem có phải số thập phân không
                            if '.' in d_aio.value or 'e' in d_aio.value.lower():
                                item['value_numeric'] = float(d_aio.value)
                            else:
                                item['value_numeric'] = int(d_aio.value)
                        elif isinstance(d_aio.value, (int, float)):
                            item['value_numeric'] = d_aio.value
                    except (ValueError, TypeError):
                        # Không thể chuyển đổi, bỏ qua
                        pass
                        
                    result.append(item)
                    
                return result
                
            except RequestError as e:
                self._handle_request_error(e, f"get data from '{feed_key}'", attempt, self.max_retries)
                if hasattr(e, 'response') and e.response and e.response.status_code in [401, 404]:
                    return []  # Lỗi nghiêm trọng, không thử lại
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return []
                    
            except Exception as e_gen:
                logger.error(f"HTTP: Unexpected error getting data from '{feed_key}' (Attempt {attempt + 1}): {e_gen}", exc_info=True)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return []
                    
        return []

    def get_last_data(self, feed_key: str, auto_create: bool = True, 
                  group_key_for_create: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Lấy dữ liệu mới nhất từ feed với xử lý lỗi tối ưu.
        
        Phương pháp này được tối ưu cho việc lấy 1 giá trị duy nhất,
        tránh được lỗi 'link' header thường gặp.
        """
        if auto_create:
            feed = self.create_feed_if_not_exists(feed_key, group_key=group_key_for_create)
            if not feed:
                logger.warning(f"Cannot get last data for '{feed_key}', feed could not be ensured.")
                return None
        
        for attempt in range(self.max_retries):
            try:
                # Dùng API receive() thay vì data() cho hiệu quả hơn
                # API này được thiết kế để lấy giá trị mới nhất và không có vấn đề với 'link' header
                last_data_aio = self.http_client.receive(feed_key)
                
                if last_data_aio:
                    # Chuyển đổi thành format của chúng ta
                    item = {
                        'id': last_data_aio.id,
                        'value': last_data_aio.value,
                        'created_at': last_data_aio.created_at,
                        'lat': getattr(last_data_aio, 'lat', None),
                        'lon': getattr(last_data_aio, 'lon', None),
                        'ele': getattr(last_data_aio, 'ele', None),
                        'feed_id': getattr(last_data_aio, 'feed_id', None),
                        'group_id': getattr(last_data_aio, 'group_id', None)
                    }
                    
                    # Thử chuyển đổi sang số
                    try:
                        if isinstance(last_data_aio.value, str):
                            if '.' in last_data_aio.value or 'e' in last_data_aio.value.lower():
                                item['value_numeric'] = float(last_data_aio.value)
                            else:
                                item['value_numeric'] = int(last_data_aio.value)
                        elif isinstance(last_data_aio.value, (int, float)):
                            item['value_numeric'] = last_data_aio.value
                    except (ValueError, TypeError):
                        pass
                        
                    return item
                else:
                    # Feed rỗng
                    logger.debug(f"No data found in feed '{feed_key}'")
                    return None
                    
            except RequestError as e:
                self._handle_request_error(e, f"get last data from '{feed_key}'", attempt, self.max_retries)
                if hasattr(e, 'response') and e.response and e.response.status_code in [401, 404]:
                    return None
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            except Exception as e_gen:
                # Nếu receive() không hoạt động, thử dùng get_data với limit=1
                if "receive" in str(e_gen).lower() or attempt == self.max_retries - 1:
                    logger.debug(f"Falling back to get_data method for feed '{feed_key}'")
                    data_list = self.get_data(feed_key, limit=1, auto_create=False)
                    return data_list[0] if data_list else None
                else:
                    logger.error(f"Unexpected error getting last data from '{feed_key}': {e_gen}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        
        return None

    def _control_actuator(self, feed_key: str, value_to_send: str, action_name: str,
                          auto_create: bool = True, group_key_for_create: Optional[str] = None) -> bool:
        # publish will handle creation, including group context if group_key_for_create is passed
        result = self.publish(feed_key, value_to_send,
                              feed_name=f"{feed_key} Control",
                              group_key=group_key_for_create if auto_create else None)
        if result: logger.info(f"Successfully sent '{value_to_send}' to {action_name} actuator: {feed_key}")
        else: logger.error(f"Failed to send '{value_to_send}' to {action_name} actuator: {feed_key}")
        return result

    def turn_actuator_on(self, feed_key: str, auto_create: bool = True, group_key_for_create: Optional[str] = None) -> bool:
        return self._control_actuator(feed_key, "1", "ON", auto_create, group_key_for_create)

    def turn_actuator_off(self, feed_key: str, auto_create: bool = True, group_key_for_create: Optional[str] = None) -> bool:
        return self._control_actuator(feed_key, "0", "OFF", auto_create, group_key_for_create)

    def get_actuator_state(self, feed_key: str, auto_create: bool = True, group_key_for_create: Optional[str] = None) -> Optional[bool]:
        last_data = self.get_last_data(feed_key, auto_create=auto_create, group_key_for_create=group_key_for_create)
        if last_data and 'value' in last_data:
            value_str = str(last_data['value']).strip().upper()
            if value_str in ('1', 'ON', 'TRUE', 'YES'): return True
            if value_str in ('0', 'OFF', 'FALSE', 'NO'): return False
        return None

