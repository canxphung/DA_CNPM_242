// // src/utils/sensorService.js
// import api from "./api"; // api.js đã được cập nhật
// import { API_ENDPOINTS, ERROR_MESSAGES } from "./constants";

// class SensorService {
//   constructor() {
//     this.cache = new Map();
//     this.lastFetchTimes = new Map();
//     this.subscribers = new Set();
//     this.cacheConfig = {
//       current: { ttl: 30000, key: 'current_sensors_snapshot' }, // Dùng snapshot
//       history: { ttl: 300000, key: 'history_sensors_v2' }, // Key mới
//       analysis: { ttl: 60000, key: 'analysis_sensors_v2' }  // Key mới
//     };
//   }

//   isCacheValid(cacheKey, ttl) {
//     const lastFetch = this.lastFetchTimes.get(cacheKey);
//     return lastFetch && (Date.now() - lastFetch) < ttl;
//   }

//   setCache(cacheKey, data) {
//     this.cache.set(cacheKey, data);
//     this.lastFetchTimes.set(cacheKey, Date.now());
//   }

//   getCache(cacheKey) {
//     return this.cache.get(cacheKey) || null;
//   }

//   // Process data from Core Ops GET /sensors/snapshot
//   processSnapshotData(snapshotData) {
//     const { sensors, analysis, irrigation_recommendation, status: overall_status, timestamp } = snapshotData;
    
//     const processedSensors = {};
//     // Core Ops snapshot returns keys like "light", "temperature", "humidity", "soil_moisture"
//     // Frontend components might expect: "light", "temperature", "moisture" (for air humidity), "soil" (for soil moisture)
    
//     if (sensors) {
//       if (sensors.light) processedSensors.light = { ...sensors.light, feedId: `feed_light_${sensors.light.timestamp}` };
//       if (sensors.temperature) processedSensors.temperature = { ...sensors.temperature, feedId: `feed_temperature_${sensors.temperature.timestamp}` };
//       if (sensors.humidity) processedSensors.moisture = { ...sensors.humidity, sensor_type: "humidity", feedId: `feed_humidity_${sensors.humidity.timestamp}` }; // Map humidity to moisture for consistency with useSensorData
//       if (sensors.soil_moisture) processedSensors.soil = { ...sensors.soil_moisture, sensor_type: "soil_moisture", feedId: `feed_soil_${sensors.soil_moisture.timestamp}` };
//     }
    
//     // Enhance analysis data for each sensor
//     const analysisSummary = {};
//     if (analysis) {
//         Object.entries(analysis).forEach(([sensorKey, sensorAnalysis]) => {
//             let targetKey = sensorKey;
//             if (sensorKey === "humidity") targetKey = "moisture";
//             else if (sensorKey === "soil_moisture") targetKey = "soil";
            
//             if(processedSensors[targetKey] && sensorAnalysis?.result) {
//                  processedSensors[targetKey].analysis = sensorAnalysis.result; // Embed specific sensor analysis result
//             }
//             analysisSummary[targetKey] = sensorAnalysis?.result; // Keep overall analysis separated as well
//         });
//     }

//     return {
//       sensors: processedSensors, // Đây là object chứa light, temperature, moisture (cho humidity), soil (cho soil_moisture)
//       overall_status: overall_status || 'unknown',
//       analysis_summary: analysisSummary, // This now contains results keyed by 'light', 'temperature', 'moisture', 'soil'
//       irrigation_recommendation: irrigation_recommendation || null,
//       timestamp: timestamp || new Date().toISOString(),
//       source: 'core_ops_snapshot_api'
//     };
//   }

