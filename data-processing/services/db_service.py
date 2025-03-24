# services/db_service.py
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config

logger = logging.getLogger("data_processor.db")

class DatabaseService:
    
    def __init__(self):

        try:
            self.client = MongoClient(Config.MONGODB_URI)
            # Kiểm tra kết nối
            self.client.admin.command('ping')
            logger.info("Kết nối MongoDB thành công")
            
            self.db = self.client[Config.MONGODB_DB]
            self.collection = self.db[Config.MONGODB_COLLECTION]
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Không thể kết nối đến MongoDB: {e}")
            raise
    
    def save_data(self, data):
       
        try:
            result = self.collection.insert_one(data)
            logger.debug(f"Đã lưu dữ liệu vào MongoDB với ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu vào MongoDB: {e}")
            raise
    
    def get_data(self, query=None, limit=100):

        try:
            if query is None:
                query = {}
            cursor = self.collection.find(query).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu từ MongoDB: {e}")
            raise
    
    def close(self):
        try:
            self.client.close()
            logger.info("Đã đóng kết nối MongoDB")
        except Exception as e:
            logger.error(f"Lỗi khi đóng kết nối MongoDB: {e}")