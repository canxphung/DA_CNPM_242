// src/utils/deviceControlService.js
import api from "./api"; // Đã được cập nhật
import { API_ENDPOINTS, ERROR_MESSAGES } from "./constants";

class DeviceControlService {
  constructor() {
    this.deviceCache = new Map();
    this.lastStatusUpdate = new Map();
    this.operationHistory = [];
    this.statusSubscribers = new Set();

    // Safety limits (có thể lấy từ GET /system/config nếu động)
    this.safetyLimits = {
      pump: {
        maxRuntime: 1800, // seconds, from config: irrigation.pump.max_runtime
        minInterval: 3600, // seconds, from config: irrigation.pump.min_interval
        // maxDailyRuntime: 14400 // Not directly in API docs, can be app logic
      },
    };
  }

  // Helper to update cache and notify
  _updateCacheAndNotify(key, data, deviceNameForEvent) {
    this.deviceCache.set(key, data);
    this.lastStatusUpdate.set(key, Date.now());
    if (deviceNameForEvent) {
        this.notifyStatusSubscribers(deviceNameForEvent, data);
    }
  }

  async getIrrigationStatus() {
    const cacheKey = 'irrigation_status_full';
    // Consider a short TTL for this full status if frequently polled
    // if (this.isCacheValid(cacheKey, 60000)) return this.deviceCache.get(cacheKey);

    try {
      console.log("Fetching irrigation status from Core Ops:", API_ENDPOINTS.CORE_OPERATIONS.CONTROL.STATUS);
      const response = await api.get(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.STATUS);
      const coreStatus = response.data; // Direct data object from API

      // Enhance status directly from what API provides
      const enhancedStatus = {
        timestamp: coreStatus.timestamp,
        pump: {
          ...coreStatus.pump,
          // Backend now provides `efficiency` and `nextAllowedStart` hopefully based on safety checks there.
          // If not, these calculations can be re-added here or done in consuming component.
          // For now, assume backend gives comprehensive data if design is to be "intelligent"
          // efficiency: this.calculatePumpEfficiency(coreStatus.pump), // Example: remove if backend provides
          // nextAllowedStart: this.calculateNextAllowedStart(coreStatus.pump, this.safetyLimits.pump.minInterval),
          recommendedAction: this.getRecommendedPumpAction(coreStatus.pump, this.safetyLimits.pump.minInterval), // UI helper
        },
        scheduler: {
          ...coreStatus.scheduler,
          // `nextScheduledEvent` and `conflictingSchedules` can be calculated in frontend or if backend gives it
          // The API response shows `schedules` array. Let's assume frontend component will process this for display
        },
        autoIrrigation: { // Naming based on component state needs to match 'auto_irrigation' from API
          ...coreStatus.auto_irrigation,
          // effectiveness/suggestions may come from AI Service or specific analytics calls rather than base status
        },
        light: {
          is_on: false,
          status: 'unavailable',
          message: 'Light control API not available'
        },
        systemHealth: this.assessSystemHealth(coreStatus), // Still useful to have client-side summary
        alerts: this.generateSystemAlerts(coreStatus),     // Client-side interpretation for UI
      };
      
      this._updateCacheAndNotify(cacheKey, enhancedStatus, 'irrigation_system');
      return { success: true, data: enhancedStatus };

    } catch (error) {
      console.error("Error fetching irrigation status (service):", error.message, error.originalError);
      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        cachedData: this.deviceCache.get(cacheKey)
      };
    }
  }

  // --- PUMP CONTROL ---
  async controlPump(action, options = {}) { // action: 'on' or 'off'
    const { duration, reason = 'manual_control' } = options;
    const endpointAction = action === 'on' ? 'on' : 'off'; // Map to 'on' or 'off' for endpoint

    try {
      // Safety checks should ideally be done by backend based on its current state and config.
      // Frontend can show warnings based on safetyLimits if needed.
      // If API fails due to safety, it should return a specific error.
      let queryParams = "";
      if (action === 'on' && duration) {
        queryParams = `?duration=${duration}`;
      }
      
      console.log(`Controlling pump: ${action}, duration: ${duration}s, via Core Ops: ${API_ENDPOINTS.CORE_OPERATIONS.CONTROL.PUMP_ACTION(endpointAction)}${queryParams}`);
      const response = await api.post(`${API_ENDPOINTS.CORE_OPERATIONS.CONTROL.PUMP_ACTION(endpointAction)}${queryParams}`);
      // API doc for ON: { success, message, start_time, scheduled_stop_time, duration }
      // API doc for OFF: { success, message, run_duration, water_used, stop_time }
      // API doc for failure: { success: false, message, details: { can_start, reason, time_remaining } }
      
      this.recordOperation('pump', action, { success: response.data.success, response: response.data, reason });
      
      if (response.data.success) {
        setTimeout(() => this.getIrrigationStatus(), 1000); // Refresh status
        return { success: true, data: response.data };
      } else {
        // Backend returned success:false (e.g. safety constraint)
        return { 
            success: false, 
            error: response.data.message || "Điều khiển bơm không thành công",
            details: response.data.details 
        };
      }

    } catch (error) {
      console.error(`Error controlling pump (${action}) (service):`, error.message, error.originalError);
      this.recordOperation('pump', action, { success: false, error: error.message, reason });
      return { 
        success: false, 
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        // recovery: this.generateRecoveryOptions('pump', action, error)
      };
    }
  }
  
  async getPumpStatus() {
    try {
      console.log("Fetching pump status from Core Ops:", API_ENDPOINTS.CORE_OPERATIONS.CONTROL.PUMP_STATUS);
      const response = await api.get(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.PUMP_STATUS);
      // API Doc: returns detailed pump status object
      this._updateCacheAndNotify('pump_status_detail', response.data, 'pump');
      return { success: true, data: response.data };
    } catch (error) {
      console.error("Error fetching pump status (service):", error.message, error.originalError);
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR, cachedData: this.deviceCache.get('pump_status_detail') };
    }
  }

  // --- LIGHT CONTROL (ASSUMED ENDPOINTS - NEED VERIFICATION) ---
  async controlLight(action, options = {}) { // action: 'on' or 'off'
    const { intensity, reason = 'manual_control' } = options;
    // !! Placeholder: Update with actual light control endpoints from API_ENDPOINTS.CORE_OPERATIONS.
    const LIGHT_ON_ENDPOINT = API_ENDPOINTS.CORE_OPERATIONS.TURN_ON_LIGHT_WITH_VALUE; // e.g., "/control/light/on"
    const LIGHT_OFF_ENDPOINT = API_ENDPOINTS.CORE_OPERATIONS.CONTROL.LIGHT_ACTION?.('off'); // e.g., "/control/light/off"
                                                                                          // We need a new const for light action path.

    if (!LIGHT_ON_ENDPOINT || !LIGHT_OFF_ENDPOINT) {
        const msg = "API endpoints cho điều khiển đèn chưa được định nghĩa trong constants.js";
        console.error(msg);
        return { success: false, error: msg };
    }

    try {
      let response;
      let apiPath = "";
      if (action === 'on') {
        apiPath = LIGHT_ON_ENDPOINT;
        const payload = intensity ? { value: intensity / 100 } : { value: 1 }; // Assuming API takes 0-1 for value
        // The API doc does not specify POST /control/light/on or body format
        // This assumes it's POST and takes a body like pump value.
        console.log(`Turning light ON, intensity: ${intensity}%, via Core Ops: ${apiPath}`);
        response = await api.post(apiPath, payload); // Send intensity in body
      } else {
        apiPath = LIGHT_OFF_ENDPOINT;
        // Assume turnOffLight sends value 0 or a specific OFF command
        console.log(`Turning light OFF via Core Ops: ${apiPath}`);
        response = await api.post(apiPath, { value: 0 }); // Assuming off is value 0
      }
      this.recordOperation('light', action, { success: response.data.success, response: response.data, reason });
      if (response.data.success !== false) { // Check for not explicitly false, as some APIs might not return 'success' on 200 OK
        setTimeout(() => this.getIrrigationStatus(), 1000); // Or a specific getLightStatus
        return { success: true, data: response.data };
      } else {
        return { success: false, error: response.data.message || "Điều khiển đèn thất bại"};
      }
    } catch (error) {
      console.error(`Error controlling light (${action}) (service):`, error.message, error.originalError);
      this.recordOperation('light', action, { success: false, error: error.message, reason });
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR };
    }
  }
  async getLightStatus() { // Placeholder if there is a specific status for light
    const LIGHT_STATUS_ENDPOINT = API_ENDPOINTS.CORE_OPERATIONS.CONTROL.LIGHT_STATUS; // Needs to be defined
    if (!LIGHT_STATUS_ENDPOINT) {
      console.warn("Light status endpoint not defined. Falling back to sensor snapshot for light data.");
      // As a fallback, you can pull light data from general sensor snapshot
      try {
        const snapshot = await api.get(API_ENDPOINTS.CORE_OPERATIONS.SENSORS.SNAPSHOT);
        if (snapshot.data && snapshot.data.sensors && snapshot.data.sensors.light) {
          const lightSensor = snapshot.data.sensors.light;
          const lightData = {
              is_on: lightSensor.value > 0, // Basic assumption
              intensity_percent: Math.round(lightSensor.value / (snapshot.data.analysis?.light?.result?.expected_range?.[1] || 10000) * 100), // Crude percent
              value: lightSensor.value,
              unit: lightSensor.unit,
              status: lightSensor.status
          };
          this._updateCacheAndNotify('light_status_detail', lightData, 'light');
          return { success: true, data: lightData };
        }
      } catch (e) { /* fallback failed */ }
      return {success: false, error: "Không thể lấy trạng thái đèn."}
    }
    // ... implementation using LIGHT_STATUS_ENDPOINT ...
    return { success: false, error: "Chức năng lấy trạng thái đèn chưa được cài đặt."};
  }

  // --- DEVICE CONFIGURATION ---
  async getSystemConfiguration(path = null) {
    try {
      const url = path 
        ? `${API_ENDPOINTS.CORE_OPERATIONS.SYSTEM_CONFIG}?path=${path}`
        : API_ENDPOINTS.CORE_OPERATIONS.SYSTEM_CONFIG;
      console.log("Fetching system config from Core Ops:", url);
      const response = await api.get(url);
      // API Doc: Full config or { path, value }
      return { success: true, data: response.data };
    } catch (error) {
      console.error("Error fetching system config (service):", error.message, error.originalError);
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR };
    }
  }

  async updateSystemConfiguration(path, value) {
    try {
      console.log(`Updating system config at path: ${path} with value: ${value} via Core Ops:`, API_ENDPOINTS.CORE_OPERATIONS.SYSTEM_CONFIG);
      const response = await api.put(API_ENDPOINTS.CORE_OPERATIONS.SYSTEM_CONFIG, { path, value });
      // API Doc: { success, message, path, value } or { success: false, message, error_code }
      if (response.data.success) {
        return { success: true, data: response.data };
      } else {
        return { success: false, error: response.data.message || "Cập nhật cấu hình thất bại", details: response.data };
      }
    } catch (error) {
      console.error("Error updating system config (service):", error.message, error.originalError);
      return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR };
    }
  }
  
  // Get config for auto-irrigation specific settings
  async getAutoIrrigationConfig() {
    try {
        console.log("Fetching auto-irrigation config from Core Ops:", API_ENDPOINTS.CORE_OPERATIONS.CONTROL.AUTO_IRRIGATION_CONFIG);
        const response = await api.get(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.AUTO_IRRIGATION_CONFIG);
        // API Doc: { enabled, min_decision_interval_seconds, moisture_thresholds, watering_durations }
        return { success: true, data: response.data };
    } catch (error) {
        console.error("Error fetching auto-irrigation config (service):", error.message, error.originalError);
        return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR };
    }
  }
  // Update auto-irrigation config
  async updateAutoIrrigationConfig(configData) {
      try {
          console.log("Updating auto-irrigation config via Core Ops:", API_ENDPOINTS.CORE_OPERATIONS.CONTROL.AUTO_IRRIGATION_CONFIG, configData);
          const response = await api.put(API_ENDPOINTS.CORE_OPERATIONS.CONTROL.AUTO_IRRIGATION_CONFIG, configData);
          // API Doc: { success, message, config: { ... } }
          if (response.data.success !== false) { // Check for not explicitly false
              return { success: true, data: response.data };
          } else {
              return { success: false, error: response.data.message || "Cập nhật cấu hình tưới tự động thất bại", details: response.data };
          }
      } catch (error) {
          console.error("Error updating auto-irrigation config (service):", error.message, error.originalError);
          return { success: false, error: error.message || ERROR_MESSAGES.SERVER_ERROR };
      }
  }

  async setDeviceMode(deviceType, mode) { // mode: 'auto' or 'manual'
    // For Pump: 'auto' means auto_irrigation.enabled = true
    // For Light: Need specific API or config path.
    let apiResult;
    if (deviceType === 'pump') {
      const action = mode === 'auto' ? 'enable' : 'disable';
      // Using Core Ops POST /control/auto/{action} endpoint
      const endpoint = API_ENDPOINTS.CORE_OPERATIONS.CONTROL.AUTO_IRRIGATION_ACTION(action);
      if (!endpoint) return { success: false, error: "Endpoint điều khiển chế độ bơm không xác định." };
      console.log(`Setting pump mode to ${mode} via ${endpoint}`);
      apiResult = await api.post(endpoint); // This endpoint may not exist as per doc; alt: PUT /control/auto with {"enabled": true/false}
      // Assuming `PUT /control/auto` with `{"enabled": (mode === 'auto')}` is the way
      // const autoConfig = await this.getAutoIrrigationConfig();
      // if(autoConfig.success){
      //   apiResult = await this.updateAutoIrrigationConfig({ ...autoConfig.data, enabled: (mode === 'auto') });
      // } else {
      //   return {success: false, error: "Không thể lấy cấu hình tưới tự động hiện tại."}
      // }

    } else if (deviceType === 'light') {
      // !! Placeholder: Need API to set light mode
      // Example: await this.updateSystemConfiguration(`sensors.light.auto_mode.enabled`, mode === 'auto');
      return { success: false, error: `Chức năng đặt chế độ cho ${deviceType} chưa được hỗ trợ.`};
    } else {
      return { success: false, error: `Loại thiết bị không xác định: ${deviceType}`};
    }
    // Check apiResult (assuming it follows standard {success, data/message})
    if (apiResult.data?.success !== false && !apiResult.error) {
         setTimeout(() => this.getIrrigationStatus(), 500); // Refresh overall status
         return { success: true, message: `Chế độ ${deviceType} đã được đặt thành ${mode}.` };
    } else {
         return { success: false, error: apiResult.error || apiResult.data?.message || `Không thể đặt chế độ ${deviceType}.` };
    }
  }


  // --- HELPERS --- (some were in main component, can be here or stay in component for UI formatting)
  calculatePumpEfficiency(pumpStatus) { /* ... as before or if backend provides ... */ return pumpStatus.efficiency || {efficiency: 0, unit: 'N/A'} }
  
  getRecommendedPumpAction(pumpStatus, minIntervalSeconds) {
    if (pumpStatus.is_on) return { action: 'monitor', message: 'Bơm đang chạy, theo dõi hoàn thành.', priority: 'low' };
    
    if (pumpStatus.last_off_time) {
        const timeSinceLastOffMs = Date.now() - new Date(pumpStatus.last_off_time).getTime();
        if (timeSinceLastOffMs < minIntervalSeconds * 1000) {
            const waitMinutes = Math.ceil((minIntervalSeconds * 1000 - timeSinceLastOffMs) / 60000);
            return { action: 'wait', message: `Chờ ${waitMinutes} phút trước lần chạy kế tiếp.`, priority: 'medium' };
        }
    }
    // Check for backend's nextAllowedStart info if available from /control/status
    if(pumpStatus.nextAllowedStart?.minutesRemaining > 0) {
        return { action: 'wait', message: `Chờ ${pumpStatus.nextAllowedStart.minutesRemaining} phút (theo hệ thống).`, priority: 'medium' };
    }

    return { action: 'ready', message: 'Bơm sẵn sàng hoạt động.', priority: 'low' };
  }

  assessSystemHealth(coreStatus) {
    // This is a simplified version based on available fields in Core Ops /control/status
    let score = 100;
    const factors = [];

    if (coreStatus.pump) {
        if (!coreStatus.pump.state_synced) {
            score -= 30;
            factors.push({ component: 'Bơm', status: 'warning', message: 'Trạng thái bơm không đồng bộ với Adafruit IO.' });
        } else {
            factors.push({ component: 'Bơm', status: 'healthy', message: 'Đồng bộ.' });
        }
    } else {
        score -= 40; factors.push({ component: 'Bơm', status: 'critical', message: 'Không có thông tin bơm.' });
    }

    if (coreStatus.scheduler) {
        if (!coreStatus.scheduler.active) {
            score -= 20;
            factors.push({ component: 'Lập lịch', status: 'warning', message: 'Bộ lập lịch không hoạt động.' });
        } else {
            factors.push({ component: 'Lập lịch', status: 'healthy', message: 'Đang hoạt động.' });
        }
         if(coreStatus.scheduler.schedules_count === 0 && coreStatus.scheduler.active){
             factors.push({ component: 'Lập lịch', status: 'info', message: 'Bộ lập lịch hoạt động nhưng không có lịch nào.' });
         }
    } else {
         score -= 30; factors.push({ component: 'Lập lịch', status: 'warning', message: 'Không có thông tin lịch trình.' });
    }

    if (coreStatus.auto_irrigation) {
        if (!coreStatus.auto_irrigation.enabled) {
            factors.push({ component: 'Tưới tự động', status: 'info', message: 'Đang tắt. Cân nhắc bật nếu cần.' });
        } else if (!coreStatus.auto_irrigation.active) { // Enabled but not active (e.g. conditions not met)
            score -= 10;
            factors.push({ component: 'Tưới tự động', status: 'warning', message: 'Đã bật nhưng không hoạt động (có thể do điều kiện không phù hợp).' });
        } else {
            factors.push({ component: 'Tưới tự động', status: 'healthy', message: 'Đang hoạt động.' });
        }
    } else {
        factors.push({ component: 'Tưới tự động', status: 'info', message: 'Thông tin tưới tự động không khả dụng.' });
    }
    
    score = Math.max(0, Math.min(100, score));
    let statusStr = 'healthy';
    if (score < 50) statusStr = 'critical';
    else if (score < 80) statusStr = 'warning';

    return { score, status: statusStr, factors };
  }

  generateSystemAlerts(coreStatus) { /* ... as before ... */ 
    const alerts = [];
    if (coreStatus.pump && !coreStatus.pump.state_synced) {
      alerts.push({type: 'warning', component: 'Bơm', message: 'Trạng thái bơm không đồng bộ.', action: 'Kiểm tra kết nối Adafruit IO.'});
    }
    if (coreStatus.scheduler && !coreStatus.scheduler.active) {
      alerts.push({type: 'info', component: 'Lập lịch', message: 'Bộ lập lịch tưới đang tắt.', action: 'Bật nếu cần tưới tự động theo lịch.'});
    }
    if(coreStatus.auto_irrigation && coreStatus.auto_irrigation.enabled && !coreStatus.auto_irrigation.active){
        alerts.push({type: 'info', component: 'Tưới tự động', message: 'Chế độ tự động đã bật nhưng hiện không hoạt động.', action: 'Kiểm tra điều kiện môi trường hoặc cấu hình ngưỡng.'});
    }
    // Add more alerts based on structure from /control/status (e.g., system health check section if present)
    return alerts;
  }
  
  recordOperation(device, action, details) { /* ... as before ... */ 
      this.operationHistory.push({device, action, timestamp: new Date().toISOString(), ...details});
      if (this.operationHistory.length > 50) this.operationHistory.shift();
  }
  // isCacheValid, notifyStatusSubscribers, subscribeToStatusUpdates, getPerformanceMetrics: Keep as before

  getSafetyLimits(){ // Can be fetched from config if dynamic
      return this.safetyLimits;
  }
}

const deviceControlService = new DeviceControlService();
export default deviceControlService;