//   // Process data from Core Ops GET /sensors/collect
//   processCollectData(collectApiData) {
//     const { data: sensorDataCollection, message, success, warnings } = collectApiData;
//     console.log("Processing collect API data:", sensorDataCollection, message, success, warnings);
//     const processedSensors = {};
//     if (sensorDataCollection) {
//         // Mapping from 'collect' structure (already matches "light", "temperature", "humidity", "soil_moisture")
//         if (sensorDataCollection.light) processedSensors.light = sensorDataCollection.light;
//         if (sensorDataCollection.temperature) processedSensors.temperature = sensorDataCollection.temperature;
//         if (sensorDataCollection.humidity) processedSensors.moisture = { ...sensorDataCollection.humidity, sensor_type: "humidity"}; // Map to 'moisture'
//         if (sensorDataCollection.soil_moisture) processedSensors.soil = { ...sensorDataCollection.soil_moisture, sensor_type: "soil_moisture" };
//     }

//     return {
//       sensors: processedSensors,
//       overall_status: success && (!warnings || warnings.length === 0) ? 'normal' : 'warning', // Basic status based on collect success
//       analysis_summary: null, // /collect endpoint doesn't provide analysis
//       irrigation_recommendation: null, // /collect endpoint doesn't provide recommendations
//       timestamp: new Date().toISOString(),
//       source: 'core_ops_collect_api',
//       collect_message: message,
//       collect_warnings: warnings || []
//     };
//   }
  
//   async fetchCurrentSensorData(forceRefresh = false) {
//     const { ttl, key } = this.cacheConfig.current;
//     if (!forceRefresh && this.isCacheValid(key, ttl)) {
//       const cachedData = this.getCache(key);
//       if (cachedData) {
//         console.log('Using cached current sensor data (snapshot)');
//         return cachedData;
//       }
//     }
//     console.log("Fetching current sensor data (v2) from Core Ops...");
//     try {
//       // Ưu tiên SNAPSHOT
//       console.log("Fetching from Core Ops SNAPSHOT:", API_ENDPOINTS.CORE_OPERATIONS.SENSORS.SNAPSHOT);
//       const snapshotResponse = await api.get(API_ENDPOINTS.CORE_OPERATIONS.SENSORS.SNAPSHOT, {
//         params: { collect: true, analyze: true }
//       });
//       console.log("Snapshot response:", snapshotResponse.data);
      
//       if (snapshotResponse.data) { // snapshot returns data directly
//         const processedData = this.processSnapshotData(snapshotResponse.data);
//         this.setCache(key, processedData);
//         this.notifySubscribers(processedData); // For WebSocket (future)
//         return processedData;
//       }
//       throw new Error("Snapshot API returned no data or invalid structure.");

//     } catch (snapshotError) {
//       console.error("Error fetching from Core Ops SNAPSHOT, trying COLLECT:", snapshotError.message, snapshotError.originalError);
//       try {
//         // Fallback là COLLECT
//         console.log("Fetching from Core Ops COLLECT:", API_ENDPOINTS.CORE_OPERATIONS.SENSORS.COLLECT_ALL);
//         const collectResponse = await api.get(API_ENDPOINTS.CORE_OPERATIONS.SENSORS.COLLECT_ALL);
        
//         if (collectResponse.data) { // collect endpoint has a data.data structure or data.success
//             const processedData = this.processCollectData(collectResponse.data);
//             this.setCache(key, processedData);
//             this.notifySubscribers(processedData);
//             return processedData;
//         }
//         throw new Error("Collect API returned no data or invalid structure.");

//       } catch (collectError) {
//         console.error("Error fetching from Core Ops COLLECT as fallback:", collectError.message, collectError.originalError);
//         // Nếu cả hai đều lỗi, trả về default data
//         return this.createDefaultSensorDataOnError(collectError.message || snapshotError.message);
//       }
//     }
//   }

//   // Xử lý dữ liệu lịch sử từ AI service (GIẢ ĐỊNH)
//   // Cần biết cấu trúc response của GET /api/sensors/history từ AI Service
//   processAIHistoricalData(aiHistoryData, requestedSensorTypes) {
//     const chartData = {};
//     const rawData = aiHistoryData.data || aiHistoryData; // Giả sử AI service trả về { data: { sensor_type: [{time, value}] } } hoặc trực tiếp

