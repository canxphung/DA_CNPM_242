const httpProxy = require('express-http-proxy');
const url = require('url');
const { createCircuitBreaker } = require('../utils/circuit-breaker');

// Hàm tạo proxy middleware
const createProxyMiddleware = (serviceName, serviceUrl, options = {}) => {
  // Cấu hình mặc định
  const defaultOptions = {
    timeout: 5000,
    stripPath: false,
    prefix: '',
  };
  
  // Kết hợp options
  const proxyOptions = { ...defaultOptions, ...options };
  
  // Tạo hàm proxy
  const proxyService = (req, res, next) => {
    // Tạo proxy
    const proxy = httpProxy(serviceUrl, {
      // Tùy chỉnh đường dẫn
      proxyReqPathResolver: function(req) {
        // Lấy đường dẫn từ request
        let path = url.parse(req.url).path;
        
        // Nếu cần bỏ tiền tố
        if (proxyOptions.stripPath && proxyOptions.prefix) {
          path = path.replace(new RegExp(`^${proxyOptions.prefix}`), '');
        }
        
        return path;
      },
      
      // Thêm header
      proxyReqOptDecorator: function(proxyReqOpts, srcReq) {
        // Thêm header X-User nếu có thông tin user
        if (srcReq.user) {
          proxyReqOpts.headers['X-User-ID'] = srcReq.user.id;
          proxyReqOpts.headers['X-User-Role'] = srcReq.user.roles.join(',');
        }
        
        // Thêm header X-Original-IP
        proxyReqOpts.headers['X-Original-IP'] = 
          srcReq.headers['x-forwarded-for'] || 
          srcReq.connection.remoteAddress;
        
        return proxyReqOpts;
      },
      
      // Thiết lập timeout
      timeout: proxyOptions.timeout,
      
      // Xử lý lỗi
      proxyErrorHandler: function(err, res, next) {
        if (err.code === 'ECONNREFUSED') {
          console.error(`Service ${serviceName} is unavailable`);
          return res.status(503).json({
            error: 'Service Unavailable', 
            message: `The ${serviceName} service is currently unavailable`
          });
        }
        
        if (err.code === 'ETIMEDOUT') {
          console.error(`Service ${serviceName} timed out`);
          return res.status(504).json({
            error: 'Gateway Timeout', 
            message: `The ${serviceName} service timed out`
          });
        }
        
        console.error(`Proxy error for ${serviceName}:`, err);
        return res.status(500).json({
          error: 'Internal Server Error', 
          message: 'An unexpected error occurred'
        });
      }
    });
    
    // Chạy proxy
    proxy(req, res, next);
  };
  
  // Bọc proxy function trong circuit breaker
  const circuitBreaker = createCircuitBreaker(proxyService, {
    timeout: proxyOptions.timeout,
    fallback: (req, res) => {
      res.status(503).json({
        error: 'Service Unavailable',
        message: `The ${serviceName} service is temporarily unavailable`
      });
    }
  });
  
  // Trả về middleware xử lý request thông qua circuit breaker
  return (req, res, next) => {
    circuitBreaker.fire(req, res, next)
      .catch(error => {
        console.error(`Circuit breaker error for ${serviceName}:`, error);
        res.status(500).json({
          error: 'Internal Server Error',
          message: 'An unexpected error occurred'
        });
      });
  };
};

module.exports = { createProxyMiddleware };