"""
Cấu hình và quản lý hệ thống logging.
"""
import os
import logging
import logging.handlers
from datetime import datetime

# Định dạng log mặc định
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Kích thước tối đa của file log
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB

# Số lượng file backup
BACKUP_COUNT = 5


def setup_logger(name=None, level=logging.INFO, log_file=None, format_str=None):
    """
    Thiết lập cấu hình cho một logger cụ thể.
    
    Args:
        name: Tên logger (None cho root logger)
        level: Mức log (INFO, DEBUG, WARNING, ERROR, CRITICAL)
        log_file: Đường dẫn đến file log (None để log chỉ ra console)
        format_str: Định dạng log
        
    Returns:
        Logger đã được cấu hình
    """
    # Sử dụng root logger nếu không có tên
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Xóa tất cả các handler hiện tại
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Định dạng mặc định
    formatter = logging.Formatter(format_str or DEFAULT_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler nếu có
    if log_file:
        # Đảm bảo thư mục logs tồn tại
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Sử dụng RotatingFileHandler để giới hạn kích thước file
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_global_logging(log_dir='logs'):
    """
    Thiết lập hệ thống logging toàn cục cho ứng dụng.
    
    Args:
        log_dir: Thư mục chứa các file log
        
    Returns:
        Root logger đã được cấu hình
    """
    # Đảm bảo thư mục log tồn tại
    os.makedirs(log_dir, exist_ok=True)
    
    # Tạo tên file log dựa trên ngày hiện tại
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'ai_service_{current_date}.log')
    
    # Cấu hình root logger
    root_logger = setup_logger(
        name=None,  # Root logger
        level=logging.INFO,
        log_file=log_file,
        format_str='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Giảm mức log của một số thư viện bên ngoài gây nhiễu
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    # Thêm thông tin khởi động
    root_logger.info("=" * 50)
    root_logger.info("AI Service logging initialized")
    root_logger.info(f"Log file: {log_file}")
    root_logger.info("=" * 50)
    
    return root_logger


def get_logger(name):
    """
    Lấy một logger theo tên.
    
    Args:
        name: Tên logger (thường là __name__ của module)
        
    Returns:
        Logger với tên cụ thể
    """
    return logging.getLogger(name)


# Thiết lập mặc định khi import module
default_logger = setup_global_logging()