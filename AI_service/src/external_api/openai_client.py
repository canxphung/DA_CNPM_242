# src/external_api/openai_client.py
import os
import json
import time
import backoff
import openai
import re
from datetime import datetime
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.config import OPENAI_API_KEY
from src.core.cache_manager import APICacheManager

# Configure OpenAI API
openai.api_key = OPENAI_API_KEY

class OpenAIClient:
    """
    Client for interacting with the OpenAI API.
    Provides methods for different types of requests with caching and error handling.
    """
    
    def __init__(self, use_cache=True):
        """
        Initialize the OpenAI client.
        
        Args:
            use_cache: Whether to use caching for API responses
        """
        self.use_cache = use_cache
        self.cache = APICacheManager() if use_cache else None
        self.model = "gpt-3.5-turbo"  # Default model
    
    @backoff.on_exception(
        backoff.expo,
        (openai.error.RateLimitError, openai.error.APIError, openai.error.ServiceUnavailableError),
        max_tries=3
    )
    def chat_completion(self, messages, temperature=0.7, max_tokens=None, use_cache=None):
        """
        Make a chat completion request to OpenAI API with caching and error handling.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in the response
            use_cache: Override instance cache setting
            
        Returns:
            API response or cached response
        """
        # Determine whether to use cache
        should_use_cache = self.use_cache if use_cache is None else use_cache
        
        # Generate a cache key if using cache
        if should_use_cache:
            cache_key = self._generate_cache_key(messages, temperature, max_tokens)
            cached_response = self.cache.get(cache_key)
            
            if cached_response:
                return cached_response
        
        try:
            # Make the API request
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Cache the response if using cache
            if should_use_cache:
                self.cache.set(cache_key, response)
            
            return response
            
        except (openai.error.RateLimitError, openai.error.APIError, 
                openai.error.ServiceUnavailableError) as e:
            # These will be retried by the backoff decorator
            raise e
        except Exception as e:
            # Log other errors but don't retry
            print(f"Error in OpenAI request: {str(e)}")
            raise
    
    def analyze_user_input(self, text, intent_filter=None):
        """
        Analyze user input to classify intent and extract info.
        
        Args:
            text: User input text
            intent_filter: Optional list of allowed intents
            
        Returns:
            Dictionary with intent and entities
        """
        system_prompt = (
            "Bạn là hệ thống phân loại ý định cho nhà kính thông minh. "
            "Phân loại văn bản đầu vào thành một trong các ý định: "
            "query_soil_moisture, query_temperature, query_humidity, query_light, "
            "turn_on_pump, turn_off_pump, get_status, schedule_irrigation. "
            "Ngoài ra, hãy trích xuất tất cả thông tin quan trọng từ văn bản như "
            "thời gian, thời lượng, v.v. "
            "Trả về kết quả dưới dạng JSON với các trường 'intent' và 'entities'."
        )
        
        if intent_filter:
            intent_list = ", ".join(intent_filter)
            system_prompt = system_prompt.replace(
                "query_soil_moisture, query_temperature, query_humidity, query_light, "
                "turn_on_pump, turn_off_pump, get_status, schedule_irrigation",
                intent_list
            )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        response = self.chat_completion(messages, temperature=0.3)
        
        try:
            content = response.choices[0].message.content.strip()
            # Try to parse JSON response
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            # If response is not valid JSON, try to extract information manually
            intent = None
            if "intent" in content.lower():
                intent_match = re.search(r'intent["\']?\s*:\s*["\']?([^"\'}\s,]+)', content)
                if intent_match:
                    intent = intent_match.group(1)
            
            return {
                "intent": intent or "unknown",
                "entities": {},
                "raw_response": content
            }
    
    def recommend_irrigation(self, sensor_data):
        """
        Get irrigation recommendation based on sensor data.
        
        Args:
            sensor_data: Dictionary with current sensor readings
            
        Returns:
            Dictionary with recommendation
        """
        system_prompt = (
            "Bạn là chuyên gia tưới tiêu. Dựa trên dữ liệu cảm biến, hãy đưa ra khuyến "
            "nghị có nên tưới không và trong bao lâu. Nếu độ ẩm đất thấp hơn 30%, "
            "nhiệt độ cao, và độ ẩm không khí thấp, rất có thể cần tưới. "
            "Trả về JSON với should_irrigate (true/false), duration_minutes (số phút) và reason (lý do)."
        )
        
        # Format sensor data for the prompt
        user_prompt = (
            f"Dữ liệu hiện tại: "
            f"Độ ẩm đất: {sensor_data.get('soil_moisture', 'N/A')}%, "
            f"Nhiệt độ: {sensor_data.get('temperature', 'N/A')}°C, "
            f"Độ ẩm không khí: {sensor_data.get('humidity', 'N/A')}%, "
            f"Ánh sáng: {sensor_data.get('light_level', 'N/A')} lux"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.chat_completion(messages, temperature=0.3)
        
        try:
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            # If response is not valid JSON, return a default recommendation
            return {
                "should_irrigate": sensor_data.get('soil_moisture', 50) < 30,
                "duration_minutes": 10,
                "reason": "Recommended based on soil moisture level",
                "error": "Failed to parse API response"
            }
    
    def generate_response(self, intent, entities, sensor_data=None, context=None):
        """
        Generate a natural language response based on intent and entities.
        
        Args:
            intent: User intent
            entities: Extracted entities
            sensor_data: Optional current sensor readings
            context: Optional conversation context
            
        Returns:
            Generated response text
        """
        system_prompt = (
            "Bạn là trợ lý thông minh cho hệ thống nhà kính. Hãy tạo phản hồi tự nhiên "
            "bằng tiếng Việt dựa trên ý định của người dùng và dữ liệu cảm biến. "
            "Giữ câu trả lời ngắn gọn, thân thiện và hữu ích."
        )
        
        # Construct the user prompt with all available information
        user_prompt = f"Ý định: {intent}\n"
        
        if entities:
            user_prompt += f"Thông tin trích xuất: {json.dumps(entities, ensure_ascii=False)}\n"
        
        if sensor_data:
            user_prompt += (
                f"Dữ liệu cảm biến hiện tại:\n"
                f"- Độ ẩm đất: {sensor_data.get('soil_moisture', 'N/A')}%\n"
                f"- Nhiệt độ: {sensor_data.get('temperature', 'N/A')}°C\n"
                f"- Độ ẩm không khí: {sensor_data.get('humidity', 'N/A')}%\n"
                f"- Ánh sáng: {sensor_data.get('light_level', 'N/A')} lux\n"
            )
        
        if context:
            user_prompt += f"Ngữ cảnh: {context}\n"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.chat_completion(messages, temperature=0.7)
        return response.choices[0].message.content.strip()
    
    def _generate_cache_key(self, messages, temperature, max_tokens):
        """
        Generate a cache key for a request.
        
        Args:
            messages: Message list
            temperature: Temperature value
            max_tokens: Max tokens value
            
        Returns:
            Cache key string
        """
        # Convert messages to a string representation
        message_str = json.dumps(messages, sort_keys=True)
        
        # Create a combined key
        key = f"{message_str}_{temperature}_{max_tokens}"
        
        # Return a hash of the key for shorter storage
        return str(hash(key))