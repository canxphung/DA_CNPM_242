# services/ai_service.py
import logging
import requests
from requests.exceptions import RequestException, Timeout
from config import Config

logger = logging.getLogger("data_processor.ai")

class AIService:
    """Service để tương tác với AI Processing Service"""
    
    def __init__(self):
        """Khởi tạo AI Service"""
        self.api_url = Config.AI_SERVICE_URL
        self.timeout = Config.AI_REQUEST_TIMEOUT
        logger.info(f"AI Service được khởi tạo với endpoint: {self.api_url}")
    
    def should_process(self, feed_key, data):
        """Kiểm tra xem dữ liệu có nên được gửi đến AI Service không
        
        Args:
            feed_key (str): Tên của feed
            data (dict): Dữ liệu đã xử lý
            
        Returns:
            bool: True nếu dữ liệu nên được gửi đến AI Service
        """
        # Thêm logic tùy chỉnh tại đây để quyết định
        # dữ liệu nào nên được gửi đến AI Service
        
        # Ví dụ: chỉ gửi dữ liệu từ cảm biến nhiệt độ và độ ẩm
        if feed_key in ["temperature", "humidity"]:
            return True
            
        # Ví dụ: gửi dữ liệu khi có giá trị bất thường
        if "value" in data:
            try:
                value = float(data["value"])
                # Ví dụ: nhiệt độ cao bất thường
                if feed_key == "temperature" and value > 30:
                    return True
                # Ví dụ: độ ẩm cao bất thường
                if feed_key == "humidity" and value > 80:
                    return True
            except (ValueError, TypeError):
                pass
        
        return False
    
    def send_for_analysis(self, data):
        
        try:
            logger.info(f"Gửi dữ liệu đến AI Service: {data}")
            
            response = requests.post(
                self.api_url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            # Kiểm tra status code
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Nhận kết quả từ AI Service: {result}")
            return result
            
        except Timeout:
            logger.error(f"Timeout khi gửi dữ liệu đến AI Service ({self.timeout}s)")
            return None
            
        except RequestException as e:
            logger.error(f"Lỗi khi gửi dữ liệu đến AI Service: {e}")
            return None
            
        except ValueError as e:
            logger.error(f"Lỗi khi parse kết quả từ AI Service: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi không xác định khi tương tác với AI Service: {e}")
            return None