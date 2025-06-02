// utils/aiAnalyticsService.js
import api from "./api";
import { API_ENDPOINTS, ERROR_MESSAGES } from "./constants"; // ERROR_MESSAGES vẫn cần thiết cho các lỗi khác

class AIAnalyticsService {
  constructor() {
    this.cache = new Map();
    this.cacheConfig = {
      historicalAnalysis: { ttl: 300000, key: 'ai_analytics_hist' },
      optimizationRecs: { ttl: 3600000, key: 'ai_analytics_opt' },
      modelPerformance: { ttl: 7200000, key: 'ai_analytics_model_perf' }
    };
  }

  _isCacheValid(key, ttl) { /* ... (như cũ) ... */ 
    const cached = this.cache.get(key);
    if (!cached) return false;
    return (Date.now() - (cached.timestamp || 0)) < ttl;
  }
  _setCache(key, data) { /* ... (như cũ) ... */ 
    this.cache.set(key, { data, timestamp: Date.now() });
  }
  _getCache(key) { /* ... (như cũ) ... */ 
    return this.cache.get(key)?.data || null;
  }
  _clearCache(key) { this.cache.delete(key); }

  async getHistoricalAnalysis(options = {}) {
    const { days = 7, forceRefresh = false } = options;
    const cacheKey = `${this.cacheConfig.historicalAnalysis.key}_${days}`;

    if (!forceRefresh && this._isCacheValid(cacheKey, this.cacheConfig.historicalAnalysis.ttl)) {
      const cachedData = this._getCache(cacheKey);
      if (cachedData) {
        console.log('Using cached AI historical analysis');
        return { success: true, data: cachedData };
      }
    }
    try {
      console.log(`Fetching AI historical analysis for ${days} days:`, API_ENDPOINTS.AI.ANALYTICS_HISTORY);
      const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_HISTORY, { params: { days } });
      // API response is now always 200 OK, check for 'message' field from backend
      if (response.data) { // response.data sẽ luôn tồn tại nếu API thành công (200 OK)
        this._setCache(cacheKey + "_stats", response.data);
        // Nếu có message từ backend, có thể dùng nó để bổ sung thông tin
        let analysisText = `Phân tích lịch sử cho giai đoạn ${response.data.period}.`;
        if(response.data.message) {
            analysisText += `\nLưu ý: ${response.data.message}`;
        }
        // Vẫn trả về data để UI có thể hiển thị stats (dù có thể là 0)
        return { success: true, data: {...response.data, derivedText: analysisText} }; 
      }
      // Về lý thuyết không nên rơi vào đây nếu API luôn trả 200 và có data
      throw new Error("Invalid data from AI historical analysis API despite 200 OK."); 
    } catch (error) {
      console.error("Error fetching AI historical analysis (service):", error.message, error.originalError);
      // Lỗi ở đây thường là network error hoặc lỗi 500 từ server, không phải 404 vì không đủ dữ liệu
      return { 
          success: false, 
          error: error.message || ERROR_MESSAGES.SERVER_ERROR, 
          data: this._getCache(cacheKey + "_stats") // trả về cache cũ nếu có lỗi
        };
    }
  }
  
  async getAnalyticsChartData(type, options = {}) {
    const { startDate, endDate, forceRefresh = false, days = 30 } = options; // days default cho API
    
    try {
      if (type === 'prediction') {
        // API_ENDPOINTS.AI.ANALYTICS_OPTIMIZE sẽ trả về { schedule: [], explanation: "..." } nếu không đủ dữ liệu
        const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_OPTIMIZE, {
          params: { days } // days truyền vào từ options hoặc default
        });
        
        let chartData = { labels: [], values: [] };
        let textResult = response.data.explanation || "Không có diễn giải cho dự đoán này.";

        if (response.data && response.data.schedule && response.data.schedule.length > 0) {
          chartData = {
            labels: response.data.schedule.map(item => `${item.hour}:00`),
            values: response.data.schedule.map(item => item.effectiveness_score * 100) // Sửa thành effectiveness_score
          };
        } else if (response.data && response.data.explanation) {
            // Explanation sẽ chứa lý do không có schedule
            textResult = response.data.explanation;
        }

        return {
          success: true,
          data: { chart: chartData, text: textResult }
        };

      } else if (type === 'correlation') {
        // API_ENDPOINTS.AI.ANALYTICS_HISTORY sẽ trả về message nếu không có sensor data
        const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_HISTORY, {
          params: { days } // days truyền vào từ options hoặc default
        });
        
        let chartData = { labels: [], values: [] };
        let textResult = `Phân tích tương quan cho giai đoạn ${response.data.period || days + ' ngày'}.`;
        if (response.data.message) { // Thông báo từ backend nếu không có dữ liệu
            textResult = response.data.message;
        }

        // Hiện tại, API /history không trực tiếp trả về dữ liệu "tương quan".
        // Nó trả về sensor_stats. Chúng ta cần tự tính toán tương quan hoặc hiển thị stats đó.
        // Giả sử chúng ta chỉ hiển thị thông báo hoặc một biểu đồ đơn giản từ stats.
        if (response.data && response.data.sensor_stats && !response.data.message) { // Chỉ tạo chart nếu có stats và không có message "không dữ liệu"
            const stats = response.data.sensor_stats;
            // Ví dụ: tạo biểu đồ hiển thị giá trị trung bình của các sensor
            // Đây KHÔNG phải là tương quan, chỉ là ví dụ chart từ stats
             chartData = {
                labels: Object.keys(stats).map(key => CHART_CONFIG[key]?.title || key), // Lấy title từ CHART_CONFIG
                values: Object.values(stats).map(statData => statData.avg || 0)
            };
            textResult += "\nBiểu đồ thể hiện giá trị trung bình của các cảm biến. " +
                          "Để phân tích tương quan sâu hơn, cần mô hình AI phức tạp hơn.";
            // Nếu backend trả message, textResult đã được set
        } else if (response.data.message) {
            // textResult đã chứa response.data.message rồi.
        } else {
            textResult = "Không có đủ dữ liệu thống kê để hiển thị hoặc phân tích tương quan.";
        }

        return {
          success: true,
          data: { chart: chartData, text: textResult }
        };
      }
      // Mặc định nếu type không hợp lệ
      return { success: false, error: "Loại phân tích không hợp lệ.", data: { chart: {labels: [], values:[]}, text:""}};

    } catch (error) { // Lỗi thực sự từ api client (network, 500,...)
      console.error(`Error fetching analytics chart data for ${type}:`, error);
      return { 
        success: false, 
        error: error.message || ERROR_MESSAGES.SERVER_ERROR, 
        data: { chart: {labels: [], values:[]}, text:"Đã xảy ra lỗi khi tải dữ liệu."} 
      };
    }
  }

  async getGeneralOptimizationRecommendations(options = {}) { /* ... (Như cũ, nếu dùng API khác) ... */ 
    const { forceRefresh = false } = options;
    const cacheKey = this.cacheConfig.optimizationRecs.key;

    if (!forceRefresh && this._isCacheValid(cacheKey, this.cacheConfig.optimizationRecs.ttl)) {
        const cached = this._getCache(cacheKey); if (cached) return {success: true, data: cached};
    }
    try {
      console.log("Fetching AI general optimization recommendations:", API_ENDPOINTS.AI.ANALYTICS_OPTIMIZE);
      const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_OPTIMIZE);
      // API này giờ cũng trả 200 OK, với explanation nếu không có schedule
      if (response.data) {
        this._setCache(cacheKey, response.data);
        return { success: true, data: response.data };
      }
      throw new Error("Invalid data from AI optimization API.");
    } catch (error) {
      console.error("Error fetching AI general optimization (service):", error.message, error.originalError);
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR, data: this._getCache(cacheKey)};
    }
  }
  async getModelPerformance(options = {}) { /* ... (Như cũ) ... */
    const { forceRefresh = false } = options;
    const cacheKey = this.cacheConfig.modelPerformance.key;

     if (!forceRefresh && this._isCacheValid(cacheKey, this.cacheConfig.modelPerformance.ttl)) {
        const cached = this._getCache(cacheKey); if (cached) return {success: true, data: cached};
    }
    try {
      console.log("Fetching AI model performance:", API_ENDPOINTS.AI.ANALYTICS_MODEL_PERFORMANCE);
      const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_MODEL_PERFORMANCE);
      if (response.data) {
        // Nếu backend trả message (vd: No model performance data), nó sẽ nằm trong response.data
        this._setCache(cacheKey, response.data);
        return { success: true, data: response.data };
      }
      throw new Error("Invalid data from AI model performance API.");
    } catch (error) {
      console.error("Error fetching AI model performance (service):", error.message, error.originalError);
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR, data: this._getCache(cacheKey) };
    }
  }
}

// Thêm CHART_CONFIG vào file này nếu chưa có, hoặc import từ constants.js
// Giả sử CHART_CONFIG đã được import từ constants.js
import { CHART_CONFIG } from "./constants"; // Import CHART_CONFIG

const aiAnalyticsService = new AIAnalyticsService();
export default aiAnalyticsService;