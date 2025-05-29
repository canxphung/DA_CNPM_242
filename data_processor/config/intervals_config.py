"""
Cấu hình intervals cho các tác vụ định kỳ trong hệ thống.
"""

# Định nghĩa các intervals mặc định (tính bằng giây)
TASK_INTERVALS = {
    # Kiểm tra trạng thái máy bơm - cần phản hồi nhanh
    "pump_status": 15,
    
    # Thu thập dữ liệu từ các cảm biến - không cần quá thường xuyên
    "sensor_data": 60,
    
    # Kiểm tra lịch tưới - cần độ chính xác trong vòng 1 phút
    "schedule_check": 60,
    
    # Ra quyết định tưới tự động - không nên quá thường xuyên
    "auto_decision": 900,
    
    # Đồng bộ trạng thái máy bơm với Adafruit
    "pump_sync": 15,
    
    # Các intervals khác có thể thêm vào sau
    "data_cleanup": 3600,     # Dọn dẹp dữ liệu cũ mỗi giờ
    "stats_calculation": 1800  # Tính toán thống kê mỗi 30 phút
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