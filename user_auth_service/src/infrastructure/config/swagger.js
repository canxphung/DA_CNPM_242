const swaggerJsdoc = require('swagger-jsdoc');
const config = require('./index');

// Cấu hình Swagger
const swaggerOptions = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'User & Auth Service API',
      version: '1.0.0',
      description: 'API Documentation for User & Auth Service',
      contact: {
        name: 'API Support',
        email: 'support@example.com'
      }
    },
    servers: [
      {
        url: `http://localhost:${config.port}${config.apiPrefix}`,
        description: 'Development server'
      }
    ],
    components: {
      securitySchemes: {
        BearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT'
        }
      }
    },
    security: [
      {
        BearerAuth: []
      }
    ]
  },
  // Đường dẫn đến các file chứa JSDoc annotations
  apis: [
    './src/api/*.routes.js',
    './src/api/*.js',
    './src/core/**/*.model.js'
  ]
};

// Khởi tạo swagger specification
const swaggerSpec = swaggerJsdoc(swaggerOptions);

module.exports = swaggerSpec;