# app.py
import signal
import sys
import time
from config import Config
from utils import setup_logging
from services import DataProcessor


logger = setup_logging()

data_processor = None

def signal_handler(sig, frame):
    logger.info("Nhận tín hiệu tắt, đang dừng ứng dụng...")
    if data_processor:
        data_processor.stop()
    sys.exit(0)

def main():
    global data_processor
    
    try:
        logger.info("Kiểm tra cấu hình...")
        Config.validate()
        
        logger.info("Khởi tạo Data Processing Service...")
        data_processor = DataProcessor()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Bắt đầu Data Processing Service...")
        data_processor.start()
        
        logger.info("Data Processing Service đang chạy...")
        while True:
            time.sleep(1)
            
    except ValueError as e:
        logger.error(f"Lỗi cấu hình: {e}")
        return 1
        
    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {e}")
        if data_processor:
            data_processor.stop()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())