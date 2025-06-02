"""
Cấu hình và quản lý hệ thống logging.
"""
import os
import sys
import io
import logging
import logging.handlers
from datetime import datetime

# Định dạng log mặc định
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Kích thước tối đa của file log (10MB)
MAX_LOG_SIZE = 10 * 1024 * 1024
BACKUP_COUNT = 5


class UTF8ConsoleHandler(logging.StreamHandler):
    """
    Custom console handler đảm bảo luôn dùng UTF-8 để log tiếng Việt không lỗi.
    """
    def __init__(self):
        try:
            stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except Exception:
            stream = sys.stdout  # fallback nếu không hỗ trợ
        super().__init__(stream)


def setup_logger(name=None, level=logging.INFO, log_file=None, format_str=None):
    """
    Thiết lập cấu hình cho một logger cụ thể.

    Args:
        name: Tên logger (None cho root logger)
        level: Mức log (INFO, DEBUG, WARNING, ERROR, CRITICAL)
        log_file: Đường dẫn tới file log (None để chỉ log ra console)
        format_str: Định dạng log

    Returns:
        Logger đã được cấu hình
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Xoá tất cả các handler cũ
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    formatter = logging.Formatter(format_str or DEFAULT_FORMAT)

    # Console logger (ép dùng UTF-8)
    console_handler = UTF8ConsoleHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File logger nếu có
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'  # đảm bảo không lỗi Unicode khi ghi tiếng Việt
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
    os.makedirs(log_dir, exist_ok=True)

    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'ai_service_{current_date}.log')

    root_logger = setup_logger(
        name=None,
        level=logging.INFO,
        log_file=log_file,
        format_str='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    # Giảm độ ồn của các thư viện bên ngoài
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    # Ghi log khởi động
    root_logger.info("=" * 60)
    root_logger.info("🎯 AI Service logging initialized")
    root_logger.info(f"📁 Log file: {log_file}")
    root_logger.info("=" * 60)

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


# Tự động thiết lập logger gốc khi import
default_logger = setup_global_logging()