//     requestedSensorTypes.forEach(sensorType => {
//         let actualSensorType = sensorType;
//         // Map frontend types to potential AI service types
//         if(sensorType === "moisture") actualSensorType = "humidity";
//         if(sensorType === "soil") actualSensorType = "soil_moisture";

//         const historyForSensor = rawData[actualSensorType];
//         if (historyForSensor && Array.isArray(historyForSensor)) {
//             const sortedHistory = historyForSensor.sort((a,b) => new Date(a.timestamp || a.time) - new Date(b.timestamp || b.time));
//             chartData[sensorType] = {
//                 labels: sortedHistory.map(item => new Date(item.timestamp || item.time).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Ho_Chi_Minh' })),
//                 values: sortedHistory.map(item => parseFloat(item.value) || 0)
//             };
//         } else {
//             chartData[sensorType] = { labels: [], values: [] };
//         }
//     });

//     return {
//       chartData, // Object keyed by "temperature", "moisture", "light", "soil"
//       timestamp: aiHistoryData.timestamp || new Date().toISOString(),
//       source: 'ai_service_history_api',
//       period_hours: aiHistoryData.period_hours || 'N/A'
//     };
//   }

//   async fetchHistoricalData(options = {}) {
//     const {
//       hours = 24,
//       sensorTypes = ['temperature', 'moisture', 'light', 'soil'], // Frontend keys
//       forceRefresh = false
//     } = options;

//     const cacheKey = `${this.cacheConfig.history.key}_${hours}_${sensorTypes.join('_')}`;
//     const { ttl } = this.cacheConfig.history;

//     if (!forceRefresh && this.isCacheValid(cacheKey, ttl)) {
//       const cachedData = this.getCache(cacheKey);
//       if (cachedData) {
//         console.log('Using cached historical data (v2)');
//         return cachedData;
//       }
//     }

//     try {
//       // GIẢ ĐỊNH: Dữ liệu lịch sử được lấy từ AI Service
//       // Path trong constants.js là API_ENDPOINTS.AI.SENSORS_HISTORY
//       // API Doc của AI service: GET /api/sensors/history (cần làm rõ params, giả sử `?hours=X`)
//       console.log("Fetching historical data from AI Service:", API_ENDPOINTS.AI.SENSORS_HISTORY);
//       const historyResponse = await api.get(API_ENDPOINTS.AI.SENSORS_HISTORY, {
//           params: { hours } // hoặc là "lastHours" tùy theo API của AI Service
//       });
      
//       if (historyResponse.data) {
//         const processedHistory = this.processAIHistoricalData(historyResponse.data, sensorTypes);
//         this.setCache(cacheKey, processedHistory);
//         return processedHistory;
//       }
//       throw new Error("AI History API returned no data.");

//     } catch (error) {
//       console.error("Error fetching historical data from AI Service:", error.message, error.originalError);
//       // Nếu AI service lỗi, chúng ta không có fallback trực tiếp từ Core Ops cho history trong API docs
//       // Vì vậy, trả về dummy data.
//       return this.createDefaultHistoricalDataOnError(sensorTypes, `Lỗi tải lịch sử từ AI: ${error.message}`);
//     }
//   }


//   async analyzeSensor(sensorType, collectFresh = false) {
//     const cacheKey = `${this.cacheConfig.analysis.key}_${sensorType}`;
//     const { ttl } = this.cacheConfig.analysis;

//     if (!collectFresh && this.isCacheValid(cacheKey, ttl)) {
//       const cachedAnalysis = this.getCache(cacheKey);
//       if (cachedAnalysis) {
//         console.log(`Using cached analysis for ${sensorType} (v2)`);
//         return cachedAnalysis;
//       }
//     }

//     try {
//       // API của Core Ops: GET /sensors/analyze/{sensor_type}?collect=true
//       // Map frontend sensorType to backend if necessary (e.g., "soil" -> "soil_moisture")
//       let backendSensorType = sensorType;
//       if (sensorType === 'soil') backendSensorType = 'soil_moisture';
//       if (sensorType === 'moisture') backendSensorType = 'humidity';


