const express = require('express');
const actuator = require('express-actuator');
const os = require('os');
const { authenticate, hasPermission } = require('../infrastructure/middlewares/auth.middleware');

const router = express.Router();

// Cấu hình express-actuator
const actuatorOptions = {
  basePath: '/management', // Base URL for the actuator endpoints
  infoGitMode: 'simple', // Cách hiển thị thông tin Git
  infoBuildOptions: {
    app: {
      name: 'user-auth-service',
      description: 'User Authentication and Authorization Service',
      version: '1.0.0'
    }
  }
};

// Sử dụng middleware actuator
router.use(actuator(actuatorOptions));

/**
 * @route GET /api/v1/monitoring/health
 * @desc Kiểm tra trạng thái của service
 * @access Public
 */
router.get('/health', (req, res) => {
  res.status(200).json({
    status: 'UP',
    timestamp: new Date().toISOString(),
    service: 'user-auth-service'
  });
});

/**
 * @route GET /api/v1/monitoring/system
 * @desc Lấy thông tin hệ thống chi tiết
 * @access Private (Admin only)
 */
router.get('/system', authenticate, hasPermission('system', 'read'), (req, res) => {
  const systemInfo = {
    hostname: os.hostname(),
    platform: os.platform(),
    architecture: os.arch(),
    cpus: os.cpus().length,
    memory: {
      totalMem: `${Math.round(os.totalmem() / (1024 * 1024 * 1024))} GB`,
      freeMem: `${Math.round(os.freemem() / (1024 * 1024 * 1024))} GB`,
      usedMemPercent: `${Math.round((1 - os.freemem() / os.totalmem()) * 100)}%`
    },
    uptime: `${Math.floor(os.uptime() / 3600)} hours, ${Math.floor((os.uptime() % 3600) / 60)} minutes`,
    processUptime: `${Math.floor(process.uptime() / 3600)} hours, ${Math.floor((process.uptime() % 3600) / 60)} minutes`,
    load: os.loadavg()
  };
  
  res.status(200).json(systemInfo);
});

module.exports = router;