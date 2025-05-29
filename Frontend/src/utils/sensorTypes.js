// src/utils/sensorTypes.js

/**
 * Enum cho các loại cảm biến
 */
export const SensorType = {
  LIGHT: 'light',
  TEMPERATURE: 'temperature', 
  HUMIDITY: 'humidity',
  SOIL_MOISTURE: 'soil_moisture'
};

/**
 * Mapping từ frontend keys sang backend keys
 */
export const SENSOR_MAPPING = {
  // Frontend key -> Backend key
  light: SensorType.LIGHT,
  temperature: SensorType.TEMPERATURE,
  moisture: SensorType.HUMIDITY,        // Frontend dùng 'moisture' cho air humidity
  soil: SensorType.SOIL_MOISTURE        // Frontend dùng 'soil' cho soil moisture
};

/**
 * Mapping ngược từ backend keys sang frontend keys
 */
export const BACKEND_TO_FRONTEND_MAPPING = {
  [SensorType.LIGHT]: 'light',
  [SensorType.TEMPERATURE]: 'temperature',
  [SensorType.HUMIDITY]: 'moisture',
  [SensorType.SOIL_MOISTURE]: 'soil'
};

/**
 * Cấu hình cho từng loại sensor
 */
export const SENSOR_CONFIG = {
  [SensorType.LIGHT]: {
    name: 'Cường độ ánh sáng',
    unit: 'Lux',
    icon: '☀️',
    color: 'rgb(234, 179, 8)',
    thresholds: {
      low: 500,
      high: 2000,
      optimal: { min: 800, max: 1500 }
    }
  },
  [SensorType.TEMPERATURE]: {
    name: 'Nhiệt độ',
    unit: '°C', 
    icon: '🌡️',
    color: 'rgb(239, 68, 68)',
    thresholds: {
      low: 18,
      high: 32,
      optimal: { min: 22, max: 28 }
    }
  },
  [SensorType.HUMIDITY]: {
    name: 'Độ ẩm không khí',
    unit: '%',
    icon: '💧',
    color: 'rgb(59, 130, 246)',
    thresholds: {
      low: 40,
      high: 80,
      optimal: { min: 50, max: 70 }
    }
  },
  [SensorType.SOIL_MOISTURE]: {
    name: 'Độ ẩm đất',
    unit: '%',
    icon: '🌱',
    color: 'rgb(34, 197, 94)',
    thresholds: {
      low: 30,
      high: 80,
      optimal: { min: 40, max: 70 }
    }
  }
};

/**
 * Trạng thái sensor
 */
export const SensorStatus = {
  NORMAL: 'normal',
  WARNING: 'warning', 
  CRITICAL: 'critical',
  ERROR: 'error',
  UNKNOWN: 'unknown'
};

/**
 * Lấy config cho sensor theo frontend key
 */
export const getSensorConfig = (frontendKey) => {
  const backendKey = SENSOR_MAPPING[frontendKey];
  return SENSOR_CONFIG[backendKey];
};

/**
 * Chuyển đổi frontend key sang backend key
 */
export const toBackendKey = (frontendKey) => {
  return SENSOR_MAPPING[frontendKey] || frontendKey;
};

/**
 * Chuyển đổi backend key sang frontend key
 */
export const toFrontendKey = (backendKey) => {
  return BACKEND_TO_FRONTEND_MAPPING[backendKey] || backendKey;
};