//       console.log("Fetching analysis from Core Ops:", API_ENDPOINTS.CORE_OPERATIONS.SENSORS.ANALYZE_SPECIFIC(backendSensorType));
//       const analysisResponse = await api.get(API_ENDPOINTS.CORE_OPERATIONS.SENSORS.ANALYZE_SPECIFIC(backendSensorType), {
//           params: { collect: collectFresh }
//       });
      
//       // Response: {"sensor_type", "timestamp", "reading":{...}, "analysis":{...}}
//       const rawAnalysis = analysisResponse.data;
//       if (rawAnalysis && rawAnalysis.analysis) {
//           const analysisData = {
//             sensor_type: sensorType, // Original frontend type
//             reading: rawAnalysis.reading,
//             analysis: rawAnalysis.analysis, // This is the detailed analysis part.
//             timestamp: rawAnalysis.timestamp,
//             // recommendations: this.generateRecommendations(rawAnalysis.analysis) // generateRecommendations cần xem xét
//           };
//           this.setCache(cacheKey, analysisData);
//           return analysisData;
//       }
//       throw new Error(`Analysis API for ${sensorType} returned invalid data.`);
      
//     } catch (error) {
//       console.error(`Error analyzing ${sensorType}:`, error.message, error.originalError);
//       return this.createDefaultAnalysisOnError(sensorType, error.message);
//     }
//   }
  
//   // Default data creators adjusted to accept an error message
//   createDefaultSensorDataOnError(errorMessage = "Không thể kết nối đến sensors") {
//     const defaultValue = { value: 0, unit: "", status: "unknown", timestamp: new Date().toISOString(), feedId: "N/A", analysis: null };
//     return {
//       sensors: {
//         temperature: { ...defaultValue, unit: "°C", value: 25 },
//         moisture: { ...defaultValue, unit: "%", value: 50 }, // for air humidity
//         light: { ...defaultValue, unit: "Lux", value: 1000 },
//         soil: { ...defaultValue, unit: "%", value: 40 } // for soil moisture
//       },
//       overall_status: 'error', // Indicate error status
//       error: errorMessage,
//       irrigation_recommendation: null,
//       analysis_summary: null,
//       timestamp: new Date().toISOString(),
//       source: 'default_fallback_error'
//     };
//   }

//   createDefaultHistoricalDataOnError(sensorTypes, errorMessage = "Không thể tải dữ liệu lịch sử") {
//     const chartData = {};
//     sensorTypes.forEach(type => {
//       chartData[type] = { labels: [], values: [] };
//     });
//     return {
//       chartData,
//       timestamp: new Date().toISOString(),
//       source: 'default_history_fallback_error',
//       error: errorMessage
//     };
//   }

//   createDefaultAnalysisOnError(sensorType, errorMessage) {
//     return {
//       sensor_type: sensorType,
//       reading: { value: 0, unit: "", status: "error", timestamp: new Date().toISOString() },
//       analysis: { status: "error", description: "Không thể phân tích", needs_water: false },
//       error: errorMessage,
//       timestamp: new Date().toISOString()
//     };
//   }

//   subscribe(callback) { /* ... (keep existing) ... */ 
//     this.subscribers.add(callback);
//     return () => { this.subscribers.delete(callback); };
//   }
//   notifySubscribers(data) { /* ... (keep existing) ... */ 
//     this.subscribers.forEach(callback => {
//       try { callback(data); } 
//       catch (error) { console.error('Error in sensor data subscriber:', error); }
//     });
//   }
//   clearCache() { /* ... (keep existing) ... */ 
//     this.cache.clear();
//     this.lastFetchTimes.clear();
//     console.log('Sensor service cache cleared (v2)');
//   }
//   getCacheStats() { /* ... (keep existing) ... */ 
//     return {
//       cacheSize: this.cache.size,
//       subscriberCount: this.subscribers.size,
//       cachedKeys: Array.from(this.cache.keys()),
//       lastFetchTimes: Object.fromEntries(this.lastFetchTimes)
//     };
//   }
// }

