/**
 * Middleware xử lý version API thông qua header
 * @param {String} defaultVersion - Version mặc định
 * @returns {Function} Middleware function
 */
const apiVersionMiddleware = (defaultVersion = '1.0.0') => {
    return (req, res, next) => {
      // Lấy version từ header hoặc dùng version mặc định
      const version = req.headers['accept-version'] || defaultVersion;
      
      // Gán version vào request để sử dụng ở các handler
      req.apiVersion = version;
      
      // Thêm vào header response
      res.setHeader('X-API-Version', version);
      
      next();
    };
  };
  
  module.exports = apiVersionMiddleware;