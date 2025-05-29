// app.js
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const statusMonitor = require('express-status-monitor');
const swaggerUi = require('swagger-ui-express');

const config = require('./infrastructure/config');
const logger = require('./infrastructure/logging/logger');
const httpLogger = require('./infrastructure/middlewares/http-logger.middleware');
const { rateLimiter, speedLimiter } = require('./infrastructure/middlewares/rate-limit.middleware');
const apiVersionMiddleware = require('./infrastructure/middlewares/api-version.middleware');
const swaggerSpec = require('./infrastructure/config/swagger');

// Import routes
const userRoutes = require('./api/user.routes');
const authRoutes = require('./api/auth.routes');
const permissionRoutes = require('./api/permission.routes');
const roleRoutes = require('./api/role.routes');
const userRoleRoutes = require('./api/user-role.routes');
const monitoringRoutes = require('./api/monitoring.routes');

// Khởi tạo app
const app = express();

// ----------------------------------------------------
// THÊM DÒNG NÀY ĐỂ TIN TƯỞNG PROXY
// Cấu hình Express để tin tưởng header X-Forwarded-For từ proxy.
// - true: Tin tưởng tất cả proxy (ít an toàn nhất nếu có nhiều proxy không kiểm soát)
// - 1: Tin tưởng 1 hop proxy (nếu Go Gateway là proxy duy nhất giữa client và Node.js)
// - 'loopback': Nếu cả Gateway và Node.js chạy trên cùng một máy (127.0.0.1 hoặc ::1)
// - IP Address/Subnet: Tin tưởng các IP hoặc dải IP cụ thể của proxy
//
// Trong trường hợp này, vì Go Gateway là proxy trực tiếp, `1` là lựa chọn tốt nhất.
app.set('trust proxy', 1);
// ----------------------------------------------------

// Thiết lập status monitor
app.use(statusMonitor());

// HTTP request logging
app.use(httpLogger);

// Middleware cơ bản
app.use(helmet()); // Bảo mật HTTP headers
app.use(cors(config.cors)); // Xử lý CORS
app.use(express.json({ limit: '1mb' })); // Parse JSON requests
app.use(express.urlencoded({ extended: true, limit: '1mb' }));
app.use(compression()); // Nén response

// THÊM MIDDLEWARE DEBUG NÀY
app.use((req, res, next) => {
  logger.info(`[DEBUG] Received request body: ${JSON.stringify(req.body)}`);
  logger.info(`[DEBUG] Request headers (Content-Type): ${req.get('Content-Type')}`);
  next();
});
// ----------------------------------------------------

app.use(compression()); // Nén response
// ----------------------------------------------------

// API version handling
app.use(apiVersionMiddleware('1.0.0'));

// Rate limiting
app.use(speedLimiter);
app.use(rateLimiter);

// Swagger documentation
app.use(`${config.apiPrefix}/docs`, swaggerUi.serve, swaggerUi.setup(swaggerSpec));

// Đăng ký routes
app.use(`${config.apiPrefix}/auth`, authRoutes);
app.use(`${config.apiPrefix}/users`, userRoutes);
app.use(`${config.apiPrefix}/permissions`, permissionRoutes);
app.use(`${config.apiPrefix}/roles`, roleRoutes);
app.use(`${config.apiPrefix}/users`, userRoleRoutes);
app.use(`${config.apiPrefix}/monitoring`, monitoringRoutes);
// Route mặc định
app.get('/', (req, res) => {
  res.status(200).json({
    service: 'User & Auth Service',
    version: '1.0.0',
    apiDocs: `${config.apiPrefix}/docs`
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error(`Error: ${err.message}`);
  logger.error(err.stack);
  
  res.status(err.status || 500).json({
    error: 'Internal Server Error',
    message: config.env === 'development' ? err.message : 'Something went wrong'
  });
});

// 404 handler
app.use((req, res) => {
  logger.warn(`Route not found: ${req.method} ${req.originalUrl}`);
  res.status(404).json({ error: 'Not Found' });
});

module.exports = app;