// const sensorService = new SensorService();

// // Exporting the instance remains the same, but the functions below might not be needed
// // if useSensorData hook directly uses sensorService methods.
// // For now, I'll update them to call the new service methods.

// export const fetchSensorData = (forceRefresh = false) => 
//   sensorService.fetchCurrentSensorData(forceRefresh);

// export const fetchChartData = (options = {}) => 
//   sensorService.fetchHistoricalData(options);

// export const analyzeSensorData = (sensorType, collectFresh = false) =>
//   sensorService.analyzeSensor(sensorType, collectFresh);

// export default sensorService;
// src/utils/sensorService.js
import api from "./api";
import { API_ENDPOINTS, ERROR_MESSAGES } from "./constants";
import { 
  SensorCollectorManager, 
  SensorReading, 
} from './sensorCollectors';
import { 
  SensorType, 
  toBackendKey, 
  toFrontendKey,
  getSensorConfig,
  SensorStatus
} from './sensorTypes';

// import { SensorStatus } from './sensorTypes';

class SensorService {
  constructor() {
    this.collectorManager = new SensorCollectorManager();
    this.cache = new Map();
    this.lastFetchTimes = new Map();
    this.subscribers = new Set();
    this.cacheConfig = {
      current: { ttl: 30000, key: 'current_sensors_snapshot' },
      history: { ttl: 300000, key: 'history_sensors_v2' },
      analysis: { ttl: 60000, key: 'analysis_sensors_v2' }
    };
  }

  isCacheValid(cacheKey, ttl) {
    const lastFetch = this.lastFetchTimes.get(cacheKey);
    return lastFetch && (Date.now() - lastFetch) < ttl;
  }

  setCache(cacheKey, data) {
    this.cache.set(cacheKey, data);
    this.lastFetchTimes.set(cacheKey, Date.now());
  }

  getCache(cacheKey) {
    return this.cache.get(cacheKey) || null;
  }

  /**
   * Xử lý dữ liệu từ Core Ops GET /sensors/snapshot
   */
  processSnapshotData(snapshotData) {
    const { sensors, analysis, irrigation_recommendation, status: overall_status, timestamp } = snapshotData;
    
    const processedSensors = {};
    
    if (sensors) {
      // Xử lý từng loại sensor với collectors
      Object.entries(sensors).forEach(([backendKey, rawData]) => {
        if (!rawData) return;
        
        const frontendKey = toFrontendKey(backendKey);
        const collector = this.collectorManager.getCollector(frontendKey);
        
        if (collector) {
          const reading = collector.processRawData({
            ...rawData,
            feedId: `feed_${frontendKey}_${rawData.timestamp || Date.now()}`
          });
          
          // Cache reading trong collector
          collector.setCachedReading(reading);
          
          processedSensors[frontendKey] = reading.toDict();
        }
      });
    }
    
    // Xử lý analysis data
    const analysisSummary = {};
    if (analysis) {
      Object.entries(analysis).forEach(([backendKey, sensorAnalysis]) => {
        const frontendKey = toFrontendKey(backendKey);
        
        if (processedSensors[frontendKey] && sensorAnalysis?.result) {
          processedSensors[frontendKey].analysis = sensorAnalysis.result;
        }
        analysisSummary[frontendKey] = sensorAnalysis?.result;
      });
    }

    return {
      sensors: processedSensors,
      overall_status: overall_status || 'unknown',
      analysis_summary: analysisSummary,
      irrigation_recommendation: irrigation_recommendation || null,
      timestamp: timestamp || new Date().toISOString(),
      source: 'core_ops_snapshot_api'
    };
  }

