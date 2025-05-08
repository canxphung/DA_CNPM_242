"""
Thiết lập hệ thống logging.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    """Thiết lập cấu hình logging cho ứng dụng."""
    # Tạo thư mục logs nếu chưa tồn tại
    os.makedirs("logs", exist_ok=True)
    
    # Cấu hình logger chính
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Định dạng log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler log vào file, với rotation
    file_handler = RotatingFileHandler(
        "logs/core_operations.log",
        maxBytes=10485760,  # 10MB
        backupCount=5       # Giữ 5 file backup
    )
    file_handler.setFormatter(formatter)
    
    # Handler log ra console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Thêm handlers vào logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("Logging system initialized")