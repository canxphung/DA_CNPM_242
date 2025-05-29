// src/utils/sensorCollectors.js

import { SensorType, SensorStatus, getSensorConfig, toBackendKey } from './sensorTypes';

/**
 * Class cơ bản cho SensorReading
 */
export class SensorReading {
  constructor(data = {}) {
    this.value = data.value || 0;
    this.unit = data.unit || '';
    this.timestamp = data.timestamp ? new Date(data.timestamp) : new Date();
    this.status = data.status || SensorStatus.UNKNOWN;
    this.feedId = data.feedId || `feed_${Date.now()}`;
    this.sensorType = data.sensorType || data.sensor_type;
    this.metadata = data.metadata || {};
  }

  /**
   * Chuyển đổi thành object để gửi API
   */
  toDict() {
    return {
      value: this.value,
      unit: this.unit,
      timestamp: this.timestamp.toISOString(),
      status: this.status,
      feedId: this.feedId,
      sensor_type: this.sensorType,
      metadata: this.metadata
    };
  }

  /**
   * Kiểm tra xem reading có hợp lệ không
   */
  isValid() {
    return this.value !== null && this.value !== undefined && !isNaN(this.value);
  }

  /**
   * Kiểm tra xem reading có quá cũ không
   */
  isStale(maxAgeMs = 5 * 60 * 1000) { // 5 phút
    return Date.now() - this.timestamp.getTime() > maxAgeMs;
  }
}

/**
 * Base class cho tất cả sensor collectors
 */
export class BaseSensorCollector {
  constructor(sensorType) {
    this.sensorType = sensorType;
    this.config = getSensorConfig(sensorType);
    this.cache = new Map();
    this.lastFetchTime = null;
    this.cacheTTL = 30000; // 30 giây
  }

  /**
   * Tạo SensorReading từ raw data
   */
  createReading(rawData) {
    return new SensorReading({
      value: rawData.value,
      unit: this.config?.unit || rawData.unit,
      timestamp: rawData.timestamp,
      status: this.determineStatus(rawData.value),
      feedId: rawData.feedId || `feed_${this.sensorType}_${Date.now()}`,
      sensorType: this.sensorType,
      metadata: rawData.metadata || {}
    });
  }

  /**
   * Xác định trạng thái dựa trên giá trị
   */
  determineStatus(value) {
    if (!this.config?.thresholds || value === null || value === undefined) {
      return SensorStatus.UNKNOWN;
    }

    const { low, high, optimal } = this.config.thresholds;
    
    if (value < low || value > high) {
      return SensorStatus.CRITICAL;
    }
    
    if (optimal && (value < optimal.min || value > optimal.max)) {
      return SensorStatus.WARNING;
    }
    
    return SensorStatus.NORMAL;
  }

  /**
   * Lấy dữ liệu từ cache
   */
  getCachedReading() {
    const cached = this.cache.get('latest');
    if (cached && !cached.isStale(this.cacheTTL)) {
      return cached;
    }
    return null;
  }

  /**
   * Lưu dữ liệu vào cache
   */
  setCachedReading(reading) {
    this.cache.set('latest', reading);
    this.lastFetchTime = Date.now();
  }

  /**
   * Xóa cache
   */
  clearCache() {
    this.cache.clear();
    this.lastFetchTime = null;
  }
}

/**
 * Light sensor collector
 */
export class LightSensorCollector extends BaseSensorCollector {
  constructor() {
    super('light');
  }

  processRawData(rawData) {
    const reading = this.createReading(rawData);
    
    // Xử lý đặc biệt cho light sensor
    if (reading.value < 0) {
      reading.value = 0;
      reading.status = SensorStatus.ERROR;
    }
    
    return reading;
  }

  getRecommendation(reading) {
    if (!reading.isValid()) return null;
    
    const value = reading.value;
    const { low, high, optimal } = this.config.thresholds;
    
    if (value < low) {
      return {
        type: 'warning',
        message: 'Ánh sáng quá yếu, cần tăng cường độ chiếu sáng',
        action: 'increase_light'
      };
    }
    
    if (value > high) {
      return {
        type: 'warning', 
        message: 'Ánh sáng quá mạnh, cần giảm cường độ',
        action: 'decrease_light'
      };
    }
    
    return {
      type: 'normal',
      message: 'Cường độ ánh sáng phù hợp',
      action: 'maintain'
    };
  }
}

/**
 * Temperature sensor collector
 */
export class TemperatureSensorCollector extends BaseSensorCollector {
  constructor() {
    super('temperature');
  }