  /**
   * Xử lý dữ liệu từ Core Ops GET /sensors/collect
   */
  processCollectData(collectApiData) {
    const { data: sensorDataCollection, message, success, warnings } = collectApiData;
    
    const processedSensors = {};
    
    if (sensorDataCollection) {
      Object.entries(sensorDataCollection).forEach(([backendKey, rawData]) => {
        if (!rawData) return;
        
        const frontendKey = toFrontendKey(backendKey);
        const collector = this.collectorManager.getCollector(frontendKey);
        
        if (collector) {
          const reading = collector.processRawData({
            ...rawData,
            sensor_type: backendKey
          });
          
          collector.setCachedReading(reading);
          processedSensors[frontendKey] = reading.toDict();
        }
      });
    }

    return {
      sensors: processedSensors,
      overall_status: success && (!warnings || warnings.length === 0) ? 'normal' : 'warning',
      analysis_summary: null,
      irrigation_recommendation: null,
      timestamp: new Date().toISOString(),
      source: 'core_ops_collect_api',
      collect_message: message,
      collect_warnings: warnings || []
    };
  }
  
  /**
   * Lấy dữ liệu sensor hiện tại
   */
  async fetchCurrentSensorData(forceRefresh = false) {
    const { ttl, key } = this.cacheConfig.current;
    
    if (!forceRefresh && this.isCacheValid(key, ttl)) {
      const cachedData = this.getCache(key);
      if (cachedData) {
        console.log('Using cached current sensor data (snapshot)');
        return cachedData;
      }
    }

    console.log("Fetching current sensor data from Core Ops...");
    
    try {
      // Ưu tiên SNAPSHOT
      console.log("Fetching from Core Ops SNAPSHOT:", API_ENDPOINTS.CORE_OPERATIONS.SENSORS.SNAPSHOT);
      const snapshotResponse = await api.get(API_ENDPOINTS.CORE_OPERATIONS.SENSORS.SNAPSHOT, {
        params: { collect: true, analyze: true }
      });
      
      if (snapshotResponse.data) {
        const processedData = this.processSnapshotData(snapshotResponse.data);
        this.setCache(key, processedData);
        this.notifySubscribers(processedData);
        return processedData;
      }
      
      throw new Error("Snapshot API returned no data or invalid structure.");

    } catch (snapshotError) {
      console.error("Error fetching from Core Ops SNAPSHOT, trying COLLECT:", snapshotError.message);
      
      try {
        // Fallback COLLECT
        console.log("Fetching from Core Ops COLLECT:", API_ENDPOINTS.CORE_OPERATIONS.SENSORS.COLLECT_ALL);
        const collectResponse = await api.get(API_ENDPOINTS.CORE_OPERATIONS.SENSORS.COLLECT_ALL);
        
        if (collectResponse.data) {
          const processedData = this.processCollectData(collectResponse.data);
          this.setCache(key, processedData);
          this.notifySubscribers(processedData);
          return processedData;
        }
        
        throw new Error("Collect API returned no data or invalid structure.");

      } catch (collectError) {
        console.error("Error fetching from Core Ops COLLECT as fallback:", collectError.message);
        return this.createDefaultSensorDataOnError(collectError.message || snapshotError.message);
      }
    }
  }

  /**
   * Xử lý dữ liệu lịch sử từ AI service
   */
  processAIHistoricalData(aiHistoryData, requestedSensorTypes) {
    const chartData = {};
    const rawData = aiHistoryData.data || aiHistoryData;

    requestedSensorTypes.forEach(frontendSensorType => {
      const backendSensorType = toBackendKey(frontendSensorType);
      const historyForSensor = rawData[backendSensorType];
      
      if (historyForSensor && Array.isArray(historyForSensor)) {
        const sortedHistory = historyForSensor.sort((a, b) => 
          new Date(a.timestamp || a.time) - new Date(b.timestamp || b.time)
        );
        
        chartData[frontendSensorType] = {
          labels: sortedHistory.map(item => 
            new Date(item.timestamp || item.time).toLocaleTimeString('vi-VN', { 
              hour: '2-digit', 
              minute: '2-digit', 
              timeZone: 'Asia/Ho_Chi_Minh' 
            })
          ),
          values: sortedHistory.map(item => parseFloat(item.value) || 0)
        };
      } else {
        chartData[frontendSensorType] = { labels: [], values: [] };
      }
    });

    return {
      chartData,
      timestamp: aiHistoryData.timestamp || new Date().toISOString(),
      source: 'ai_service_history_api',
      period_hours: aiHistoryData.period_hours || 'N/A'
    };
  }

