"""
Tối ưu hóa tài nguyên (nước và năng lượng) cho hệ thống tưới.
"""
import logging
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ResourceOptimizer:
    """
    Tối ưu hóa tài nguyên (nước và năng lượng) cho hệ thống tưới dựa trên
    dữ liệu cảm biến, dự báo thời tiết, và đặc tính cây trồng.
    """
    
    def __init__(self, config, model_registry, weather_client=None):
        """
        Khởi tạo ResourceOptimizer.
        
        Args:
            config: Cấu hình hệ thống
            model_registry: Registry chứa các mô hình ML
            weather_client: Client API thời tiết (tùy chọn)
        """
        self.config = config
        self.model_registry = model_registry
        self.weather_client = weather_client
        
        # Tải cấu hình
        self.preferred_times = config.RESOURCE_OPTIMIZATION.get('preferred_times', ["06:00", "18:00"])
        self.avoid_times = config.RESOURCE_OPTIMIZATION.get('avoid_times', ["12:00", "13:00"])
        self.min_water_saving_percent = config.RESOURCE_OPTIMIZATION.get('min_water_saving_percent', 10)
        
        # Tải dữ liệu về các loại cây
        self.plant_profiles = self._load_plant_profiles()
        
        logger.info("ResourceOptimizer initialized")
    
    def optimize_schedule(self, sensor_data, plant_types, zones=None) -> Dict[str, Any]:
        """
        Tạo lịch tưới tối ưu dựa trên dữ liệu cảm biến và loại cây.
        
        Args:
            sensor_data: Dữ liệu cảm biến hiện tại
            plant_types: Các loại cây trồng trong vườn
            zones: Phân chia vùng tưới (tùy chọn)
            
        Returns:
            Dict chứa lịch tưới tối ưu
        """
        logger.info(f"Creating optimized irrigation schedule for plant types: {plant_types}")
        
        # Tính nhu cầu nước cho các loại cây
        water_needs = self._calculate_water_needs(sensor_data, plant_types)
        
        # Tính thời điểm tưới tối ưu
        optimal_times = self._determine_optimal_times(sensor_data)
        
        # Tối ưu theo vùng nếu có thông tin vùng
        if zones:
            return self._optimize_by_zones(water_needs, optimal_times, zones, sensor_data)
        
        # Tối ưu tổng thể nếu không có thông tin vùng
        return self._optimize_general(water_needs, optimal_times, sensor_data)
    
    def calculate_water_savings(self, current_schedule, optimized_schedule) -> Dict[str, Any]:
        """
        Tính toán mức tiết kiệm nước giữa lịch hiện tại và lịch đã tối ưu.
        
        Args:
            current_schedule: Lịch tưới hiện tại hoặc ước tính mặc định
            optimized_schedule: Lịch tưới đã tối ưu
            
        Returns:
            Dict chứa thông tin tiết kiệm
        """
        # Tính tổng thời gian tưới
        current_duration = 0
        for item in current_schedule.get('zones', [current_schedule]):
            if item.get('should_irrigate', False):
                current_duration += item.get('duration_minutes', 0)
        
        optimized_duration = 0
        for item in optimized_schedule.get('zones', [optimized_schedule]):
            if item.get('should_irrigate', False):
                optimized_duration += item.get('duration_minutes', 0)
        
        # Ước tính lượng nước (1 phút = 2 lít nước, có thể điều chỉnh)
        water_rate = 2  # lít/phút
        current_water = current_duration * water_rate
        optimized_water = optimized_duration * water_rate
        
        # Tính tiết kiệm
        saved_water = max(0, current_water - optimized_water)
        saved_percentage = (saved_water / current_water * 100) if current_water > 0 else 0
        
        return {
            "saved_water_liters": round(saved_water, 1),
            "saved_percentage": round(saved_percentage, 1),
            "current_water_usage": round(current_water, 1),
            "optimized_water_usage": round(optimized_water, 1)
        }
    
    def _calculate_water_needs(self, sensor_data, plant_types) -> Dict[str, float]:
        """
        Tính toán nhu cầu nước dựa trên loại cây và điều kiện môi trường.
        
        Args:
            sensor_data: Dữ liệu cảm biến hiện tại
            plant_types: Các loại cây trồng
            
        Returns:
            Dict chứa nhu cầu nước cho các loại cây
        """
        water_needs = {}
        
        # Lấy thông số môi trường
        soil_moisture = sensor_data.get('soil_moisture', 50)
        temperature = sensor_data.get('temperature', 25)
        humidity = sensor_data.get('humidity', 60)
        
        for plant_type in plant_types:
            # Lấy thông tin cây từ profiles
            profile = self.plant_profiles.get(plant_type, {
                'water_need_factor': 1.0,
                'optimal_soil_moisture': 60,
                'drought_tolerance': 0.5
            })
            
            # Tính thiếu hụt độ ẩm đất
            moisture_deficit = max(0, profile.get('optimal_soil_moisture', 60) - soil_moisture)
            
            # Tính hệ số bay hơi dựa trên nhiệt độ và độ ẩm
            evaporation_factor = (temperature / 30) * (1 - (humidity / 100))
            
            # Tính nhu cầu nước (phút tưới)
            base_duration = moisture_deficit * 0.25  # 0.25 phút cho mỗi % thiếu hụt
            water_need = base_duration * profile.get('water_need_factor', 1.0) * (1 + evaporation_factor)
            
            # Điều chỉnh theo khả năng chịu hạn
            water_need = water_need * (2 - profile.get('drought_tolerance', 0.5))
            
            # Lưu kết quả
            water_needs[plant_type] = max(0, min(30, round(water_need, 1)))  # Giới hạn tối đa 30 phút
        
        return water_needs
    
    def _determine_optimal_times(self, sensor_data) -> List[str]:
        """
        Xác định thời điểm tưới tối ưu dựa trên điều kiện môi trường.
        
        Args:
            sensor_data: Dữ liệu cảm biến hiện tại
            
        Returns:
            Danh sách các thời điểm tưới tối ưu (HH:MM)
        """
        # Thời điểm mặc định
        default_times = self.preferred_times.copy()
        
        # Nếu có dự báo thời tiết, điều chỉnh thời gian
        if self.weather_client:
            try:
                forecast = self.weather_client.get_forecast(days=1)
                # Logic điều chỉnh thời gian dựa trên dự báo
                # ...
            except Exception as e:
                logger.error(f"Error getting weather forecast: {str(e)}")
        
        # Nếu nhiệt độ cao, chọn thời điểm mát hơn
        temperature = sensor_data.get('temperature', 25)
        if temperature > 30:
            # Ưu tiên sáng sớm nếu trời nóng
            if "06:00" not in default_times:
                default_times.append("06:00")
            # Tránh buổi trưa
            if "12:00" in default_times:
                default_times.remove("12:00")
        
        return default_times
    
    def _optimize_by_zones(self, water_needs, optimal_times, zones, sensor_data) -> Dict[str, Any]:
        """
        Tối ưu hóa lịch tưới theo từng vùng.
        
        Args:
            water_needs: Nhu cầu nước cho các loại cây
            optimal_times: Các thời điểm tưới tối ưu
            zones: Thông tin về các vùng tưới
            sensor_data: Dữ liệu cảm biến hiện tại
            
        Returns:
            Lịch tưới tối ưu theo vùng
        """
        optimized_zones = []
        now = datetime.now()
        
        for i, zone in enumerate(zones):
            zone_plants = zone.get('plant_types', [])
            
            # Tính nhu cầu nước cho vùng này
            if zone_plants:
                zone_water_needs = [water_needs.get(plant, 0) for plant in zone_plants]
                duration = round(sum(zone_water_needs) / len(zone_water_needs), 1)
            else:
                # Nếu không có thông tin cây, sử dụng mặc định
                duration = self._default_duration(sensor_data)
            
            # Quyết định có tưới không
            should_irrigate = self._should_irrigate(duration, sensor_data, zone.get('soil_moisture'))
            
            # Tính thời gian tưới
            if should_irrigate:
                # Chia các vùng vào các thời điểm khác nhau để tránh quá tải
                time_index = i % len(optimal_times)
                irrigation_time = optimal_times[time_index]
                
                # Tính toán thời gian tuyệt đối
                hour, minute = map(int, irrigation_time.split(":"))
                irrigation_datetime = now.replace(hour=hour, minute=minute)
                
                # Nếu thời gian đã qua, lên lịch cho ngày mai
                if irrigation_datetime < now:
                    irrigation_datetime = irrigation_datetime + timedelta(days=1)
            else:
                irrigation_time = None
                irrigation_datetime = None
            
            optimized_zones.append({
                "zone_id": zone.get('id', str(i+1)),
                "name": zone.get('name', f"Zone {i+1}"),
                "should_irrigate": should_irrigate,
                "duration_minutes": duration if should_irrigate else 0,
                "irrigation_time": irrigation_time,
                "irrigation_datetime": irrigation_datetime.isoformat() if irrigation_datetime else None,
                "plant_types": zone_plants
            })
        
        # Tính tổng thời gian tưới
        total_duration = sum(z.get('duration_minutes', 0) for z in optimized_zones if z.get('should_irrigate', False))
        
        # Tổng hợp kết quả
        return {
            "zones": optimized_zones,
            "total_duration_minutes": total_duration,
            "soil_moisture": sensor_data.get('soil_moisture'),
            "temperature": sensor_data.get('temperature'),
            "humidity": sensor_data.get('humidity'),
            "should_irrigate": any(z.get('should_irrigate', False) for z in optimized_zones),
            "reason": self._generate_reason(sensor_data, water_needs),
            "timestamp": now.isoformat()
        }
    
    def _optimize_general(self, water_needs, optimal_times, sensor_data) -> Dict[str, Any]:
        """
        Tối ưu hóa lịch tưới tổng thể (không phân vùng).
        
        Args:
            water_needs: Nhu cầu nước cho các loại cây
            optimal_times: Các thời điểm tưới tối ưu
            sensor_data: Dữ liệu cảm biến hiện tại
            
        Returns:
            Lịch tưới tối ưu tổng thể
        """
        now = datetime.now()
        
        # Tính trung bình nhu cầu nước
        if water_needs:
            duration = round(sum(water_needs.values()) / len(water_needs), 1)
        else:
            duration = self._default_duration(sensor_data)
        
        # Quyết định có tưới không
        should_irrigate = self._should_irrigate(duration, sensor_data)
        
        # Tính thời gian tưới
        if should_irrigate and optimal_times:
            irrigation_time = optimal_times[0]
            
            # Tính toán thời gian tuyệt đối
            hour, minute = map(int, irrigation_time.split(":"))
            irrigation_datetime = now.replace(hour=hour, minute=minute)
            
            # Nếu thời gian đã qua, lên lịch cho ngày mai
            if irrigation_datetime < now:
                irrigation_datetime = irrigation_datetime + timedelta(days=1)
        else:
            irrigation_time = None
            irrigation_datetime = None
        
        # Tổng hợp kết quả
        return {
            "should_irrigate": should_irrigate,
            "duration_minutes": duration if should_irrigate else 0,
            "irrigation_time": irrigation_time,
            "irrigation_datetime": irrigation_datetime.isoformat() if irrigation_datetime else None,
            "soil_moisture": sensor_data.get('soil_moisture'),
            "temperature": sensor_data.get('temperature'),
            "humidity": sensor_data.get('humidity'),
            "reason": self._generate_reason(sensor_data, water_needs),
            "timestamp": now.isoformat()
        }
    
    def _should_irrigate(self, duration, sensor_data, zone_moisture=None) -> bool:
        """
        Quyết định có nên tưới không dựa trên nhu cầu nước và điều kiện hiện tại.
        
        Args:
            duration: Thời lượng tưới được tính toán
            sensor_data: Dữ liệu cảm biến
            zone_moisture: Độ ẩm đất của vùng cụ thể (nếu có)
            
        Returns:
            True nếu nên tưới, False nếu không
        """
        # Sử dụng độ ẩm đất vùng nếu có, nếu không sử dụng độ ẩm chung
        soil_moisture = zone_moisture if zone_moisture is not None else sensor_data.get('soil_moisture', 50)
        
        # Quyết định dựa trên độ ẩm đất và nhu cầu nước
        if soil_moisture < 30:
            # Tưới luôn nếu đất quá khô
            return True
        elif soil_moisture < 45:
            # Tưới nếu có nhu cầu nước đáng kể
            return duration >= 5
        elif soil_moisture < 60:
            # Chỉ tưới nếu có nhu cầu nước cao
            return duration >= 10
        else:
            # Không tưới nếu đất đủ ẩm
            return False
    
    def _default_duration(self, sensor_data) -> float:
        """
        Tính thời lượng tưới mặc định dựa trên độ ẩm đất.
        
        Args:
            sensor_data: Dữ liệu cảm biến
            
        Returns:
            Thời lượng tưới mặc định (phút)
        """
        soil_moisture = sensor_data.get('soil_moisture', 50)
        
        if soil_moisture < 20:
            return 15.0  # Rất khô, tưới nhiều
        elif soil_moisture < 30:
            return 10.0  # Khô, tưới trung bình
        elif soil_moisture < 45:
            return 5.0   # Hơi khô, tưới nhẹ
        else:
            return 0.0   # Đủ ẩm, không tưới
    
    def _generate_reason(self, sensor_data, water_needs) -> str:
        """
        Tạo lý do cho khuyến nghị tưới.
        
        Args:
            sensor_data: Dữ liệu cảm biến
            water_needs: Nhu cầu nước cho các loại cây
            
        Returns:
            Chuỗi lý do
        """
        soil_moisture = sensor_data.get('soil_moisture', 50)
        temperature = sensor_data.get('temperature', 25)
        humidity = sensor_data.get('humidity', 60)
        
        if soil_moisture < 30:
            return f"Đất quá khô ({soil_moisture}%), cần tưới ngay"
        
        if temperature > 30 and humidity < 50:
            return f"Thời tiết nóng ({temperature}°C) và khô ({humidity}%), cần bổ sung nước"
        
        if water_needs and sum(water_needs.values()) / len(water_needs) > 10:
            return "Cây trồng có nhu cầu nước cao dựa trên điều kiện hiện tại"
            
        return f"Độ ẩm đất ({soil_moisture}%) đủ cho nhu cầu hiện tại"
    
    def _load_plant_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Tải thông tin về các loại cây trồng.
        
        Returns:
            Dict chứa thông tin cây trồng
        """
        try:
            # Cố gắng tải từ file
            with open('data/plant_profiles/profiles.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load plant profiles: {str(e)}")
            
            # Sử dụng một số profiles mặc định
            return {
                "tomato": {
                    "water_need_factor": 1.2,
                    "optimal_soil_moisture": 65,
                    "drought_tolerance": 0.4
                },
                "cucumber": {
                    "water_need_factor": 1.3,
                    "optimal_soil_moisture": 70,
                    "drought_tolerance": 0.3
                },
                "lettuce": {
                    "water_need_factor": 1.0,
                    "optimal_soil_moisture": 60,
                    "drought_tolerance": 0.2
                },
                "pepper": {
                    "water_need_factor": 0.8,
                    "optimal_soil_moisture": 55,
                    "drought_tolerance": 0.6
                },
                "default": {
                    "water_need_factor": 1.0,
                    "optimal_soil_moisture": 60,
                    "drought_tolerance": 0.5
                }
            }