// src/utils/sensorTypes.js

export const SensorStatus = {
  NORMAL: 'normal',
  WARNING: 'warning',
  CRITICAL: 'critical',
  ERROR: 'error',
  UNKNOWN: 'unknown',
  OPTIMAL: 'optimal',
  WARNING_HIGH: 'warning_high',
  WARNING_LOW: 'warning_low',
  CRITICAL_HIGH: 'critical_high',
  CRITICAL_LOW: 'critical_low'
};

export const SensorType = {
  TEMPERATURE: 'temperature',
  MOISTURE: 'moisture',
  LIGHT: 'light',
  SOIL: 'soil'
};

export const SensorUnit = {
  TEMPERATURE: '°C',
  MOISTURE: '%',
  LIGHT: 'Lux',
  SOIL: '%'
};

export const SensorThresholds = {
  temperature: {
    critical_low: 10,
    warning_low: 15,
    optimal_min: 20,
    optimal_max: 30,
    warning_high: 35,
    critical_high: 40
  },
  moisture: {
    critical_low: 20,
    warning_low: 30,
    optimal_min: 50,
    optimal_max: 80,
    warning_high: 85,
    critical_high: 90
  },
  light: {
    critical_low: 100,
    warning_low: 300,
    optimal_min: 500,
    optimal_max: 1500,
    warning_high: 1800,
    critical_high: 2000
  },
  soil: {
    critical_low: 20,
    warning_low: 30,
    optimal_min: 40,
    optimal_max: 60,
    warning_high: 70,
    critical_high: 80
  }
};

export const getStatusFromValue = (sensorType, value) => {
  if (value === null || value === undefined) {
    return SensorStatus.UNKNOWN;
  }

  const thresholds = SensorThresholds[sensorType];
  if (!thresholds) {
    return SensorStatus.UNKNOWN;
  }

  if (value <= thresholds.critical_low) {
    return SensorStatus.CRITICAL_LOW;
  } else if (value <= thresholds.warning_low) {
    return SensorStatus.WARNING_LOW;
  } else if (value >= thresholds.critical_high) {
    return SensorStatus.CRITICAL_HIGH;
  } else if (value >= thresholds.warning_high) {
    return SensorStatus.WARNING_HIGH;
  } else if (value >= thresholds.optimal_min && value <= thresholds.optimal_max) {
    return SensorStatus.OPTIMAL;
  } else {
    return SensorStatus.NORMAL;
  }
};

export const getStatusColor = (status) => {
  switch (status) {
    case SensorStatus.OPTIMAL:
    case SensorStatus.NORMAL:
      return 'text-green-600';
    case SensorStatus.WARNING:
    case SensorStatus.WARNING_HIGH:
    case SensorStatus.WARNING_LOW:
      return 'text-yellow-600';
    case SensorStatus.CRITICAL:
    case SensorStatus.CRITICAL_HIGH:
    case SensorStatus.CRITICAL_LOW:
      return 'text-red-600';
    case SensorStatus.ERROR:
      return 'text-red-700';
    default:
      return 'text-gray-500';
  }
};

export const getStatusBgColor = (status) => {
  switch (status) {
    case SensorStatus.OPTIMAL:
    case SensorStatus.NORMAL:
      return 'bg-green-50';
    case SensorStatus.WARNING:
    case SensorStatus.WARNING_HIGH:
    case SensorStatus.WARNING_LOW:
      return 'bg-yellow-50';
    case SensorStatus.CRITICAL:
    case SensorStatus.CRITICAL_HIGH:
    case SensorStatus.CRITICAL_LOW:
      return 'bg-red-50';
    case SensorStatus.ERROR:
      return 'bg-red-100';
    default:
      return 'bg-gray-50';
  }
};