  /**
   * Lấy dữ liệu lịch sử
   */
  async fetchHistoricalData(options = {}) {
    const {
      hours = 24,
      sensorTypes = ['temperature', 'moisture', 'light', 'soil'],
      forceRefresh = false
    } = options;

    const cacheKey = `${this.cacheConfig.history.key}_${hours}_${sensorTypes.join('_')}`;
    const { ttl } = this.cacheConfig.history;

    if (!forceRefresh && this.isCacheValid(cacheKey, ttl)) {
      const cachedData = this.getCache(cacheKey);
      if (cachedData) {
        console.log('Using cached historical data');
        return cachedData;
      }
    }

    try {
      console.log("Fetching historical data from AI Service:", API_ENDPOINTS.AI.SENSORS_HISTORY);
      const historyResponse = await api.get(API_ENDPOINTS.AI.SENSORS_HISTORY, {
        params: { hours }
      });
      
      if (historyResponse.data) {
        const processedHistory = this.processAIHistoricalData(historyResponse.data, sensorTypes);
        this.setCache(cacheKey, processedHistory);
        return processedHistory;
      }
      
      throw new Error("AI History API returned no data.");

    } catch (error) {
      console.error("Error fetching historical data from AI Service:", error.message);
      return this.createDefaultHistoricalDataOnError(sensorTypes, `Lỗi tải lịch sử từ AI: ${error.message}`);
    }
  }

  /**
   * Phân tích dữ liệu sensor
   */
  async analyzeSensor(sensorType, collectFresh = false) {
    const cacheKey = `${this.cacheConfig.analysis.key}_${sensorType}`;
    const { ttl } = this.cacheConfig.analysis;

    if (!collectFresh && this.isCacheValid(cacheKey, ttl)) {
      const cachedAnalysis = this.getCache(cacheKey);
      if (cachedAnalysis) {
        console.log(`Using cached analysis for ${sensorType}`);
        return cachedAnalysis;
      }
    }

    try {
      const backendSensorType = toBackendKey(sensorType);
      
      console.log("Fetching analysis from Core Ops:", API_ENDPOINTS.CORE_OPERATIONS.SENSORS.ANALYZE_SPECIFIC(backendSensorType));
      const analysisResponse = await api.get(API_ENDPOINTS.CORE_OPERATIONS.SENSORS.ANALYZE_SPECIFIC(backendSensorType), {
        params: { collect: collectFresh }
      });
      
      const rawAnalysis = analysisResponse.data;
      if (rawAnalysis && rawAnalysis.analysis) {
        const collector = this.collectorManager.getCollector(sensorType);
        const reading = collector ? collector.createReading(rawAnalysis.reading) : null;
        
        const analysisData = {
          sensor_type: sensorType,
          reading: reading ? reading.toDict() : rawAnalysis.reading,
          analysis: rawAnalysis.analysis,
          timestamp: rawAnalysis.timestamp,
          recommendation: reading ? collector.getRecommendation(reading) : null
        };
        
        this.setCache(cacheKey, analysisData);
        return analysisData;
      }
      
      throw new Error(`Analysis API for ${sensorType} returned invalid data.`);
      
    } catch (error) {
      console.error(`Error analyzing ${sensorType}:`, error.message);
      return this.createDefaultAnalysisOnError(sensorType, error.message);
    }
  }

