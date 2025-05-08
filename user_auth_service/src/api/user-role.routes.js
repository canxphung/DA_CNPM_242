const express = require('express');
const userRoleController = require('./user-role.controller');
const { authenticate, hasPermission } = require('../infrastructure/middlewares/auth.middleware');

const router = express.Router();

/**
 * @route POST /api/v1/users/:userId/roles
 * @desc Gán vai trò cho người dùng
 * @access Private (Yêu cầu quyền quản lý người dùng)
 */
router.post(
  '/:userId/roles',
  authenticate,
  hasPermission('user', 'manage'),
  userRoleController.assignRoleToUser
);

/**
 * @route DELETE /api/v1/users/:userId/roles/:roleId
 * @desc Xóa vai trò khỏi người dùng
 * @access Private (Yêu cầu quyền quản lý người dùng)
 */
router.delete(
  '/:userId/roles/:roleId',
  authenticate,
  hasPermission('user', 'manage'),
  userRoleController.removeRoleFromUser
);

/**
 * @route POST /api/v1/users/:userId/permissions
 * @desc Thêm quyền tùy chỉnh cho người dùng
 * @access Private (Yêu cầu quyền quản lý người dùng)
 */
router.post(
  '/:userId/permissions',
  authenticate,
  hasPermission('user', 'manage'),
  userRoleController.addCustomPermissionToUser
);

/**
 * @route DELETE /api/v1/users/:userId/permissions/:permissionId
 * @desc Xóa quyền tùy chỉnh khỏi người dùng
 * @access Private (Yêu cầu quyền quản lý người dùng)
 */
router.delete(
  '/:userId/permissions/:permissionId',
  authenticate,
  hasPermission('user', 'manage'),
  userRoleController.removeCustomPermissionFromUser
);

/**
 * @route GET /api/v1/users/:userId/check-permission
 * @desc Kiểm tra quyền của người dùng
 * @access Private (Yêu cầu quyền quản lý người dùng)
 */
router.get(
  '/:userId/check-permission',
  authenticate,
  hasPermission('user', 'manage'),
  userRoleController.checkPermission
);

module.exports = router;