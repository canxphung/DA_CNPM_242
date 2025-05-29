// utils/aiRecommendationsService.js
import api from "./api";
import { API_ENDPOINTS, ERROR_MESSAGES, HTTP_STATUS } from "./constants";

class AIRecommendationsService {
  constructor() {
    this.cache = new Map();
    this.cacheConfig = {
      // Removed immediate recommendations as per new understanding
      recommendationHistory: { ttl: 120000, key: 'ai_rec_history' }, // 2 minutes for history
      optimizedSchedule: { ttl: 3600000, key: 'ai_opt_schedule' }, // 1 hour for optimized schedule
    };
    // Analytics and other properties can be kept if they were for internal service tracking
    this.recommendationAnalytics = { /* ... (keep if used for anything else) ... */ };
  }

  _isCacheValid(key, ttl) {
    const cached = this.cache.get(key);
    if (!cached) return false;
    return (Date.now() - (cached.timestamp || 0)) < ttl;
  }

  _setCache(key, data) {
    this.cache.set(key, { data, timestamp: Date.now() });
  }

  _getCache(key) {
    return this.cache.get(key)?.data || null;
  }
  _clearCache(key) {
      this.cache.delete(key);
      console.log(`Cache for ${key} cleared.`);
  }


  // Fetch recommendation history
  async getRecommendationHistory(options = {}) {
    const { days = 7, forceRefresh = false } = options;
    const cacheKey = `${this.cacheConfig.recommendationHistory.key}_${days}`;

    if (!forceRefresh && this._isCacheValid(cacheKey, this.cacheConfig.recommendationHistory.ttl)) {
      const cachedData = this._getCache(cacheKey);
      if (cachedData) {
        console.log('Using cached AI recommendation history');
        return { success: true, data: cachedData };
      }
    }

    try {
      console.log(`Fetching AI recommendation history for ${days} days from:`, API_ENDPOINTS.AI.RECOMMENDATION_HISTORY);
      const response = await api.get(API_ENDPOINTS.AI.RECOMMENDATION_HISTORY, {
        params: { days } // Assuming AI service uses 'days' query param
      });
      // API Doc Output: Array of { id, timestamp, recommendation: {should_irrigate, zones, reason, ...}, status, result: {irrigation_completed, ...} }
      
      if (response.data && Array.isArray(response.data)) {
        // Optional: Further process/enhance history data here if needed for UI
        const processedHistory = response.data.map(item => ({
            ...item,
            // Example enhancement: make timestamp more readable for direct display
            displayTimestamp: new Date(item.timestamp).toLocaleString('vi-VN'),
            isActionable: item.status === 'created' || item.status === 'pending_approval', // Can this be resent?
        }));
        this._setCache(cacheKey, processedHistory);
        return { success: true, data: processedHistory };
      }
      throw new Error("Invalid data structure from recommendation history API.");

    } catch (error) {
      console.error("Error fetching AI recommendation history (service):", error.message, error.originalError);
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        data: this._getCache(cacheKey) || [], // Return cached on error or empty
      };
    }
  }

  // Fetch optimized irrigation schedule from AI
  async getOptimizedSchedule(options = {}) {
    // API doc for GET /api/recommendation/optimize/schedule has `analysis_period_days`
    // and output `schedule: [{ day, schedule: [{ time, duration_minutes, effectiveness }] }]`
    const { analysis_period_days = 14, forceRefresh = false } = options; // Default 14 days analysis
    const cacheKey = `${this.cacheConfig.optimizedSchedule.key}_${analysis_period_days}`;

    if (!forceRefresh && this._isCacheValid(cacheKey, this.cacheConfig.optimizedSchedule.ttl)) {
      const cachedData = this._getCache(cacheKey);
      if (cachedData) {
        console.log('Using cached AI optimized schedule');
        return { success: true, data: cachedData };
      }
    }

    try {
      console.log("Fetching AI optimized schedule from:", API_ENDPOINTS.AI.RECOMMENDATION_OPTIMIZE_SCHEDULE);
      const response = await api.get(API_ENDPOINTS.AI.RECOMMENDATION_OPTIMIZE_SCHEDULE, {
          params: { analysis_period_days } // Assuming query param is 'analysis_period_days'
      });
      
      // API Doc Output: { schedule: [...], analysis_period_days, recommendation (text) }
      if (response.data && response.data.schedule) {
        this._setCache(cacheKey, response.data);
        return { success: true, data: response.data };
      }
      throw new Error("Invalid data structure from optimized schedule API.");

    } catch (error) {
      console.error("Error fetching AI optimized schedule (service):", error.message, error.originalError);
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        data: this._getCache(cacheKey) || null, // Return cached or null
      };
    }
  }

  // Send a specific recommendation (by its ID) to Core Operations for execution
  async sendRecommendationToCore(recommendationId, options = {}) {
    const { priority = "medium" } = options; // From API doc POST /api/recommendation/{id}/send?priority=high
    
    if (!recommendationId) {
        return { success: false, error: "Recommendation ID is required."};
    }

    try {
      console.log(`Sending recommendation ${recommendationId} to Core Ops via AI Service:`, API_ENDPOINTS.AI.RECOMMENDATION_SEND_TO_CORE(recommendationId));
      const response = await api.post(`${API_ENDPOINTS.AI.RECOMMENDATION_SEND_TO_CORE(recommendationId)}?priority=${priority}`);
      // API Doc Response: { success, message, core_ops_response: { accepted, scheduled_time, estimated_duration } }
      
      if (response.data.success) {
        this._clearCache(this.cacheConfig.recommendationHistory.key); // Refresh history after action
        return { success: true, data: response.data };
      } else {
        return { success: false, error: response.data.message || "Gửi khuyến nghị thất bại." };
      }
    } catch (error) {
      console.error(`Error sending recommendation ${recommendationId} to Core Ops (service):`, error.message, error.originalError);
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
      };
    }
  }

  // Placeholder for applying an optimized schedule.
  // This would involve taking the schedule from getOptimizedSchedule()
  // and then making multiple calls to Core Ops's POST /control/schedules or PUT /control/schedules/{id}
  async applyOptimizedScheduleToCore(optimizedScheduleData) {
      console.warn("applyOptimizedScheduleToCore is a complex operation and currently a placeholder.");
      // Logic:
      // 1. Potentially delete or deactivate existing Core Ops schedules.
      // 2. Iterate through optimizedScheduleData.schedule.
      // 3. For each day and time slot, create a new schedule object for Core Ops API.
      //    Core Ops POST /control/schedules expects: { name, days (array), start_time (HH:MM), duration (seconds), active, description }
      //    AI Output is: { day (string), schedule: [{ time (HH:MM), duration_minutes, effectiveness }] }
      // 4. Call schedulingService.createSchedule (from Core Ops integration) for each.
      // This would need to import `schedulingService.js` (for Core Ops schedule CRUD).
      
      // Example transformation (conceptual):
      // for (const dayData of optimizedScheduleData.schedule) {
      //   const dayName = dayData.day; // e.g., "monday"
      //   for (const slot of dayData.schedule) {
      //     const coreOpsPayload = {
      //       name: `AI Optimized - ${dayName} ${slot.time}`,
      //       days: [dayName],
      //       start_time: slot.time,
      //       duration: slot.duration_minutes * 60, // convert to seconds
      //       active: true,
      //       description: `AI Optimized schedule. Effectiveness: ${slot.effectiveness?.toFixed(2) || 'N/A'}`
      //     };
      //     // await coreOpsSchedulingService.createSchedule(coreOpsPayload);
      //   }
      // }
      return { success: false, message: "Chức năng áp dụng lịch tối ưu chưa được triển khai đầy đủ."};
  }

  // Any other methods like gathering context, processing responses if needed, analytics...
  // can be added or refined here based on what AI service expects vs provides.
  // For now, it focuses on calling the documented APIs.
}

const aiRecommendationsService = new AIRecommendationsService();
export default aiRecommendationsService;