  /**
   * Lấy reading từ collector cache
   */
  getCachedReading(sensorType) {
    const collector = this.collectorManager.getCollector(sensorType);
    return collector ? collector.getCachedReading() : null;
  }

  /**
   * Lấy recommendation cho sensor
   */
  getRecommendation(sensorType) {
    const reading = this.getCachedReading(sensorType);
    if (!reading) return null;
    
    const collector = this.collectorManager.getCollector(sensorType);
    return collector ? collector.getRecommendation(reading) : null;
  }

  /**
   * Tạo dữ liệu mặc định khi lỗi
   */
  createDefaultSensorDataOnError(errorMessage = "Không thể kết nối đến sensors") {
    const defaultSensors = {};
    const sensorTypes = ['temperature', 'moisture', 'light', 'soil'];
    
    sensorTypes.forEach(type => {
      const config = getSensorConfig(type);
      const collector = this.collectorManager.getCollector(type);
      
      const defaultReading = collector ? collector.createReading({
        value: 0,
        unit: config?.unit || "",
        timestamp: new Date().toISOString(),
        status: SensorStatus.ERROR
      }) : new SensorReading({
        value: 0,
        unit: config?.unit || "",
        timestamp: new Date().toISOString(),
        status: SensorStatus.ERROR,
        sensorType: type
      });

      defaultSensors[type] = defaultReading.toDict();
    });

    return {
      sensors: defaultSensors,
      overall_status: 'error',
      error: errorMessage,
      irrigation_recommendation: null,
      analysis_summary: null,
      timestamp: new Date().toISOString(),
      source: 'default_fallback_error'
    };
  }

  createDefaultHistoricalDataOnError(sensorTypes, errorMessage = "Không thể tải dữ liệu lịch sử") {
    const chartData = {};
    sensorTypes.forEach(type => {
      chartData[type] = { labels: [], values: [] };
    });
    
    return {
      chartData,
      timestamp: new Date().toISOString(),
      source: 'default_history_fallback_error',
      error: errorMessage
    };
  }

  createDefaultAnalysisOnError(sensorType, errorMessage) {
    const config = getSensorConfig(sensorType);
    
    return {
      sensor_type: sensorType,
      reading: {
        value: 0,
        unit: config?.unit || "",
        status: SensorStatus.ERROR,
        timestamp: new Date().toISOString()
      },
      analysis: {
        status: "error",
        description: "Không thể phân tích",
        needs_water: false
      },
      error: errorMessage,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Subscribe to sensor data updates
   */
  subscribe(callback) {
    this.subscribers.add(callback);
    return () => {
      this.subscribers.delete(callback);
    };
  }

  /**
   * Notify all subscribers
   */
  notifySubscribers(data) {
    this.subscribers.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error('Error in sensor data subscriber:', error);
      }
    });
  }

  /**
   * Clear all caches
   */
  clearCache() {
    this.cache.clear();
    this.lastFetchTimes.clear();
    this.collectorManager.clearAllCaches();
    console.log('Sensor service cache cleared');
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    return {
      serviceCacheSize: this.cache.size,
      subscriberCount: this.subscribers.size,
      cachedKeys: Array.from(this.cache.keys()),
      lastFetchTimes: Object.fromEntries(this.lastFetchTimes),
      collectorStats: this.collectorManager.getCollectorStats()
    };
  }
}

// Create singleton instance
const sensorService = new SensorService();

// Export convenience functions
export const fetchSensorData = (forceRefresh = false) => 
  sensorService.fetchCurrentSensorData(forceRefresh);

export const fetchChartData = (options = {}) => 
  sensorService.fetchHistoricalData(options);

export const analyzeSensorData = (sensorType, collectFresh = false) =>
  sensorService.analyzeSensor(sensorType, collectFresh);

export const getCachedSensorReading = (sensorType) =>
  sensorService.getCachedReading(sensorType);

export const getSensorRecommendation = (sensorType) =>
  sensorService.getRecommendation(sensorType);

export default sensorService;