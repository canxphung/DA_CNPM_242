// src/utils/sensorService.js
import api from './api';
import { API_ENDPOINTS } from './constants';
import { SensorStatus } from './sensorTypes';

class SensorService {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 30000; // 30 seconds
    this.subscribers = [];
  }

  /**
   * Subscribe to sensor data updates
   */
  subscribe(callback) {
    this.subscribers.push(callback);
    return () => {
      this.subscribers = this.subscribers.filter(cb => cb !== callback);
    };
  }

  /**
   * Notify all subscribers
   */
  notifySubscribers(data) {
    this.subscribers.forEach(callback => callback(data));
  }

  /**
   * Get cache key
   */
  getCacheKey(type, params = {}) {
    return `${type}_${JSON.stringify(params)}`;
  }

  /**
   * Check if cache is valid
   */
  isCacheValid(key) {
    const cached = this.cache.get(key);
    if (!cached) return false;
    
    const now = Date.now();
    return now - cached.timestamp < this.cacheTimeout;
  }

  /**
   * Get from cache
   */
  getFromCache(key) {
    const cached = this.cache.get(key);
    return cached ? cached.data : null;
  }

  /**
   * Set cache
   */
  setCache(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache.clear();
  }

  /**
   * Get cache stats
   */
  getCacheStats() {
    const stats = {
      size: this.cache.size,
      entries: []
    };

    this.cache.forEach((value, key) => {
      stats.entries.push({
        key,
        age: Date.now() - value.timestamp,
        expired: !this.isCacheValid(key)
      });
    });

    return stats;
  }

  /**
   * Create default sensor data structure
   */
  createDefaultSensorData() {
    return {
      sensors: {
        temperature: {
          value: null,
          unit: '°C',
          status: SensorStatus.UNKNOWN,
          timestamp: null,
          sensor_type: 'temperature',
          analysis: null
        },
        moisture: {
          value: null,
          unit: '%',
          status: SensorStatus.UNKNOWN,
          timestamp: null,
          sensor_type: 'moisture',
          analysis: null
        },
        light: {
          value: null,
          unit: 'Lux',
          status: SensorStatus.UNKNOWN,
          timestamp: null,
          sensor_type: 'light',
          analysis: null
        },
        soil: {
          value: null,
          unit: '%',
          status: SensorStatus.UNKNOWN,
          timestamp: null,
          sensor_type: 'soil',
          analysis: null
        }
      },
      overall_status: SensorStatus.UNKNOWN,
      analysis_summary: null,
      irrigation_recommendation: null,
      timestamp: new Date().toISOString(),
      source: 'default'
    };
  }

  /**
   * Transform API response to standard format
   */
  transformSensorData(apiResponse) {
    if (!apiResponse || !apiResponse.sensors) {
      return this.createDefaultSensorData();
    }

    const transformed = {
      sensors: {},
      overall_status: apiResponse.overall_status || SensorStatus.UNKNOWN,
      analysis_summary: apiResponse.analysis_summary || null,
      irrigation_recommendation: apiResponse.irrigation_recommendation || null,
      timestamp: apiResponse.timestamp || new Date().toISOString(),
      source: apiResponse.source || 'api'
    };

    // Transform each sensor
    Object.entries(apiResponse.sensors).forEach(([key, sensor]) => {
      transformed.sensors[key] = {
        value: sensor.value,
        unit: sensor.unit,
        status: sensor.status || SensorStatus.UNKNOWN,
        timestamp: sensor.timestamp,
        sensor_type: key,
        analysis: sensor.analysis || null,
        feedId: sensor.feedId,
        metadata: sensor.metadata
      };
    });

    return transformed;
  }

  /**
   * Fetch current sensor data
   */
  async fetchCurrentSensorData(forceRefresh = false) {
    const cacheKey = this.getCacheKey('current');
    
    if (!forceRefresh && this.isCacheValid(cacheKey)) {
      return this.getFromCache(cacheKey);
    }

    try {
      const response = await api.get(API_ENDPOINTS.CORE_OPERATIONS.SENSORS.SNAPSHOT);
      const data = this.transformSensorData(response.data);
      
      this.setCache(cacheKey, data);
      this.notifySubscribers(data);
      
      return data;
    } catch (error) {
      console.error('Error fetching sensor data:', error);
      
      // Return cached data if available, even if expired
      const cachedData = this.getFromCache(cacheKey);
      if (cachedData) {
        return {
          ...cachedData,
          error: error.message,
          source: 'cache_fallback'
        };
      }
      
      // Return default data with error
      return {
        ...this.createDefaultSensorData(),
        error: error.message,
        source: 'default_fallback_error'
      };
    }
  }

  /**
   * Fetch historical data
   */
  async fetchHistoricalData(options = {}) {
    const { hours = 24, sensorTypes = ['temperature', 'moisture', 'light', 'soil'], forceRefresh = false } = options;
    
    const cacheKey = this.getCacheKey('history', { hours, sensorTypes });
    
    if (!forceRefresh && this.isCacheValid(cacheKey)) {
      return this.getFromCache(cacheKey);
    }

    try {
      // This is a placeholder - you'll need to implement the actual API endpoint
      // For now, return mock data
      const mockData = {
        chartData: {},
        timestamp: new Date().toISOString(),
        source: 'mock',
        period_hours: hours
      };

      sensorTypes.forEach(type => {
        const dataPoints = 24; // 24 data points for the period
        mockData.chartData[type] = {
          labels: Array.from({ length: dataPoints }, (_, i) => {
            const date = new Date();
            date.setHours(date.getHours() - (dataPoints - i));
            return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
          }),
          values: Array.from({ length: dataPoints }, () => {
            switch (type) {
              case 'temperature': return 20 + Math.random() * 15;
              case 'moisture': return 40 + Math.random() * 30;
              case 'light': return 500 + Math.random() * 1500;
              case 'soil': return 30 + Math.random() * 40;
              default: return 0;
            }
          })
        };
      });

      this.setCache(cacheKey, mockData);
      return mockData;
    } catch (error) {
      console.error('Error fetching historical data:', error);
      return {
        chartData: {},
        error: error.message,
        timestamp: new Date().toISOString(),
        source: 'error'
      };
    }
  }

  /**
   * Analyze specific sensor
   */
  async analyzeSensor(sensorType, collectFresh = false) {
    try {
      const endpoint = API_ENDPOINTS.CORE_OPERATIONS.SENSORS.ANALYZE_SPECIFIC(sensorType);
      const response = await api.get(endpoint, {
        params: { collect_fresh: collectFresh }
      });
      
      return response.data;
    } catch (error) {
      console.error(`Error analyzing ${sensorType}:`, error);
      throw error;
    }
  }

  /**
   * Get recommendation for sensor
   */
  getRecommendation(sensorType) {
    // This would typically come from the analysis or a separate endpoint
    const recommendations = {
      temperature: 'Duy trì nhiệt độ trong khoảng 20-30°C cho cây trồng phát triển tốt nhất',
      moisture: 'Độ ẩm không khí lý tưởng là 60-80%',
      light: 'Cung cấp 12-16 giờ ánh sáng mỗi ngày cho cây trồng',
      soil: 'Giữ độ ẩm đất ở mức 40-60% cho hầu hết các loại cây'
    };
    
    return recommendations[sensorType] || 'Không có khuyến nghị cụ thể';
  }
}

const sensorService = new SensorService();
export default sensorService;