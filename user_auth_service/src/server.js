const app = require('./app');
const config = require('./infrastructure/config');
const logger = require('./infrastructure/logging/logger');
const { connectToDatabase } = require('./infrastructure/database/connection');

// Import tích hợp (chỉ để khởi tạo)
require('./infrastructure/integration/service-discovery');
require('./infrastructure/integration/api-gateway');

// Xử lý lỗi không được bắt
process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception:', error);
  // Trong trường hợp lỗi nghiêm trọng, restart process
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // Không thoát process để giữ server chạy
});

// Kết nối đến cơ sở dữ liệu trước khi khởi động server
const startServer = async () => {
  try {
    // Kết nối đến MongoDB
    await connectToDatabase();
    logger.info('Connected to MongoDB database');
    
    // Khởi động server
    app.listen(config.port, () => {
      logger.info(`User & Auth Service running on ${config.host}:${config.port}`);
      logger.info(`API available at ${config.apiPrefix}`);
      logger.info(`API Documentation: ${config.apiPrefix}/docs`);
      logger.info(`Environment: ${config.env}`);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
};

startServer();