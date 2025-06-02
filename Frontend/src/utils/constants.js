// src/utils/constants.js
export const API_BASE_URL = "http://localhost:3000/api/v1"; // Gateway URL

// Service prefixes theo API Gateway routing
export const USER_AUTH_PREFIX = "";  // Gateway đã xử lý prefix
export const CORE_OPERATIONS_PREFIX = "";  // Gateway đã xử lý prefix
export const AI_SERVICE_PREFIX = "";  // Gateway đã xử lý prefix

export const API_ENDPOINTS = {
  // User Authentication & Management Service
  AUTH: {
    LOGIN: `/user-auth/auth/login`,
    REGISTER: `/user-auth/auth/register`,
    REFRESH_TOKEN: `/user-auth/auth/refresh-token`,
    LOGOUT: `/user-auth/auth/logout`,
    LOGOUT_ALL: `/user-auth/auth/logout-all`,
    ME: `/user-auth/auth/me`,
  },
  USERS: {
    BASE: `/user-auth/users`,
    ME: `/user-auth/users/me`,
    BY_ID: (id) => `/user-auth/users/${id}`,
    CHANGE_PASSWORD: `/user-auth/users/change-password`,
    DEACTIVATE: (id) => `/user-auth/users/${id}/deactivate`,
    ACTIVATE: (id) => `/user-auth/users/${id}/activate`,
  },
  ROLES: {
    BASE: `/user-auth/roles`,
    BY_ID: (id) => `/user-auth/roles/${id}`,
  },
  PERMISSIONS: {
    BASE: `/user-auth/permissions`,
    BY_ID: (id) => `/user-auth/permissions/${id}`,
  },

  // Core Operations Service
  CORE_OPERATIONS: {
    // Control routes
    CONTROL: {
      STATUS: `/core-operations/control/status`,
      HISTORY: `/core-operations/control/history`,
      SYSTEM_ACTION: (action) => `/core-operations/control/system/${action}`,
      PUMP_ACTION: (action) => `/core-operations/control/pump/${action}`,
      PUMP_STATUS: `/core-operations/control/pump/status`,
      SCHEDULES_BASE: `/core-operations/control/schedules`,
      SCHEDULE_BY_ID: (id) => `/core-operations/control/schedules/${id}`,
      AUTO_IRRIGATION_CONFIG: `/core-operations/control/auto`,
      AUTO_IRRIGATION_ACTION: (action) => `/core-operations/control/auto/${action}`,
      RECOMMENDATION_RECEIVE: `/core-operations/control/recommendation`,
    },
    // System routes
    SYSTEM_CONFIG: `/core-operations/system/config`,
    SYSTEM_CONFIG_BULK: `/core-operations/system/config/bulk`,
    SYSTEM_CONFIG_RESET: `/core-operations/system/config/reset`,
    SYSTEM_INFO: `/core-operations/system/info`,
    // Sensor routes
    SENSORS: {
      LIST_AVAILABLE: `/core-operations/sensors`,
      COLLECT_ALL: `/core-operations/sensors/collect`,
      SNAPSHOT: `/core-operations/sensors/snapshot`,
      ANALYZE: `/core-operations/sensors/analyze`,
      ANALYZE_SPECIFIC: (type) => `/core-operations/sensors/analyze/${type}`,
      BY_TYPE: (type) => `/core-operations/sensors/${type}`,
    },
    // Health & Version
    HEALTH: `/core-operations/health`,
    VERSION: `/core-operations/version`,
  },

  // AI Service
  AI: {
    // Analytics routes
    ANALYTICS_HISTORY: `/greenhouse-ai/api/analytics/history`,
    ANALYTICS_OPTIMIZE: `/greenhouse-ai/api/analytics/optimize`,
    ANALYTICS_MODEL_PERFORMANCE: `/greenhouse-ai/api/analytics/model-performance`,
    
    // Chat routes
    CHAT_MESSAGE: `/greenhouse-ai/api/chat/message`,
    
    // Recommendation routes
    RECOMMENDATION_CREATE: `/greenhouse-ai/api/recommendation/create`,
    RECOMMENDATION_HISTORY: `/greenhouse-ai/api/recommendation/history`,
    RECOMMENDATION_BY_ID: (id) => `/greenhouse-ai/api/recommendation/${id}`,
    RECOMMENDATION_SEND_TO_CORE: (id) => `/greenhouse-ai/api/recommendation/${id}/send`,
    RECOMMENDATION_OPTIMIZE_SCHEDULE: `/greenhouse-ai/api/recommendation/optimize/schedule`,
    
    // Sensor routes (AI version)
    SENSORS_CURRENT: `/greenhouse-ai/api/sensors/current`,
    SENSORS_DATA: `/greenhouse-ai/api/sensors/data`,
    SENSORS_HISTORY: `/greenhouse-ai/api/sensors/history`,
    
    // Health
    HEALTH: `/greenhouse-ai/health`,
  },

  // Upload service
  UPLOAD: {
    IMAGE: `/user-auth/uploads/image` // Assuming upload is part of User Auth service
  }
};

