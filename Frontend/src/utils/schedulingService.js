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
  // utils/schedulingService.js

// ... (code khác) ...

  async getIrrigationHistory(options = {}) {
    const { days = 7, forceRefresh = false } = options; // forceRefresh chưa được dùng, có thể thêm logic cache sau

    try {
      console.log("Fetching irrigation history from Core Ops:", API_ENDPOINTS.CORE_OPERATIONS.CONTROL.HISTORY, { params: { days } });
      const response = await api.get(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.HISTORY, {
        params: { days }
      });
      console.log("Irrigation History API Response Data:", response.data);

      // KIỂM TRA CẤU TRÚC response.data VÀ TRUY CẬP ĐÚNG MẢNG
      // Ví dụ: Nếu bạn muốn map qua mảng "irrigation_events"
      let rawHistoryArray = [];
      if (response.data && Array.isArray(response.data.irrigation_events)) {
          rawHistoryArray = response.data.irrigation_events;
      } else if (response.data && Array.isArray(response.data.auto_decisions)) {
          // Hoặc nếu bạn muốn dùng auto_decisions, hoặc kết hợp cả hai
          // rawHistoryArray = response.data.auto_decisions;
          console.warn("Using 'auto_decisions' for history. Verify if this is intended.");
      } else if (Array.isArray(response.data)) {
          // Trường hợp không thể xảy ra dựa trên backend code hiện tại, nhưng để phòng hờ
          rawHistoryArray = response.data;
          console.warn("API response.data for history is an array directly, which is unexpected based on backend code.");
      } else {
        console.error("Error fetching irrigation history: response.data is not in expected format or relevant array is missing.", response.data);
        return { success: false, error: "Dữ liệu lịch sử không đúng định dạng.", data: [] };
      }

      // Bây giờ map trên rawHistoryArray
      const historyData = rawHistoryArray.map(item => {
        // Cần điều chỉnh item access dựa trên cấu trúc thực tế của các object trong mảng pump_history hoặc decision_history
        // Ví dụ, nếu `item` từ `pump_history` có cấu trúc:
        // { id, timestamp, duration_seconds, source, details: { schedule_name }, status }
        // Và bạn muốn nó khớp với cấu trúc frontend:
        // { id, title, date, time, moisture, temperature, duration_minutes, status }

        let title = 'Hoạt động tưới'; // Tiêu đề mặc định
        if (item.source === 'schedule' && item.details && item.details.schedule_name) {
          title = `Lịch: ${item.details.schedule_name}`;
        } else if (item.source === 'auto' && item.details && item.details.reason) {
          title = `Tự động: ${item.details.reason.substring(0,30)}...`;
        } else if (item.source === 'manual') {
          title = 'Tưới thủ công';
        } else if (item.description) { // Nếu từ auto_decisions có description
          title = item.description;
        }


        // Duration từ pump_history (duration_seconds) hoặc decision_history (có thể không có duration trực tiếp)
        let durationMinutes = 'N/A';
        if (typeof item.duration_seconds === 'number') {
          durationMinutes = Math.round(item.duration_seconds / 60);
        } else if (typeof item.duration_minutes === 'number') { // Nếu nó đã có sẵn
            durationMinutes = item.duration_minutes;
        }
        // Logic tương tự cho các trường khác như soil_moisture_improvement, status từ item
        // Dựa trên cấu trúc thực tế của item từ pump_history hoặc decision_history
        
        return {
          id: item.id, // id của bản ghi lịch sử
          title: title,
          date: new Date(item.timestamp).toLocaleDateString("vi-VN"),
          time: new Date(item.timestamp).toLocaleTimeString("vi-VN"),
          moisture: item.soil_moisture_improvement || "N/A", // Cần kiểm tra nguồn gốc trường này
          temperature: "N/A", // Hiện không có trong data từ manager
          duration_minutes: durationMinutes,
          status: item.status || 'completed' // 'completed', 'failed', 'pending' (tùy thuộc backend)
        };
      });

      return { success: true, data: historyData };
    } catch (error) {
      console.error("Error fetching irrigation history (service):", error.message, error.originalError || error);
      // Trả về cached data (nếu có) hoặc mảng rỗng khi lỗi
      // const cached = this._getCache(cacheKeyForHistory); // Cần định nghĩa cacheKeyForHistory
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        data: [] // Hoặc cached || []
      };
    }
  }
}

const schedulingService = new SchedulingService();
export default schedulingService;