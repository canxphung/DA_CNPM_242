// utils/schedulingService.js
import api from "./api";
import { API_ENDPOINTS, ERROR_MESSAGES } from "./constants";

class SchedulingService {
  constructor() {
    // Cache cho danh sách lịch trình
    this.scheduleCache = new Map();
    this.cacheConfig = {
      schedulesList: { ttl: 60000, key: 'schedules_list_core' }, // 1 minute cache for active schedules
      // executionHistory: { ttl: 300000, key: 'irrigation_execution_history_core' } // If we get an API for this
    };
  }

  _isCacheValid(key, ttl) {
    const cached = this.scheduleCache.get(key);
    if (!cached) return false;
    const age = Date.now() - (cached.timestamp || 0);
    return age < ttl;
  }

  _setCache(key, data) {
    this.scheduleCache.set(key, { data, timestamp: Date.now() });
  }

  _getCache(key) {
    return this.scheduleCache.get(key)?.data || null;
  }

  _clearCache(keyPrefix = 'schedules_') {
      for (const key of this.scheduleCache.keys()) {
        if (key.startsWith(keyPrefix)) {
          this.scheduleCache.delete(key);
        }
      }
      console.log(`Cache for prefix '${keyPrefix}' cleared.`);
  }

  async getSchedules(forceRefresh = false) {
    const cacheKey = this.cacheConfig.schedulesList.key;
    if (!forceRefresh && this._isCacheValid(cacheKey, this.cacheConfig.schedulesList.ttl)) {
      console.log('Using cached schedules (Core Ops)');
      return { success: true, data: this._getCache(cacheKey) };
    }

    try {
      console.log("Fetching schedules from Core Ops:", API_ENDPOINTS.CORE_OPERATIONS.CONTROL.SCHEDULES_BASE);
      const response = await api.get(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.SCHEDULES_BASE);
      // API Response: {"schedules": [{id, name, days, start_time, duration, active, description, created_at, updated_at}], "count": X}
      const schedulesData = response.data.schedules || [];
      this._setCache(cacheKey, schedulesData);
      return { success: true, data: schedulesData };
    } catch (error) {
      console.error("Error fetching schedules (service):", error.message, error.originalError);
      const cached = this._getCache(cacheKey);
      return { 
        success: false, 
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        data: cached || [] // Return cached data on error if available
      };
    }
  }

  async createSchedule(schedulePayload) {
    // schedulePayload: { name, days, start_time, duration, active, description }
    try {
      console.log("Creating schedule via Core Ops:", API_ENDPOINTS.CORE_OPERATIONS.CONTROL.SCHEDULES_BASE, schedulePayload);
      const response = await api.post(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.SCHEDULES_BASE, schedulePayload);
      // API Response: {"success": true, "message": "...", "schedule": {new_schedule_object}}
      if (response.data.success || response.data.schedule) { // Backend might not always send 'success' boolean if using HTTP status for success
        this._clearCache(); // Clear cache as list has changed
        return { success: true, data: response.data.schedule, message: response.data.message };
      } else {
        return { success: false, error: response.data.message || "Không thể tạo lịch trình." };
      }
    } catch (error) {
      console.error("Error creating schedule (service):", error.message, error.originalError);
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR };
    }
  }

  async updateSchedule(scheduleId, updatePayload) {
    // updatePayload: { name?, days?, start_time?, duration?, active?, description? }
    try {
      console.log(`Updating schedule ${scheduleId} via Core Ops:`, API_ENDPOINTS.CORE_OPERATIONS.CONTROL.SCHEDULE_BY_ID(scheduleId), updatePayload);
      const response = await api.put(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.SCHEDULE_BY_ID(scheduleId), updatePayload);
      // API Response: {"success": true, "message": "...", "schedule": {updated_schedule_object}}
      if (response.data.success || response.data.schedule) {
        this._clearCache();
        return { success: true, data: response.data.schedule, message: response.data.message };
      } else {
        return { success: false, error: response.data.message || "Không thể cập nhật lịch trình." };
      }
    } catch (error) {
      console.error("Error updating schedule (service):", error.message, error.originalError);
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR };
    }
  }

  async deleteSchedule(scheduleId) {
    try {
      console.log(`Deleting schedule ${scheduleId} via Core Ops:`, API_ENDPOINTS.CORE_OPERATIONS.CONTROL.SCHEDULE_BY_ID(scheduleId));
      const response = await api.delete(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.SCHEDULE_BY_ID(scheduleId));
      // API Response: {"success": true, "message": "...", "deleted_schedule": {old_schedule_object}}
      if (response.data.success || response.status === HTTP_STATUS.NO_CONTENT || response.status === HTTP_STATUS.OK ) { // DELETE might return 204
        this._clearCache();
        return { success: true, message: response.data.message || "Xóa lịch trình thành công." };
      } else {
        return { success: false, error: response.data.message || "Không thể xóa lịch trình." };
      }
    } catch (error) {
      console.error("Error deleting schedule (service):", error.message, error.originalError);
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR };
    }
  }

  // --- IRRIGATION EXECUTION HISTORY ---
  // THIS IS A PLACEHOLDER - Actual implementation depends on backend API
  async getIrrigationHistory(options = {}) {
    const { days = 7, forceRefresh = false } = options;
    
    try {
      // Sử dụng Core Ops control/history endpoint
      const response = await api.get(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.HISTORY, {
        params: { days } // Cần xác nhận query params
      });
      
      // Transform data to match ScheduleContext expectations
      const historyData = response.data.map(item => ({
        id: item.id,
        title: item.description || 'Tưới tự động',
        date: new Date(item.timestamp).toLocaleDateString("vi-VN"),
        time: new Date(item.timestamp).toLocaleTimeString("vi-VN"),
        moisture: item.soil_moisture_improvement || "N/A",
        temperature: "N/A",
        duration_minutes: item.duration_minutes || Math.round(item.duration_seconds / 60),
        status: item.status || 'completed'
      }));
      
      return { success: true, data: historyData };
    } catch (error) {
      console.error("Error fetching irrigation history:", error);
      return { success: false, error: error.message, data: [] };
    }
  }
}

const schedulingService = new SchedulingService();
export default schedulingService;