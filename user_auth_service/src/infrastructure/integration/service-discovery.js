const axios = require('axios');
const logger = require('../logging/logger');
const config = require('../config');

// Cache cho service endpoints
let serviceCache = {};
const SERVICE_CACHE_TTL = 60000; // 1 minute

/**
 * Class quản lý giao tiếp với các service khác
 */
class ServiceDiscovery {
  constructor() {
    // Khởi tạo Axios instance cho các request đến service registry
    this.client = axios.create({
      baseURL: config.serviceRegistry.url || 'http://localhost:3000',
      timeout: 5000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
    
    // Thêm interceptor để log các request
    this.client.interceptors.request.use(request => {
      logger.debug(`External Request: ${request.method.toUpperCase()} ${request.baseURL}${request.url}`);
      return request;
    });
    
    // Thêm interceptor để log các response
    this.client.interceptors.response.use(
      response => {
        logger.debug(`External Response: ${response.status} ${response.config.url}`);
        return response;
      },
      error => {
        if (error.response) {
          logger.error(`External Error: ${error.response.status} ${error.config.url}`);
          logger.error(error.response.data);
        } else {
          logger.error(`External Request Failed: ${error.message}`);
        }
        return Promise.reject(error);
      }
    );
    
    // Đăng ký service với service registry
    this.registerService();
  }
  
  /**
   * Đăng ký service với service registry
   */
  async registerService() {
    if (!config.serviceRegistry.enabled) {
      logger.info('Service Registry is disabled, skipping registration');
      return;
    }
    
    try {
      const serviceInfo = {
        name: 'user-auth-service',
        version: '1.0.0',
        host: config.host || 'localhost',
        port: config.port,
        healthCheck: `${config.apiPrefix}/monitoring/health`
      };
      
      const response = await this.client.post('/register', serviceInfo);
      logger.info(`Service registered successfully: ${response.data.id}`);
      
      // Thiết lập heartbeat định kỳ để duy trì đăng ký
      this.setupHeartbeat(response.data.id);
    } catch (error) {
      logger.error('Failed to register service:', error.message);
    }
  }
  
  /**
   * Thiết lập heartbeat định kỳ
   * @param {String} serviceId - ID service đã đăng ký
   */
  setupHeartbeat(serviceId) {
    setInterval(async () => {
      try {
        await this.client.put(`/heartbeat/${serviceId}`);
        logger.debug(`Heartbeat sent for service: ${serviceId}`);
      } catch (error) {
        logger.error(`Heartbeat failed: ${error.message}`);
        // Thử đăng ký lại nếu heartbeat thất bại
        this.registerService();
      }
    }, 30000); // 30 seconds
  }
  
  /**
   * Tìm service theo tên
   * @param {String} serviceName - Tên service cần tìm
   * @returns {Promise<Object>} Thông tin service
   */
  async findService(serviceName) {
    // Kiểm tra cache
    if (serviceCache[serviceName] && 
       (Date.now() - serviceCache[serviceName].timestamp) < SERVICE_CACHE_TTL) {
      return serviceCache[serviceName].data;
    }
    
    try {
      const response = await this.client.get(`/find/${serviceName}`);
      
      // Cập nhật cache
      serviceCache[serviceName] = {
        data: response.data,
        timestamp: Date.now()
      };
      
      return response.data;
    } catch (error) {
      logger.error(`Service discovery failed for ${serviceName}: ${error.message}`);
      throw new Error(`Service ${serviceName} not found`);
    }
  }
  
  /**
   * Gửi request đến service khác
   * @param {String} serviceName - Tên service
   * @param {Object} requestOptions - Tùy chọn request
   * @returns {Promise<Object>} Response từ service
   */
  async callService(serviceName, requestOptions) {
    try {
      // Tìm service
      const service = await this.findService(serviceName);
      
      // Tạo URL endpoint
      const baseURL = `http://${service.host}:${service.port}`;
      
      // Tạo axios instance cho service
      const serviceClient = axios.create({
        baseURL,
        timeout: requestOptions.timeout || 5000,
        headers: {
          ...requestOptions.headers,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });
      
      // Gửi request
      const response = await serviceClient({
        method: requestOptions.method || 'get',
        url: requestOptions.url,
        data: requestOptions.data,
        params: requestOptions.params
      });
      
      return response.data;
    } catch (error) {
      logger.error(`Service call failed: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Xóa đăng ký service khi shutdown
   */
  async deregisterService() {
    if (!config.serviceRegistry.enabled || !this.serviceId) {
      return;
    }
    
    try {
      await this.client.delete(`/register/${this.serviceId}`);
      logger.info(`Service deregistered: ${this.serviceId}`);
    } catch (error) {
      logger.error(`Deregistration failed: ${error.message}`);
    }
  }
}

// Tạo instance
const serviceDiscovery = new ServiceDiscovery();

// Xử lý sự kiện shutdown để hủy đăng ký
process.on('SIGINT', async () => {
  logger.info('Shutting down...');
  await serviceDiscovery.deregisterService();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  logger.info('Shutting down...');
  await serviceDiscovery.deregisterService();
  process.exit(0);
});

module.exports = serviceDiscovery;