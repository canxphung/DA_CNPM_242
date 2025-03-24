// Cấu hình API Gateway - định nghĩa các service và route
module.exports = {
    // Danh sách các services cần route tới
    services: {
      data_processing: {
        url: process.env.DATA_PROCESSING_URL || 'http://data-processing-service:3008',
        timeout: 5000
      },
      storage: {
        url: process.env.STORAGE_URL || 'http://storage-service:3009',
        timeout: 5000
      },
      environment: {
        url: process.env.ENVIRONMENT_URL || 'http://environment-service:3002',
        timeout: 3000
      },
      irrigation: {
        url: process.env.IRRIGATION_URL || 'http://irrigation-service:3001',
        timeout: 3000
      },
      fertigation: {
        url: process.env.FERTIGATION_URL || 'http://fertigation-service:3004',
        timeout: 3000
      },
      scheduling: {
        url: process.env.SCHEDULING_URL || 'http://scheduling-service:3003',
        timeout: 5000
      },
      analytics: {
        url: process.env.ANALYTICS_URL || 'http://analytics-service:3005',
        timeout: 10000
      },
      ai: {
        url: process.env.AI_URL || 'http://ai-service:3006',
        timeout: 15000
      },
      auth: {
        url: process.env.AUTH_URL || 'http://auth-service:3007',
        timeout: 3000
      }
    },
    
    // Cấu hình các routes
    routes: [
      // Auth routes - không yêu cầu xác thực
      {
        path: '/api/auth/*',
        service: 'auth',
        protected: false,
        stripPath: true,
        rateLimit: {
          windowMs: 15 * 60 * 1000, // 15 phút
          max: 30 // 30 request trong 15 phút
        }
      },
      
      // Data processing routes
      {
        path: '/api/data/*',
        service: 'data_processing',
        protected: true,
        stripPath: true,
        roles: ['user', 'admin', 'device']
      },
      
      // Storage routes
      {
        path: '/api/storage/*',
        service: 'storage',
        protected: true,
        stripPath: true,
        roles: ['user', 'admin']
      },
      
      // Environment routes
      {
        path: '/api/environment/*',
        service: 'environment',
        protected: true,
        stripPath: true,
        roles: ['user', 'admin', 'device']
      },
      
      // Irrigation routes
      {
        path: '/api/irrigation/*',
        service: 'irrigation',
        protected: true,
        stripPath: true,
        roles: ['admin', 'operator']
      },
      
      // Fertigation routes
      {
        path: '/api/fertigation/*',
        service: 'fertigation',
        protected: true,
        stripPath: true,
        roles: ['admin', 'operator']
      },
      
      // Scheduling routes
      {
        path: '/api/schedules/*',
        service: 'scheduling',
        protected: true,
        stripPath: true,
        roles: ['admin', 'operator']
      },
      
      // Analytics routes
      {
        path: '/api/analytics/*',
        service: 'analytics',
        protected: true,
        stripPath: true,
        roles: ['admin', 'analyst', 'user']
      },
      
      // AI routes
      {
        path: '/api/ai/*',
        service: 'ai',
        protected: true,
        stripPath: true,
        roles: ['admin', 'analyst']
      }
    ]
  };