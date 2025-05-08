const axios = require('axios');
const logger = require('../logging/logger');
const config = require('../config');

/**
 * Class quản lý tích hợp với API Gateway
 */
class ApiGateway {
  constructor() {
    this.client = axios.create({
      baseURL: config.apiGateway.url || 'http://localhost:8000',
      timeout: 5000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
    
    // Đăng ký routes với API Gateway nếu được cấu hình
    if (config.apiGateway.enabled) {
      this.registerRoutes();
    }
  }
  
  /**
   * Đăng ký routes với API Gateway
   */
  async registerRoutes() {
    try {
      const routeDefinitions = [
        {
          path: '/auth',
          methods: ['POST', 'GET', 'PUT'],
          service: 'user-auth-service',
          version: '1.0.0'
        },
        {
          path: '/users',
          methods: ['GET', 'POST', 'PUT', 'DELETE'],
          service: 'user-auth-service',
          version: '1.0.0'
        },
        {
          path: '/roles',
          methods: ['GET', 'POST', 'PUT', 'DELETE'],
          service: 'user-auth-service',
          version: '1.0.0'
        },
        {
          path: '/permissions',
          methods: ['GET', 'POST', 'PUT', 'DELETE'],
          service: 'user-auth-service',
          version: '1.0.0'
        }
      ];
      
      const response = await this.client.post('/routes/register', {
        serviceId: 'user-auth-service',
        routes: routeDefinitions
      });
      
      logger.info(`Routes registered with API Gateway: ${response.data.message}`);
    } catch (error) {
      logger.error('Failed to register routes with API Gateway:', error.message);
    }
  }
  
  /**
   * Hủy đăng ký routes với API Gateway
   */
  async deregisterRoutes() {
    if (!config.apiGateway.enabled) {
      return;
    }
    
    try {
      await this.client.delete('/routes/user-auth-service');
      logger.info('Routes deregistered from API Gateway');
    } catch (error) {
      logger.error('Failed to deregister routes:', error.message);
    }
  }
}

// Tạo instance
const apiGateway = new ApiGateway();

// Xử lý sự kiện shutdown để hủy đăng ký
process.on('SIGINT', async () => {
  await apiGateway.deregisterRoutes();
});

process.on('SIGTERM', async () => {
  await apiGateway.deregisterRoutes();
});

module.exports = apiGateway;