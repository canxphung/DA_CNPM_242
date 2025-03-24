const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const dotenv = require('dotenv');
const winston = require('winston');
const { setupRoutes } = require('./routes/routes');

// Tải biến môi trường
dotenv.config();

// Khởi tạo logger
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'api-gateway-error.log', level: 'error' }),
    new winston.transports.File({ filename: 'api-gateway.log' })
  ]
});

// Khởi tạo Express app
const app = express();

// Middleware cơ bản
app.use(helmet()); // Bảo mật headers
app.use(cors());   // Hỗ trợ CORS
app.use(express.json()); // Parse JSON body

// Middleware logging
app.use((req, res, next) => {
  const start = Date.now();
  
  // Khi request hoàn thành, log thông tin
  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info({
      method: req.method,
      path: req.path,
      statusCode: res.statusCode,
      duration: `${duration}ms`,
      userAgent: req.headers['user-agent'],
      ip: req.headers['x-forwarded-for'] || req.connection.remoteAddress
    });
  });
  
  next();
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Thiết lập routes
app.use('/', setupRoutes());

// Middleware xử lý lỗi
app.use((err, req, res, next) => {
  logger.error({
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method
  });
  
  res.status(500).json({
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'production' 
      ? 'An unexpected error occurred' 
      : err.message
  });
});

// Khởi động server
// const PORT = process.env.PORT || 8000;
// app.listen(PORT, () => {
//   logger.info(`API Gateway running on port ${PORT}`);
//   logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
// });
// // Thêm vào src/server.js
// const http = require('http');
// const WebSocketProxy = require('./routes/websocket-proxy');

// Thay đổi cách khởi tạo server
// const app = express();
const server = http.createServer(app);

// Khởi tạo WebSocket proxy
const wsProxy = new WebSocketProxy(server);

// Thay đổi cách khởi động server
const PORT = process.env.PORT || 8000;
server.listen(PORT, () => {
  logger.info(`API Gateway running on port ${PORT}`);
  logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
});
// Xử lý sự kiện tắt
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  process.exit(0);
});

module.exports = app;