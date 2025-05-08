const dotenv = require('dotenv');
const path = require('path');

// Load .env file dựa vào môi trường
const envFile = process.env.NODE_ENV === 'production' ? '.env.production' : '.env';
dotenv.config({ path: path.resolve(process.cwd(), envFile) });

// Cấu hình môi trường
const config = {
  env: process.env.NODE_ENV || 'development',
  host: process.env.HOST || 'localhost',
  port: process.env.PORT || 3001,
  apiPrefix: process.env.API_PREFIX || '/api/v1',
  
  // JWT config
  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: process.env.JWT_EXPIRATION || '1d',
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRATION || '7d'
  },
  
  // Database config
  db: {
    mongo: {
      uri: process.env.MONGODB_URI
    },
    redis: {
      host: process.env.REDIS_HOST || 'localhost',
      port: process.env.REDIS_PORT || 6379,
      password: process.env.REDIS_PASSWORD || '',
      uri: process.env.REDIS_URI
    }
  },
  
  // API Gateway config
  apiGateway: {
    enabled: process.env.API_GATEWAY_ENABLED === 'true',
    url: process.env.API_GATEWAY_URL || 'http://localhost:8000'
  },
  
  // Service Registry config
  serviceRegistry: {
    enabled: process.env.SERVICE_REGISTRY_ENABLED === 'true',
    url: process.env.SERVICE_REGISTRY_URL || 'http://localhost:3000'
  },
  
  // CORS config
  cors: {
    origin: process.env.CORS_ORIGIN ? process.env.CORS_ORIGIN.split(',') : '*',
    methods: 'GET,HEAD,PUT,PATCH,POST,DELETE',
    credentials: true,
    preflightContinue: false,
    optionsSuccessStatus: 204
  },
  
  // Rate limiting
  rateLimit: {
    windowMs: process.env.RATE_LIMIT_WINDOW_MS || 15 * 60 * 1000, // 15 phút
    max: process.env.RATE_LIMIT_MAX || 100 // 100 request
  }
};

module.exports = config;