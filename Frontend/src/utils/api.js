// src/utils/api.js
import axios from 'axios';
import { API_BASE_URL, ERROR_MESSAGES, HTTP_STATUS, STORAGE_KEYS } from './constants';

class ApiClient {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL, // API Gateway URL
      timeout: 15000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  setupInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        config.metadata = { startTime: new Date() };
        return config;
      },
      (error) => {
        console.error('Request interceptor error:', error);
        return Promise.reject(error);
      }
    );

    this.client.interceptors.response.use(
      (response) => {
        if (response.config.metadata) {
          const duration = new Date() - response.config.metadata.startTime;
          console.log(`API Call: ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`);
        }
        return response;
      },
      async (error) => {
        const originalRequest = error.config;

        if (error.response) {
          const { status, data } = error.response;

          if (status === HTTP_STATUS.UNAUTHORIZED && !originalRequest._retryAttempted) {
            originalRequest._retryAttempted = true;
            try {
              const newToken = await this.refreshAccessToken();
              if (newToken) {
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
                return this.client(originalRequest);
              }
            } catch (refreshError) {
              console.error('Token refresh failed:', refreshError);
              this.handleAuthenticationFailure(refreshError.message || ERROR_MESSAGES.REFRESH_FAILED);
              // Return a structured error after auth failure
              return Promise.reject(this.createStandardError(refreshError, HTTP_STATUS.UNAUTHORIZED));
            }
          }
          // If token refresh was attempted and failed, or if it's another error type.
          if(status === HTTP_STATUS.UNAUTHORIZED && originalRequest._retryAttempted){
              this.handleAuthenticationFailure(ERROR_MESSAGES.UNAUTHORIZED);
          }

          const standardError = this.parseServiceError(data, status, originalRequest.url);
          return Promise.reject(standardError);
        }

        if (error.request) {
          console.error('Network error:', error.message);
          return Promise.reject({
            message: ERROR_MESSAGES.NETWORK_ERROR,
            status: 0, // Typically 0 for network errors
            isNetworkError: true,
            url: originalRequest.url
          });
        }

        return Promise.reject(this.createStandardError(error));
      }
    );
  }

  parseServiceError(errorData, status, requestUrl = '') {
    let message = ERROR_MESSAGES.SERVER_ERROR; // Default server error
    let details = null;
    let validationErrors = null;
    let errorCode = null;

    // Determine which service might have responded based on URL structure, if needed
    // For simplicity, we'll try to parse common structures first.

    if (errorData) {
      // User Auth Service like format: {"error": "message"} or {"errors": [validation]}
      if (typeof errorData.error === 'string') {
        message = errorData.error;
      }
      if (Array.isArray(errorData.errors) && errorData.errors.length > 0 && errorData.errors[0].msg && errorData.errors[0].field) {
        validationErrors = errorData.errors.map(err => `${err.field}: ${err.msg}`).join('; ');
        message = `${ERROR_MESSAGES.VALIDATION_ERROR}: ${validationErrors}`;
      }

      // Core Operations Service & some AI formats: {"detail": "message"} or {"detail": [validation_objects]}
      if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          message = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          // FastAPI validation error format: [{"loc": ["body", "field"], "msg": "error message", "type": "validation_type"}]
          validationErrors = errorData.detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join('; ');
          message = `${ERROR_MESSAGES.VALIDATION_ERROR}: ${validationErrors}`;
          details = errorData.detail;
        }
      }

      // Specific AI Service error format for validation: {"error": "Validation Error", "detail": [...]}
      if (errorData.error === "Validation Error" && Array.isArray(errorData.detail)) {
        validationErrors = errorData.detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join('; ');
        message = `AI Service Validation: ${validationErrors}`;
        details = errorData.detail;
        errorCode = "AI_VALIDATION_ERROR";
      }
      
      // AI Service unhandled exception: {"error": "Internal Server Error", "detail": "exception string"}
      if (errorData.error === "Internal Server Error" && typeof errorData.detail === 'string') {
        message = `AI Service Error: ${errorData.detail.substring(0, 200)}${errorData.detail.length > 200 ? '...' : ''}`; // Keep it concise
        errorCode = "AI_INTERNAL_SERVER_ERROR";
      }

      // Core Operations error code
      if(errorData.error_code){
        errorCode = errorData.error_code;
      }
    }
    
    // General fallbacks based on status code if message is still generic
    if (message === ERROR_MESSAGES.SERVER_ERROR || (message === ERROR_MESSAGES.VALIDATION_ERROR && !validationErrors) ) {
        switch (status) {
            case HTTP_STATUS.BAD_REQUEST: message = ERROR_MESSAGES.VALIDATION_ERROR; break; // Assume 400 is validation if not specified
            case HTTP_STATUS.UNAUTHORIZED: message = ERROR_MESSAGES.UNAUTHORIZED; break;
            case HTTP_STATUS.FORBIDDEN: message = ERROR_MESSAGES.FORBIDDEN; break;
            case HTTP_STATUS.NOT_FOUND: message = `${ERROR_MESSAGES.NOT_FOUND} (URL: ${requestUrl})`; break;
            case HTTP_STATUS.VALIDATION_ERROR: message = ERROR_MESSAGES.VALIDATION_ERROR; break; // HTTP 422
            case HTTP_STATUS.TOO_MANY_REQUESTS: message = "Quá nhiều yêu cầu, vui lòng thử lại sau."; break;
            case HTTP_STATUS.SERVICE_UNAVAILABLE: message = ERROR_MESSAGES.SERVICE_UNAVAILABLE("Hệ thống"); break;
            // Keep default server error for 500
        }
    }


    return {
      message,
      status,
      details, // This can hold the raw 'detail' array from FastAPI validation errors
      validationErrors, // A formatted string of validation errors
      errorCode,
      originalError: errorData,
      url: requestUrl
    };
  }

  createStandardError(error, defaultStatus = HTTP_STATUS.SERVER_ERROR) {
    return {
      message: error.message || ERROR_MESSAGES.SERVER_ERROR,
      status: error.response?.status || error.status || defaultStatus,
      originalError: error,
      url: error.config?.url,
    };
  }

  getAccessToken() {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  }

  getRefreshToken() {
    return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
  }

  setTokens(accessToken, refreshToken) {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    if (refreshToken) {
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    }
  }

  clearAuthData() {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER_DATA);
    localStorage.removeItem(STORAGE_KEYS.PERMISSIONS);
  }

  async refreshAccessToken() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      console.warn('No refresh token available for refresh.');
      this.handleAuthenticationFailure(ERROR_MESSAGES.REFRESH_FAILED);
      throw this.createStandardError({ message: ERROR_MESSAGES.REFRESH_FAILED }, HTTP_STATUS.UNAUTHORIZED);
    }

    try {
      // Directly use axios to avoid interceptor loop on refresh failure for /auth/refresh-token
      const response = await axios.post(
        `${API_BASE_URL}${API_ENDPOINTS.AUTH.REFRESH_TOKEN}`, // Ensure this path is correct AFTER gateway
        { refreshToken },
        { 
            headers: {'Content-Type': 'application/json'},
            timeout: 10000 // Shorter timeout for refresh token
        } 
      );

      const { accessToken, refreshToken: newRefreshToken } = response.data;
      
      if (accessToken) {
        this.setTokens(accessToken, newRefreshToken || refreshToken);
        console.log("Token refreshed successfully.");
        return accessToken;
      }
      // If API returns 200 but no accessToken, it's an issue.
      console.error('Token refresh response missing access token.');
      this.handleAuthenticationFailure(ERROR_MESSAGES.REFRESH_FAILED);
      throw this.createStandardError({ message: ERROR_MESSAGES.REFRESH_FAILED }, HTTP_STATUS.UNAUTHORIZED);

    } catch (error) {
      console.error('Token refresh API call failed:', error.response?.data || error.message);
      // Specific handling if refresh token itself is invalid/expired (e.g., BE returns 401/403 on refresh)
      if(error.response && (error.response.status === HTTP_STATUS.UNAUTHORIZED || error.response.status === HTTP_STATUS.FORBIDDEN)){
        this.handleAuthenticationFailure(error.response.data?.detail || error.response.data?.error || ERROR_MESSAGES.UNAUTHORIZED);
      } else {
        this.handleAuthenticationFailure(ERROR_MESSAGES.REFRESH_FAILED); // Generic failure if not specific auth error
      }
      throw this.createStandardError(error.response?.data || error, error.response?.status || HTTP_STATUS.UNAUTHORIZED);
    }
  }

  handleAuthenticationFailure(errorMessage = ERROR_MESSAGES.UNAUTHORIZED) {
    console.warn("Authentication failure:", errorMessage);
    this.clearAuthData();
    window.dispatchEvent(new CustomEvent('authFailure', {
      detail: { message: errorMessage }
    }));
  }

  async get(url, config = {}) {
    return this.client.get(url, config);
  }

  async post(url, data, config = {}) {
    return this.client.post(url, data, config);
  }

  async put(url, data, config = {}) {
    return this.client.put(url, data, config);
  }

  async patch(url, data, config = {}) { // Added patch method
    return this.client.patch(url, data, config);
  }

  async delete(url, config = {}) {
    return this.client.delete(url, config);
  }

  // Upload service - Assuming the API Gateway routes /uploads/image to a specific service
  // and that service handles multipart/form-data.
  // The current `API_BASE_URL` implies uploads might also go through /api/v1 prefix.
  // If UPLOAD.IMAGE is part of a service like USER_AUTH_SERVICE, it should be defined with its prefix.
  // For now, UPLOAD.IMAGE is defined as `/uploads/image`. If this is not prefixed by `/api/v1`
  // then the axios instance 'this.client' might not be suitable, or we need a specific uploader.
  // Assuming for now that it IS part of the general API structure:
  async upload(url, formData, onProgress = null) {
    // The 'url' parameter here should be the full path *after* the API_BASE_URL.
    // e.g., if UPLOAD.IMAGE is `${USER_AUTH_PREFIX}/users/me/avatar`, then pass that to this.client.post.
    // For `UPLOAD.IMAGE = '/uploads/image'`, the full URL would be `http://localhost:3000/api/v1/uploads/image`

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    };

    if (onProgress) {
      config.onUploadProgress = (progressEvent) => {
        if (progressEvent.total) {
            const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(percentCompleted);
        } else {
            onProgress(0); // Or handle unknown progress
        }
      };
    }
    // Using this.client ensures tokens are attached if needed for the upload endpoint
    return this.client.post(url, formData, config); 
  }

  // Specific service call methods (examples, to be used by individual service files)
  // These could be part of the ApiClient, or the individual service files could just use api.get, api.post etc.
  async coreService(method, endpoint, data = null, config = {}) {
    return this.client[method.toLowerCase()](`${CORE_OPERATIONS_PREFIX}${endpoint}`, data, config);
  }

  async aiService(method, endpoint, data = null, config = {}) {
    // Note: AI service paths in your docs start with /api/chat, /api/sensors etc.
    // If AI_SERVICE_PREFIX is "/ai-service", then endpoint should be passed as "/api/chat/message" not just "/chat/message"
    // Or, define AI endpoints in constants as AI.CHAT_MESSAGE: `${AI_SERVICE_PREFIX}/chat/message` if prefix does not include `/api`
    // For now, assuming `endpoint` includes the `/api/` part.
    return this.client[method.toLowerCase()](`${AI_SERVICE_PREFIX}${endpoint}`, data, config);
  }
  
  async userService(method, endpoint, data = null, config = {}) { // Renamed from userAuthService for clarity
    return this.client[method.toLowerCase()](`${USER_AUTH_PREFIX}${endpoint}`, data, config);
  }
}

const api = new ApiClient();

export default api;
export { ApiClient }; // Exporting class if it's needed elsewhere for extension/testing