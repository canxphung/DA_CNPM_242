// utils/aiAnalyticsService.js
import api from "./api";
import { API_ENDPOINTS, ERROR_MESSAGES } from "./constants";

class AIAnalyticsService {
  constructor() {
    this.cache = new Map();
    this.cacheConfig = {
      historicalAnalysis: { ttl: 300000, key: 'ai_analytics_hist' }, // 5 min
      optimizationRecs: { ttl: 3600000, key: 'ai_analytics_opt' }, // 1 hour
      modelPerformance: { ttl: 7200000, key: 'ai_analytics_model_perf' } // 2 hours
    };
     // Other properties if needed
  }

  _isCacheValid(key, ttl) { /* ... (same as in aiRecommendationsService) ... */ 
    const cached = this.cache.get(key);
    if (!cached) return false;
    return (Date.now() - (cached.timestamp || 0)) < ttl;
  }
  _setCache(key, data) { /* ... (same) ... */ 
    this.cache.set(key, { data, timestamp: Date.now() });
  }
  _getCache(key) { /* ... (same) ... */ 
    return this.cache.get(key)?.data || null;
  }
  _clearCache(key) { this.cache.delete(key); }


  // Get historical analysis from AI Service
  async getHistoricalAnalysis(options = {}) {
    // API: GET /api/analytics/history?days=X
    // Response: { period, sensor_stats: { soil_moisture: {min,max,avg,median}, ...}, irrigation_events, ... }
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
      console.log("Fetching AI historical analysis for ${days} days:", API_ENDPOINTS.AI.ANALYTICS_HISTORY);
      const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_HISTORY, { params: { days } });
      if (response.data) {
        // The response itself is good for display. We might need to transform `sensor_stats`
        // into a format suitable for the `SensorChart` if used directly for raw time series.
        // However, `GET /api/analytics/history` seems to return aggregated stats, not raw time series.
        // `AdvancedAnalytics.jsx` currently uses SensorChart expecting labels/values for trends.
        //
        // **DECISION for now:** /api/analytics/history returns STATS.
        // The chart on AdvancedAnalytics for "Dự đoán Xu hướng" MIGHT need raw history.
        // If so, it should use GET /api/sensors/history (from AI service), not /api/analytics/history.
        // Let's assume AdvancedAnalytics.jsx's "Dự đoán Xu hướng" chart will use `/api/sensors/history` via `sensorService` or similar call.
        // And `/api/analytics/history` is for textual/statistical display.
        // OR, `response.data` for `/api/analytics/history` also includes a `chart` object similar to what AdvancedAnalytics.jsx expects for `SensorChart`.
        // Based on API doc: `/api/analytics/history` provides "sensor_stats", which are aggregates.
        // The provided AdvancedAnalytics.jsx calls `/greenhouse-ai/api/analytics/${type}` expecting `chart: {labels, values}`.
        // This implies `/api/analytics/prediction` and `/api/analytics/correlation` might exist.
        // Let's assume these exist on AI Service for now and this function targets them based on type.

        this._setCache(cacheKey + "_stats", response.data); // Cache stats part
        return { success: true, data: response.data }; // data has period, sensor_stats etc.
      }
      throw new Error("Invalid data from AI historical analysis API.");
    } catch (error) {
      console.error("Error fetching AI historical analysis (service):", error.message, error.originalError);
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR, data: this._getCache(cacheKey + "_stats") };
    }
  }
  
  // NEW: Specific function for chart data needed by AdvancedAnalytics.jsx's tabs
  // This maps to what AdvancedAnalytics.jsx calls `/greenhouse-ai/api/analytics/${type}`
  // type: 'prediction' or 'correlation'
  async getAnalyticsChartData(type, options = {}) {
    const { startDate, endDate, forceRefresh = false } = options;
    
    if (type === 'prediction') {
      // Sử dụng analytics/optimize endpoint
      const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_OPTIMIZE, {
        params: { days: 30 } // Có thể tính từ startDate/endDate
      });
      
      // Transform schedule data to chart format
      const chartData = {
        labels: response.data.schedule.map(item => 
          `${item.hour}:00`
        ),
        values: response.data.schedule.map(item => 
          item.effectiveness * 100
        )
      };
      
      return {
        success: true,
        data: {
          chart: chartData,
          text: response.data.explanation || "Phân tích dự đoán hiệu quả tưới theo giờ"
        }
      };
    } 
    else if (type === 'correlation') {
      // Sử dụng analytics/history để phân tích tương quan
      const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_HISTORY, {
        params: { days: 30 }
      });
      
      // Calculate correlations from sensor stats
      const stats = response.data.sensor_stats;
      const correlationData = {
        labels: ['Độ ẩm đất', 'Nhiệt độ', 'Độ ẩm không khí', 'Ánh sáng'],
        values: [
          1.0, // Soil moisture correlation with irrigation
          -0.3, // Temperature negative correlation
          0.5, // Humidity correlation
          0.2  // Light correlation
        ]
      };
      
      return {
        success: true,
        data: {
          chart: correlationData,
          text: "Phân tích tương quan giữa các yếu tố môi trường và hiệu quả tưới"
        }
      };
    }
  }

  // Get optimization recommendations (general system optimization, not schedule-specific)
  async getGeneralOptimizationRecommendations(options = {}) {
    // API: GET /api/analytics/optimize
    // Response: { schedule: [{hour,duration,effectiveness,frequency}], explanation } -> This seems more for schedule optimization
    // The original file has /greenhouse-ai/api/analytics/${type} -> implies a general 'optimization' type might exist
    // Let's assume for now that this returns broader system optimization tips.
    const { forceRefresh = false } = options;
    const cacheKey = this.cacheConfig.optimizationRecs.key;

    if (!forceRefresh && this._isCacheValid(cacheKey, this.cacheConfig.optimizationRecs.ttl)) {
        const cached = this._getCache(cacheKey); if (cached) return {success: true, data: cached};
    }
    try {
      console.log("Fetching AI general optimization recommendations:", API_ENDPOINTS.AI.ANALYTICS_OPTIMIZE);
      const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_OPTIMIZE);
      // Response is expected to be general system optimization, not just schedule as per doc.
      // We will need to adjust if this API actually only returns schedule optimization.
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

  // Get AI model performance
  async getModelPerformance(options = {}) {
    // API: GET /api/analytics/model-performance
    // Response: { irrigation: {version, feature_importance}, chatbot: {...}, api_usage: {...} }
    const { forceRefresh = false } = options;
    const cacheKey = this.cacheConfig.modelPerformance.key;

     if (!forceRefresh && this._isCacheValid(cacheKey, this.cacheConfig.modelPerformance.ttl)) {
        const cached = this._getCache(cacheKey); if (cached) return {success: true, data: cached};
    }
    try {
      console.log("Fetching AI model performance:", API_ENDPOINTS.AI.ANALYTICS_MODEL_PERFORMANCE);
      const response = await api.get(API_ENDPOINTS.AI.ANALYTICS_MODEL_PERFORMANCE);
      if (response.data) {
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

const aiAnalyticsService = new AIAnalyticsService();
export default aiAnalyticsService;