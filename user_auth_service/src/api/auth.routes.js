const express = require('express');
const authController = require('./auth.controller');
const { authenticate } = require('../infrastructure/middlewares/auth.middleware');

const router = express.Router();

/**
 * @route POST /api/v1/auth/login
 * @desc Đăng nhập và trả về token
 * @access Public
 */
router.post('/login', authController.login);

/**
 * @route POST /api/v1/auth/refresh-token
 * @desc Làm mới access token
 * @access Public
 */
router.post('/refresh-token', authController.refreshToken);

/**
 * @route POST /api/v1/auth/logout
 * @desc Đăng xuất và vô hiệu hóa token
 * @access Private
 */
router.post('/logout', authenticate, authController.logout);

/**
 * @route POST /api/v1/auth/logout-all
 * @desc Đăng xuất khỏi tất cả thiết bị
 * @access Private
 */
router.post('/logout-all', authenticate, authController.logoutAll);

/**
 * @route GET /api/v1/auth/me
 * @desc Lấy thông tin người dùng hiện tại
 * @access Private
 */
router.get('/me', authenticate, authController.me);

module.exports = router;