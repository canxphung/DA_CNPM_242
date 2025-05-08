# src/external_api/prompts.py
class PromptTemplates:
    """
    Collection of prompt templates for OpenAI API.
    """
    
    # Intent classification prompt
    INTENT_CLASSIFICATION = """
    Bạn là hệ thống phân loại ý định cho nhà kính thông minh. Phân loại 
    văn bản đầu vào thành một trong các ý định: query_soil_moisture, 
    query_temperature, query_humidity, query_light, turn_on_pump, turn_off_pump, 
    get_status, schedule_irrigation. Trả về duy nhất tên ý định.
    """
    
    # Entity extraction prompt
    ENTITY_EXTRACTION = """
    Trích xuất tất cả thông tin quan trọng từ văn bản đầu vào. Tập trung vào 
    các giá trị số, đơn vị thời gian, và tham số. Trả về dưới dạng JSON.
    """
    
    # Irrigation recommendation prompt
    IRRIGATION_RECOMMENDATION = """
    Bạn là chuyên gia tưới tiêu. Dựa trên dữ liệu cảm biến, hãy đưa ra khuyến 
    nghị có nên tưới không và trong bao lâu. Nếu độ ẩm đất thấp hơn 30%, 
    nhiệt độ cao, và độ ẩm không khí thấp, rất có thể cần tưới.
    Trả về JSON với should_irrigate (true/false), duration_minutes (số phút) và reason (lý do).
    """
    
    # Response generation prompt
    RESPONSE_GENERATION = """
    Bạn là trợ lý thông minh cho hệ thống nhà kính. Hãy tạo phản hồi tự nhiên 
    bằng tiếng Việt dựa trên ý định của người dùng và dữ liệu cảm biến. 
    Giữ câu trả lời ngắn gọn, thân thiện và hữu ích.
    """
    
    # Analyze sensor data prompt
    SENSOR_ANALYSIS = """
    Phân tích dữ liệu cảm biến sau và đưa ra nhận xét về tình trạng nhà kính.
    Nêu bất kỳ vấn đề nào cần chú ý và đề xuất hành động nếu cần.
    Trả về JSON với các trường: status, issues, recommendations.
    """
    
    # Schedule optimization prompt
    SCHEDULE_OPTIMIZATION = """
    Dựa trên dữ liệu lịch sử tưới và cảm biến, hãy đề xuất lịch tưới tối ưu.
    Xem xét các mẫu theo thời gian trong ngày, điều kiện thời tiết, và hiệu quả tưới.
    Trả về JSON với trường schedule chứa danh sách các thời điểm tưới đề xuất.
    """
    
    @staticmethod
    def format_irrigation_recommendation(sensor_data):
        """
        Format the irrigation recommendation prompt with current sensor data.
        
        Args:
            sensor_data: Dictionary with current sensor readings
            
        Returns:
            Formatted prompt string
        """
        return f"""
        Dữ liệu hiện tại:
        Độ ẩm đất: {sensor_data.get('soil_moisture', 'N/A')}%
        Nhiệt độ: {sensor_data.get('temperature', 'N/A')}°C
        Độ ẩm không khí: {sensor_data.get('humidity', 'N/A')}%
        Ánh sáng: {sensor_data.get('light_level', 'N/A')} lux
        """
    
    @staticmethod
    def format_sensor_analysis(sensor_data, historical_data=None):
        """
        Format the sensor analysis prompt with current and historical data.
        
        Args:
            sensor_data: Dictionary with current sensor readings
            historical_data: Optional list of historical sensor readings
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""
        Dữ liệu hiện tại:
        Độ ẩm đất: {sensor_data.get('soil_moisture', 'N/A')}%
        Nhiệt độ: {sensor_data.get('temperature', 'N/A')}°C
        Độ ẩm không khí: {sensor_data.get('humidity', 'N/A')}%
        Ánh sáng: {sensor_data.get('light_level', 'N/A')} lux
        """
        
        if historical_data:
            prompt += "\n\nDữ liệu lịch sử (24 giờ qua):\n"
            for i, data in enumerate(historical_data):
                timestamp = data.get('timestamp', f"Thời điểm {i+1}")
                prompt += f"""
                {timestamp}:
                Độ ẩm đất: {data.get('soil_moisture', 'N/A')}%
                Nhiệt độ: {data.get('temperature', 'N/A')}°C
                Độ ẩm không khí: {data.get('humidity', 'N/A')}%
                Ánh sáng: {data.get('light_level', 'N/A')} lux
                ---
                """
        
        return prompt