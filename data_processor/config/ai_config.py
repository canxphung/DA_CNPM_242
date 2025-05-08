"""
Cấu hình cho tích hợp AI Service.
"""

# Cấu hình nhận khuyến nghị từ AI
AI_RECOMMENDATION_CONFIG = {
    # Cho phép áp dụng khuyến nghị từ AI Service
    "enabled": True,
    
    # Các nguồn khuyến nghị được phép
    "allowed_sources": ["ai_service", "all"],
    
    # Mức ưu tiên tối thiểu để áp dụng ngay
    "min_priority_for_immediate": "high",
    
    # Ngưỡng độ tin cậy tối thiểu
    "min_confidence": 0.7
}