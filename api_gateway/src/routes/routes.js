const express = require('express');
const rateLimit = require('express-rate-limit');
const gatewayConfig = require('../config/gateway.config');
const authMiddleware = require('../middleware/auth');
const { createProxyMiddleware } = require('./proxy');

const router = express.Router();

// Hàm thiết lập routes
function setupRoutes() {
  // Duyệt qua tất cả routes trong cấu hình
  gatewayConfig.routes.forEach(route => {
    console.log(`Setting up route: ${route.path} -> ${route.service}`);
    
    // Lấy thông tin service
    const service = gatewayConfig.services[route.service];
    if (!service) {
      console.error(`Service ${route.service} not found in configuration`);
      return;
    }
    
    // Mảng middleware
    const middlewares = [];
    
    // Thêm rate limiter nếu được cấu hình
    if (route.rateLimit) {
      const limiter = rateLimit({
        windowMs: route.rateLimit.windowMs || 15 * 60 * 1000,
        max: route.rateLimit.max || 100,
        message: {
          error: 'Too many requests',
          message: 'Please try again later'
        }
      });
      middlewares.push(limiter);
    }
    
    // Thêm middleware xác thực nếu route được bảo vệ
    if (route.protected) {
      middlewares.push(authMiddleware(route.roles || []));
    }
    
    // Thêm proxy middleware
    middlewares.push(
      createProxyMiddleware(route.service, service.url, {
        timeout: service.timeout || 5000,
        stripPath: route.stripPath || false,
        prefix: route.path.replace('*', '')
      })
    );
    
    // Đăng ký route
    router.use(route.path, middlewares);
  });
  
  // Route mặc định cho các path không được định nghĩa
  router.use('*', (req, res) => {
    res.status(404).json({
      error: 'Not Found',
      message: 'The requested resource does not exist'
    });
  });
  
  return router;
}

module.exports = { setupRoutes };