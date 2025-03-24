# utils/logging_config.py
import logging
import sys
from config import Config

def setup_logging():
    """Thiết lập cấu hình logging cho ứng dụng"""
    
    # Chuyển đổi level từ chuỗi sang hằng số logging
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level = level_map.get(Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Cấu hình logging cơ bản
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            
        ]
    )
    
    logging.getLogger("paho.mqtt").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Tạo và trả về logger chính cho ứng dụng
    logger = logging.getLogger("data_processor")
    logger.setLevel(log_level)
    
    return logger