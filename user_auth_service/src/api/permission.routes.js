const express = require('express');
const permissionController = require('./permission.controller');
const { authenticate, hasPermission } = require('../infrastructure/middlewares/auth.middleware');

const router = express.Router();

/**
 * @route GET /api/v1/permissions
 * @desc Lấy danh sách quyền
 * @access Private (Yêu cầu quyền đọc quyền)
 */
router.get(
  '/',
  authenticate,
  hasPermission('permission', 'read'),
  permissionController.getPermissions
);

/**
 * @route POST /api/v1/permissions
 * @desc Tạo quyền mới
 * @access Private (Yêu cầu quyền tạo quyền)
 */
router.post(
  '/',
  authenticate,
  hasPermission('permission', 'create'),
  permissionController.createPermission
);

/**
 * @route PUT /api/v1/permissions/:id
 * @desc Cập nhật quyền
 * @access Private (Yêu cầu quyền cập nhật quyền)
 */
router.put(
  '/:id',
  authenticate,
  hasPermission('permission', 'update'),
  permissionController.updatePermission
);

/**
 * @route DELETE /api/v1/permissions/:id
 * @desc Xóa quyền
 * @access Private (Yêu cầu quyền xóa quyền)
 */
router.delete(
  '/:id',
  authenticate,
  hasPermission('permission', 'delete'),
  permissionController.deletePermission
);

module.exports = router;