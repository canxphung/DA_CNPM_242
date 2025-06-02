"""
Cấu hình intervals cho các tác vụ định kỳ trong hệ thống.
"""

TASK_INTERVALS = {
    # Kiểm tra trạng thái máy bơm - giữ nguyên vì cần phản hồi nhanh
    "pump_status": 15,
    
    # Thu thập dữ liệu từ cảm biến - TĂNG LÊN để giảm tải
    "sensor_data": 180,  # 3 phút thay vì 60s
    
    # Kiểm tra lịch tưới - giữ nguyên
    "schedule_check": 60,
    
    # Ra quyết định tưới tự động - GIẢM XUỐNG cho phản hồi nhanh hơn
    "auto_decision": 600,  # 10 phút thay vì 15 phút
    
    # Đồng bộ trạng thái máy bơm
    "pump_sync": 30,  # Tăng lên 30s thay vì 15s
    
    # Intervals khác
    "data_cleanup": 3600,     # Giữ nguyên 1 giờ
    "stats_calculation": 1800, # Giữ nguyên 30 phút
    
    # Intervals mới cho optimization
    "cache_refresh": 300,     # Refresh cache mỗi 5 phút
    "batch_sync": 600,        # Batch sync với Adafruit mỗi 10 phút
}

# Intervals động theo thời gian trong ngày
DYNAMIC_INTERVALS = {
    "sensor_data": {
        "peak": 120,     # 2 phút (6-10 sáng, 14-18 chiều)
        "normal": 180,   # 3 phút (10-14, 18-22)
        "off_peak": 300  # 5 phút (22-6 sáng)
    },
    "auto_decision": {
        "peak": 300,     # 5 phút
        "normal": 600,   # 10 phút  
        "off_peak": 900  # 15 phút
    }
}

# Định nghĩa giới hạn tối thiểu cho mỗi loại task
# Điều này giúp tránh cấu hình sai làm quá tải hệ thống
MIN_INTERVALS = {
    "pump_status": 5,       # Tối thiểu 5 giây
    "sensor_data": 30,      # Tối thiểu 30 giây
    "schedule_check": 30,   # Tối thiểu 30 giây
    "auto_decision": 300,   # Tối thiểu 5 phút
    "pump_sync": 5,         # Tối thiểu 5 giây
    "data_cleanup": 600,    # Tối thiểu 10 phút
    "stats_calculation": 600 # Tối thiểu 10 phút
}

# Peak hours definition
PEAK_HOURS = {
    "morning": (6, 10),   # 6:00 - 10:00
    "afternoon": (14, 18) # 14:00 - 18:00
}


# Định nghĩa mô tả cho từng interval
# Giúp người dùng hiểu rõ mục đích của từng task
INTERVAL_DESCRIPTIONS = {
    "pump_status": "Kiểm tra trạng thái máy bơm (bật/tắt, thời gian chạy)",
    "sensor_data": "Thu thập dữ liệu từ các cảm biến (nhiệt độ, độ ẩm, ánh sáng, độ ẩm đất)",
    "schedule_check": "Kiểm tra và thực hiện lịch tưới đã đặt",
    "auto_decision": "Phân tích môi trường và ra quyết định tưới tự động",
    "pump_sync": "Đồng bộ trạng thái máy bơm với Adafruit IO",
    "data_cleanup": "Dọn dẹp dữ liệu cũ trong cache",
    "stats_calculation": "Tính toán thống kê sử dụng nước và hiệu suất"
}

# Hàm helper để validate interval
def validate_interval(task_type: str, interval: int) -> int:
    """
    Kiểm tra và điều chỉnh interval cho phù hợp với giới hạn tối thiểu.
    
    Args:
        task_type: Loại task
        interval: Giá trị interval mong muốn (giây)
        
    Returns:
        Interval đã được điều chỉnh (nếu cần)
    """
    min_interval = MIN_INTERVALS.get(task_type, 30)
    
    if interval < min_interval:
        return min_interval
    
    return interval

# Hàm helper để lấy interval với fallback
def get_interval(task_type: str, default: int = 60) -> int:
    """
    Lấy interval cho một loại task cụ thể.
    
    Args:
        task_type: Loại task
        default: Giá trị mặc định nếu không tìm thấy
        
    Returns:
        Interval (giây)
    """
    return TASK_INTERVALS.get(task_type, default)
def get_dynamic_interval(task_type: str) -> int:
    """Lấy interval động dựa trên thời gian."""
    from datetime import datetime
    
    if task_type not in DYNAMIC_INTERVALS:
        return TASK_INTERVALS.get(task_type, 60)
    
    hour = datetime.now().hour
    
    # Peak hours: 6-10, 14-18
    if (6 <= hour < 10) or (14 <= hour < 18):
        period = "peak"
    # Off-peak: 22-6
    elif hour >= 22 or hour < 6:
        period = "off_peak"
    else:
        period = "normal"
    
    return DYNAMIC_INTERVALS[task_type][period]