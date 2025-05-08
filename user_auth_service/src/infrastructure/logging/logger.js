const winston = require('winston');
const path = require('path');
const config = require('../config');

// Định nghĩa cấu hình format
const logFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.errors({ stack: true }),
  winston.format.splat(),
  winston.format.json()
);

// Thiết lập loại transports dựa vào môi trường
const transports = [];

// Luôn ghi log vào console
transports.push(
  new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.printf(
        info => `${info.timestamp} ${info.level}: ${info.message}`
      )
    )
  })
);

// Thêm file transport trong môi trường production
if (config.env === 'production') {
  // Log file chung cho tất cả các cấp độ
  transports.push(
    new winston.transports.File({
      filename: path.join('logs', 'combined.log'),
      format: logFormat
    })
  );
  
  // File log riêng cho lỗi
  transports.push(
    new winston.transports.File({
      filename: path.join('logs', 'error.log'),
      level: 'error',
      format: logFormat
    })
  );
}

// Tạo instance logger
const logger = winston.createLogger({
  level: config.env === 'production' ? 'info' : 'debug',
  levels: winston.config.npm.levels,
  format: logFormat,
  transports
});

module.exports = logger;