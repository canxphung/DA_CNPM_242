"""
Lớp wrapper cho kết nối và thao tác với Redis.
"""
import json
import logging
import redis
from typing import Any, Dict, List, Optional, Union
from datetime import timedelta

logger = logging.getLogger(__name__)

class RedisClient:
    """
    Lớp wrapper cung cấp các tiện ích để làm việc với Redis.
    """
    
    def __init__(self, host: str, port: int, db: int = 0, password: Optional[str] = None):
        """
        Khởi tạo kết nối Redis.
        
        Args:
            host: Máy chủ Redis
            port: Cổng Redis
            db: Số database Redis
            password: Mật khẩu Redis (nếu có)
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'db': db,
            'decode_responses': True  # Tự động chuyển đổi bytes thành string
        }
        
        if password:
            self.connection_params['password'] = password
            
        self.redis = self._create_connection()
        
    def _create_connection(self) -> redis.Redis:
        """Tạo và trả về kết nối Redis."""
        try:
            client = redis.Redis(**self.connection_params)
            # Kiểm tra kết nối
            client.ping()
            logger.info(f"Redis connection established: {self.connection_params['host']}:{self.connection_params['port']}")
            return client
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
            
    def reconnect(self) -> None:
        """Kết nối lại với Redis."""
        self.redis = self._create_connection()
            
    def set(self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None) -> bool:
        """
        Lưu giá trị vào Redis.
        
        Args:
            key: Khóa
            value: Giá trị (sẽ được tự động chuyển đổi thành JSON nếu là dict/list)
            expire: Thời gian hết hạn (giây hoặc timedelta)
            
        Returns:
            bool: Thành công hay thất bại
        """
        try:
            # Chuyển đổi giá trị phức tạp thành JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
                
            # Xử lý thời gian hết hạn
            if isinstance(expire, timedelta):
                expire = int(expire.total_seconds())
                
            return self.redis.set(key, value, ex=expire)
        except redis.RedisError as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        Lấy giá trị từ Redis.
        
        Args:
            key: Khóa
            default: Giá trị mặc định nếu khóa không tồn tại
            
        Returns:
            Giá trị tương ứng với khóa
        """
        try:
            value = self.redis.get(key)
            if value is None:
                return default
                
            # Thử chuyển đổi từ JSON
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value
        except redis.RedisError as e:
            logger.error(f"Redis get error: {str(e)}")
            return default
            
    def hset(self, name: str, key: str, value: Any) -> bool:
        """
        Lưu giá trị vào hash.
        
        Args:
            name: Tên hash
            key: Khóa
            value: Giá trị (sẽ được tự động chuyển đổi thành JSON nếu là dict/list)
            
        Returns:
            bool: Thành công hay thất bại
        """
        try:
            # Chuyển đổi giá trị phức tạp thành JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
                
            self.redis.hset(name, key, value)
            return True
        except redis.RedisError as e:
            logger.error(f"Redis hset error: {str(e)}")
            return False
            
    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """
        Lấy giá trị từ hash.
        
        Args:
            name: Tên hash
            key: Khóa
            default: Giá trị mặc định nếu khóa không tồn tại
            
        Returns:
            Giá trị tương ứng với khóa
        """
        try:
            value = self.redis.hget(name, key)
            if value is None:
                return default
                
            # Thử chuyển đổi từ JSON
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value
        except redis.RedisError as e:
            logger.error(f"Redis hget error: {str(e)}")
            return default
            
    def hgetall(self, name: str) -> Dict[str, Any]:
        """
        Lấy tất cả các cặp khóa-giá trị từ hash.
        
        Args:
            name: Tên hash
            
        Returns:
            Dict chứa tất cả cặp khóa-giá trị
        """
        try:
            result = self.redis.hgetall(name)
            if not result:
                return {}
                
            # Chuyển đổi giá trị từ JSON
            converted = {}
            for key, value in result.items():
                try:
                    converted[key] = json.loads(value)
                except (TypeError, json.JSONDecodeError):
                    converted[key] = value
            return converted
        except redis.RedisError as e:
            logger.error(f"Redis hgetall error: {str(e)}")
            return {}
            
    def delete(self, *keys: str) -> int:
        """
        Xóa một hoặc nhiều khóa.
        
        Args:
            keys: Danh sách khóa cần xóa
            
        Returns:
            int: Số khóa đã được xóa
        """
        try:
            return self.redis.delete(*keys)
        except redis.RedisError as e:
            logger.error(f"Redis delete error: {str(e)}")
            return 0
            
    def keys(self, pattern: str) -> List[str]:
        """
        Tìm khóa theo mẫu.
        
        Args:
            pattern: Mẫu tìm kiếm (ví dụ: "sensor:*")
            
        Returns:
            Danh sách khóa phù hợp
        """
        try:
            return self.redis.keys(pattern)
        except redis.RedisError as e:
            logger.error(f"Redis keys error: {str(e)}")
            return []
            
    def exists(self, *keys: str) -> bool:
        """
        Kiểm tra xem một hoặc nhiều khóa có tồn tại hay không.
        
        Args:
            keys: Danh sách khóa cần kiểm tra
            
        Returns:
            bool: True nếu tất cả khóa đều tồn tại, ngược lại False
        """
        try:
            return bool(self.redis.exists(*keys))
        except redis.RedisError as e:
            logger.error(f"Redis exists error: {str(e)}")
            return False
            
    def expire(self, key: str, time: Union[int, timedelta]) -> bool:
        """
        Đặt thời gian hết hạn cho khóa.
        
        Args:
            key: Khóa cần đặt thời gian hết hạn
            time: Thời gian hết hạn (giây hoặc timedelta)
            
        Returns:
            bool: Thành công hay thất bại
        """
        try:
            if isinstance(time, timedelta):
                time = int(time.total_seconds())
                
            return self.redis.expire(key, time)
        except redis.RedisError as e:
            logger.error(f"Redis expire error: {str(e)}")
            return False
            
    def ttl(self, key: str) -> int:
        """
        Lấy thời gian còn lại trước khi khóa hết hạn.
        
        Args:
            key: Khóa cần kiểm tra
            
        Returns:
            int: Thời gian còn lại (giây), -1 nếu không có thời hạn, -2 nếu khóa không tồn tại
        """
        try:
            return self.redis.ttl(key)
        except redis.RedisError as e:
            logger.error(f"Redis ttl error: {str(e)}")
            return -2
            
    def close(self) -> None:
        """Đóng kết nối Redis."""
        if hasattr(self, 'redis') and self.redis:
            self.redis.close()