export const CHART_CONFIG = {
  temperature: {
    title: "Nhiệt độ",
    lineColor: "rgb(239, 68, 68)",
    yAxisLabel: "°C",
  },
  humidity: { // Changed from "moisture" to "humidity" for air humidity as per API sensor list
    title: "Độ ẩm không khí",
    lineColor: "rgb(59, 130, 246)",
    yAxisLabel: "%",
  },
  light: {
    title: "Cường độ ánh sáng",
    lineColor: "rgb(234, 179, 8)",
    yAxisLabel: "Lux",
  },
  soil_moisture: { // Added specific for soil moisture
    title: "Độ ẩm đất",
    lineColor: "rgb(34, 197, 94)",
    yAxisLabel: "%",
  },
};

export const ERROR_MESSAGES = {
  NETWORK_ERROR: "Không thể kết nối đến server. Vui lòng kiểm tra kết nối mạng.",
  UNAUTHORIZED: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  FORBIDDEN: "Bạn không có quyền thực hiện hành động này.",
  NOT_FOUND: "Không tìm thấy dữ liệu yêu cầu.",
  VALIDATION_ERROR: "Dữ liệu nhập vào không hợp lệ. Vui lòng kiểm tra lại các trường.",
  SERVER_ERROR: "Lỗi server. Vui lòng thử lại sau hoặc liên hệ quản trị viên.",
  TOKEN_EXPIRED: "Token đã hết hạn. Đang làm mới...",
  REFRESH_FAILED: "Không thể làm mới phiên đăng nhập. Vui lòng đăng nhập lại.",
  SERVICE_UNAVAILABLE: (serviceName) => `${serviceName} hiện không khả dụng. Vui lòng thử lại sau.`
};

export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  ACCEPTED: 202,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  VALIDATION_ERROR: 422,
  TOO_MANY_REQUESTS: 429,
  SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
};

export const STORAGE_KEYS = {
  ACCESS_TOKEN: "smartwater_access_token", // Added prefix for clarity
  REFRESH_TOKEN: "smartwater_refresh_token",
  USER_DATA: "smartwater_user_data",
  PERMISSIONS: "smartwater_user_permissions",
  USER_ROLES: "smartwater_user_roles", // Added this
};

// Permissions (from AuthContext.jsx - should be kept in sync or imported)
// These should ideally come from a shared source or AuthContext itself
export const PERMISSIONS = {
  // Dashboard & General
  VIEW_DASHBOARD: "dashboard:read", // Consistent with AuthContext
  VIEW_REPORTS: "reports:read",

  // User Management (renaming to align with new constants)
  MANAGE_USERS: "user:manage", // Higher level permission
  CREATE_USER: "user:create",
  READ_USER: "user:read",
  UPDATE_USER: "user:update",
  DELETE_USER: "user:delete",

  // Profile Management
  EDIT_PROFILE: "profile:update",
  CHANGE_PASSWORD: "profile:change_password",

  // Device Management
  MANAGE_DEVICES: "device:control", // Used for pump/light on/off in ConfigDevice
  CONFIGURE_DEVICES: "device:configure", // Used for speed/intensity/thresholds in ConfigDevice
  READ_DEVICES: "device:read",

  // Irrigation Specific (aligning with API service, from DeviceStatusMonitor or new irrigation services)
  READ_IRRIGATION: "irrigation:read",
  CONTROL_IRRIGATION: "irrigation:control", // Might cover pump on/off
  MANAGE_SCHEDULES: "irrigation:schedule", // From Schedule.jsx and AuthContext for sidebar

  // System
  VIEW_SETTINGS: "system:read", // General read access to system info/config
  MANAGE_SYSTEM_CONFIG: "system:configure", // For PUT /system/config

  // Admin
  ADMIN_ACCESS: "admin:access", // Broad admin access

  // Roles and Permissions Management
  MANAGE_ROLES: "role:manage",
  MANAGE_PERMISSIONS: "permission:manage",
};