  processRawData(rawData) {
    const reading = this.createReading(rawData);
    
    // Kiểm tra giá trị nhiệt độ hợp lý
    if (reading.value < -50 || reading.value > 80) {
      reading.status = SensorStatus.ERROR;
    }
    
    return reading;
  }

  getRecommendation(reading) {
    if (!reading.isValid()) return null;
    
    const value = reading.value;
    const { low, high } = this.config.thresholds;
    
    if (value < low) {
      return {
        type: 'warning',
        message: 'Nhiệt độ quá thấp, cần sưởi ấm',
        action: 'increase_temperature'
      };
    }
    
    if (value > high) {
      return {
        type: 'warning',
        message: 'Nhiệt độ quá cao, cần làm mát',
        action: 'decrease_temperature'
      };
    }
    
    return {
      type: 'normal',
      message: 'Nhiệt độ trong khoảng phù hợp',
      action: 'maintain'
    };
  }
}

/**
 * Humidity sensor collector
 */
export class HumiditySensorCollector extends BaseSensorCollector {
  constructor() {
    super('moisture'); // Frontend key
  }

  processRawData(rawData) {
    const reading = this.createReading(rawData);
    
    // Đảm bảo giá trị humidity trong khoảng 0-100%
    if (reading.value < 0) reading.value = 0;
    if (reading.value > 100) reading.value = 100;
    
    return reading;
  }

  getRecommendation(reading) {
    if (!reading.isValid()) return null;
    
    const value = reading.value;
    const { low, high } = this.config.thresholds;
    
    if (value < low) {
      return {
        type: 'warning',
        message: 'Độ ẩm không khí quá thấp, cần tăng độ ẩm',
        action: 'increase_humidity'
      };
    }
    
    if (value > high) {
      return {
        type: 'warning',
        message: 'Độ ẩm không khí quá cao, cần giảm độ ẩm',
        action: 'decrease_humidity'
      };
    }
    
    return {
      type: 'normal',
      message: 'Độ ẩm không khí phù hợp',
      action: 'maintain'
    };
  }
}

/**
 * Soil moisture sensor collector
 */
export class SoilMoistureSensorCollector extends BaseSensorCollector {
  constructor() {
    super('soil'); // Frontend key
  }

  processRawData(rawData) {
    const reading = this.createReading(rawData);
    
    // Đảm bảo giá trị soil moisture trong khoảng 0-100%
    if (reading.value < 0) reading.value = 0;
    if (reading.value > 100) reading.value = 100;
    
    return reading;
  }

  getRecommendation(reading) {
    if (!reading.isValid()) return null;
    
    const value = reading.value;
    const { low, high } = this.config.thresholds;
    
    if (value < low) {
      return {
        type: 'critical',
        message: 'Đất quá khô, cần tưới nước ngay',
        action: 'water_now'
      };
    }
    
    if (value > high) {
      return {
        type: 'warning',
        message: 'Đất quá ướt, tạm dừng tưới nước',
        action: 'stop_watering'
      };
    }
    
    return {
      type: 'normal',
      message: 'Độ ẩm đất phù hợp',
      action: 'maintain'
    };
  }
}

/**
 * Factory để tạo collectors
 */
export class SensorCollectorFactory {
  static collectors = {
    light: () => new LightSensorCollector(),
    temperature: () => new TemperatureSensorCollector(), 
    moisture: () => new HumiditySensorCollector(),
    soil: () => new SoilMoistureSensorCollector()
  };

  static create(sensorType) {
    const factory = this.collectors[sensorType];
    if (!factory) {
      throw new Error(`Unknown sensor type: ${sensorType}`);
    }
    return factory();
  }

  static getAllSensorTypes() {
    return Object.keys(this.collectors);
  }
}

/**
 * Manager để quản lý tất cả collectors
 */
export class SensorCollectorManager {
  constructor() {
    this.collectors = {};
    this.initializeCollectors();
  }

  initializeCollectors() {
    const sensorTypes = SensorCollectorFactory.getAllSensorTypes();
    sensorTypes.forEach(type => {
      this.collectors[type] = SensorCollectorFactory.create(type);
    });
  }

  getCollector(sensorType) {
    return this.collectors[sensorType];
  }

  getAllCollectors() {
    return this.collectors;
  }

  clearAllCaches() {
    Object.values(this.collectors).forEach(collector => {
      collector.clearCache();
    });
  }

  getCollectorStats() {
    const stats = {};
    Object.entries(this.collectors).forEach(([type, collector]) => {
      stats[type] = {
        lastFetchTime: collector.lastFetchTime,
        hasCachedData: collector.getCachedReading() !== null,
        cacheSize: collector.cache.size
      };
    });
    return stats;
  }
}