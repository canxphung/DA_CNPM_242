// utils/aiChatService.js
import api from "./api";
import { API_ENDPOINTS, ERROR_MESSAGES, HTTP_STATUS } from "./constants";
// Không cần import sensorService hay deviceControlService ở đây nữa

class AIChatService {
  constructor() {
    this.conversationHistory = [];
    this.sessionId = this.generateSessionId();
    // Các thuộc tính khác như responseCache, chatAnalytics, confidenceThresholds có thể giữ nếu vẫn thấy hữu ích
  }

  generateSessionId() {
    return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  async sendMessage(message, options = {}) {
    const { userId = null } = options; // Chỉ cần userId từ client nếu backend AI cần
    const startTime = Date.now();

    try {
      // Payload giờ đây đơn giản hơn nhiều, không cần client gửi context hệ thống
      const payload = {
        text: message,
        // session_id: this.sessionId, // Gửi nếu backend AI cần để duy trì hội thoại
        timestamp: new Date().toISOString(),
      };
      if (userId) payload.user_id = userId;
      // Backend AI Service sẽ tự lấy sensor data, system status khi cần.

      console.log('Sending message to AI Chat Service:', payload.text);
      
      const response = await api.post(API_ENDPOINTS.AI.CHAT_MESSAGE, payload);
      // API Response: { text, intent, actions_taken (array of strings mô tả action), timestamp }
      
      const aiServiceResponse = response.data;

      // Log actions AI đã tự thực hiện (hoặc trigger)
      if (aiServiceResponse.actions_taken && aiServiceResponse.actions_taken.length > 0) {
        console.log("AI Service reported these actions were taken/triggered:", aiServiceResponse.actions_taken);
        // Frontend có thể hiển thị thông báo này hoặc trigger refresh một phần UI nào đó nếu cần
        // Ví dụ, nếu actions_taken bao gồm "Scheduled irrigation for Zone A",
        // bạn có thể trigger việc fetch lại schedule data.
      }
      
      this.updateConversationHistory(message, aiServiceResponse); // Lưu lại cuộc hội thoại
      // updateChatAnalytics() // giữ lại nếu bạn có cơ chế thu thập analytics
      
      return {
        success: true,
        response: { 
            text: aiServiceResponse.text,
            intent: aiServiceResponse.intent,
            actions_taken_by_ai: aiServiceResponse.actions_taken || [], // Để AIChat.jsx có thể hiển thị
            timestamp: aiServiceResponse.timestamp || new Date().toISOString(),
        },
        processingTime: Date.now() - startTime
      };

    } catch (error) {
      console.error('AI Chat Service error (service wrapper):', error.message, error.originalError);
      const fallback = this.generateFallbackResponse(message, error);
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        response: fallback, // fallback object { text, intent, fallback, ... }
      };
    }
  }
  
  updateConversationHistory(userMessage, aiResponse) {
    const entry = {
      timestamp: new Date().toISOString(),
      user_message: userMessage,
      ai_response_text: aiResponse.text,
      intent: aiResponse.intent,
      actions_taken_by_ai: aiResponse.actions_taken || [], // Key này nhất quán với response gửi về component
    };
    this.conversationHistory.push(entry);
    if (this.conversationHistory.length > 20) this.conversationHistory.shift(); // Giới hạn lịch sử chat
  }
  
  generateFallbackResponse(message, error) {
     let responseText = 'Xin lỗi, tôi gặp sự cố khi xử lý yêu cầu của bạn.';
     if (error.status === HTTP_STATUS.TOO_MANY_REQUESTS) {
         responseText = "Bạn đã tương tác quá nhanh. Vui lòng chờ một lát rồi thử lại."
     } else if (error.isNetworkError || error.status === 0) { // Network error
         responseText = "Không thể kết nối đến trợ lý AI. Vui lòng kiểm tra kết nối mạng của bạn."
     } else if (error.status === HTTP_STATUS.SERVICE_UNAVAILABLE) {
         responseText = "Trợ lý AI tạm thời không khả dụng. Vui lòng thử lại sau."
     } else if (error.message) {
         responseText = `Lỗi: ${error.message.substring(0,150)}`; // Hiển thị một phần lỗi nếu có
     }

    return {
      text: responseText,
      intent: 'fallback_error',
      fallback: true, // Để UI biết đây là fallback
      actions_taken_by_ai: [],
      timestamp: new Date().toISOString(),
    };
  }
  
  resetSession() {
    this.conversationHistory = [];
    this.sessionId = this.generateSessionId(); // Tạo session ID mới
    console.log("AI Chat session has been reset.");
  }
}

const aiChatService = new AIChatService();
export default aiChatService;