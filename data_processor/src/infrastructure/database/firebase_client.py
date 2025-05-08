"""
Lớp tiện ích để thao tác với Firebase Realtime Database.
"""
import logging
from typing import Any, Dict, List, Optional, Union
import firebase_admin
from firebase_admin import db
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class FirebaseClient:
    """
    Lớp cung cấp các tiện ích để thao tác với Firebase Realtime Database.
    """
    
    def __init__(self, base_path: str = ""):
        """
        Khởi tạo client với đường dẫn cơ sở.
        
        Args:
            base_path: Đường dẫn cơ sở trong database
        """
        self.base_path = base_path
        # Đảm bảo Firebase đã được khởi tạo
        if not firebase_admin._apps:
            raise RuntimeError("Firebase app is not initialized. Call firebase_admin.initialize_app() first.")
        
    def _get_reference(self, path: Optional[str] = None) -> db.Reference:
        """
        Lấy tham chiếu đến một đường dẫn trong database.
        
        Args:
            path: Đường dẫn tương đối (sẽ được thêm vào base_path)
            
        Returns:
            Tham chiếu đến database
        """
        if path:
            full_path = f"{self.base_path}/{path}" if self.base_path else path
        else:
            full_path = self.base_path
            
        return db.reference(full_path)
        
    def set(self, path: str, data: Any) -> None:
        """
        Ghi dữ liệu vào đường dẫn cụ thể, ghi đè dữ liệu hiện có.
        
        Args:
            path: Đường dẫn
            data: Dữ liệu cần ghi
        """
        try:
            ref = self._get_reference(path)
            ref.set(data)
            logger.debug(f"Data set at path: {path}")
        except Exception as e:
            logger.error(f"Firebase set error at {path}: {str(e)}")
            raise
            
    def update(self, path: str, data: Dict[str, Any]) -> None:
        """
        Cập nhật một phần dữ liệu tại đường dẫn.
        
        Args:
            path: Đường dẫn
            data: Dict chứa các cập nhật
        """
        try:
            ref = self._get_reference(path)
            ref.update(data)
            logger.debug(f"Data updated at path: {path}")
        except Exception as e:
            logger.error(f"Firebase update error at {path}: {str(e)}")
            raise
            
    def push(self, path: str, data: Any) -> str:
        """
        Thêm dữ liệu vào danh sách với khóa tự động tạo.
        
        Args:
            path: Đường dẫn
            data: Dữ liệu cần thêm
            
        Returns:
            str: Khóa của dữ liệu đã thêm
        """
        try:
            ref = self._get_reference(path)
            new_ref = ref.push()
            new_ref.set(data)
            logger.debug(f"Data pushed to path: {path}")
            return new_ref.key
        except Exception as e:
            logger.error(f"Firebase push error at {path}: {str(e)}")
            raise
            
    def get(self, path: str, default: Any = None) -> Any:
        """
        Lấy dữ liệu từ đường dẫn.
        
        Args:
            path: Đường dẫn
            default: Giá trị mặc định nếu không tìm thấy dữ liệu
            
        Returns:
            Dữ liệu tại đường dẫn
        """
        try:
            ref = self._get_reference(path)
            data = ref.get()
            return data if data is not None else default
        except Exception as e:
            logger.error(f"Firebase get error at {path}: {str(e)}")
            return default
            
    def delete(self, path: str) -> None:
        """
        Xóa dữ liệu tại đường dẫn.
        
        Args:
            path: Đường dẫn
        """
        try:
            ref = self._get_reference(path)
            ref.delete()
            logger.debug(f"Data deleted at path: {path}")
        except Exception as e:
            logger.error(f"Firebase delete error at {path}: {str(e)}")
            raise
            
    def store_sensor_data(self, sensor_type: str, data: Dict[str, Any]) -> str:
        """
        Lưu trữ dữ liệu cảm biến với timestamp.
        
        Args:
            sensor_type: Loại cảm biến (light, temperature, humidity, soil_moisture)
            data: Dữ liệu cảm biến
            
        Returns:
            str: Khóa của dữ liệu đã lưu
        """
        # Đảm bảo dữ liệu có timestamp
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
            
        path = f"sensor_data/{sensor_type}"
        return self.push(path, data)
            
    def get_latest_sensor_data(self, sensor_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu cảm biến mới nhất.
        
        Args:
            sensor_type: Loại cảm biến (light, temperature, humidity, soil_moisture)
            limit: Số lượng bản ghi tối đa
            
        Returns:
            List chứa dữ liệu cảm biến
        """
        path = f"sensor_data/{sensor_type}"
        try:
            ref = self._get_reference(path)
            # Truy vấn sắp xếp theo khóa và lấy các giá trị mới nhất
            query = ref.order_by_key().limit_to_last(limit)
            data = query.get()
            
            if data is None:
                return []
                
            # Chuyển đổi từ dict thành list với key bên trong
            result = []
            for key, value in data.items():
                if isinstance(value, dict):
                    value['id'] = key
                    result.append(value)
                else:
                    result.append({'id': key, 'value': value})
                    
            # Sắp xếp theo timestamp giảm dần (nếu có)
            result.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return result
        except Exception as e:
            logger.error(f"Firebase get_latest_sensor_data error for {sensor_type}: {str(e)}")
            return []
            
    def store_irrigation_event(self, event_data: Dict[str, Any]) -> str:
        """
        Lưu trữ sự kiện tưới nước.
        
        Args:
            event_data: Dữ liệu sự kiện
            
        Returns:
            str: Khóa của sự kiện đã lưu
        """
        # Đảm bảo dữ liệu có timestamp
        if 'timestamp' not in event_data:
            event_data['timestamp'] = datetime.now().isoformat()
            
        path = "irrigation_events"
        return self.push(path, event_data)
            
    def get_irrigation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử tưới nước.
        
        Args:
            limit: Số lượng bản ghi tối đa
            
        Returns:
            List chứa lịch sử tưới nước
        """
        path = "irrigation_events"
        try:
            ref = self._get_reference(path)
            # Truy vấn sắp xếp theo khóa và lấy các giá trị mới nhất
            query = ref.order_by_key().limit_to_last(limit)
            data = query.get()
            
            if data is None:
                return []
                
            # Chuyển đổi từ dict thành list với key bên trong
            result = []
            for key, value in data.items():
                if isinstance(value, dict):
                    value['id'] = key
                    result.append(value)
                else:
                    result.append({'id': key, 'value': value})
                    
            # Sắp xếp theo timestamp giảm dần (nếu có)
            result.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return result
        except Exception as e:
            logger.error(f"Firebase get_irrigation_history error: {str(e)}")
            return []