const morgan = require('morgan');
const logger = require('../logging/logger');

// Tạo stream để ghi log thông qua winston
const stream = {
  write: message => logger.http(message.trim())
};

// Format log tùy chỉnh
const format = ':remote-addr :method :url :status :res[content-length] - :response-time ms';

// Tạo middleware morgan với winston logger
const httpLogger = morgan(format, { stream });

module.exports = httpLogger;