const express = require('express');
const roleController = require('./role.controller');
const { authenticate, hasPermission } = require('../infrastructure/middlewares/auth.middleware');

const router = express.Router();

/**
 * @route GET /api/v1/roles
 * @desc Lấy danh sách vai trò
 * @access Private (Yêu cầu quyền đọc vai trò)
 */
router.get(
  '/',
  authenticate,
  hasPermission('role', 'read'),
  roleController.getRoles
);

/**
 * @route GET /api/v1/roles/:id
 * @desc Lấy chi tiết vai trò
 * @access Private (Yêu cầu quyền đọc vai trò)
 */
router.get(
  '/:id',
  authenticate,
  hasPermission('role', 'read'),
  roleController.getRoleById
);

/**
 * @route POST /api/v1/roles
 * @desc Tạo vai trò mới
 * @access Private (Yêu cầu quyền tạo vai trò)
 */
router.post(
  '/',
  authenticate,
  hasPermission('role', 'create'),
  roleController.createRole
);

/**
 * @route PUT /api/v1/roles/:id
 * @desc Cập nhật vai trò
 * @access Private (Yêu cầu quyền cập nhật vai trò)
 */
router.put(
  '/:id',
  authenticate,
  hasPermission('role', 'update'),
  roleController.updateRole
);

/**
 * @route DELETE /api/v1/roles/:id
 * @desc Xóa vai trò
 * @access Private (Yêu cầu quyền xóa vai trò)
 */
router.delete(
  '/:id',
  authenticate,
  hasPermission('role', 'delete'),
  roleController.deleteRole
);

/**
 * @route POST /api/v1/roles/:id/permissions
 * @desc Thêm quyền cho vai trò
 * @access Private (Yêu cầu quyền cập nhật vai trò)
 */
router.post(
  '/:id/permissions',
  authenticate,
  hasPermission('role', 'update'),
  roleController.addPermissionToRole
);

/**
 * @route DELETE /api/v1/roles/:id/permissions/:permissionId
 * @desc Xóa quyền khỏi vai trò
 * @access Private (Yêu cầu quyền cập nhật vai trò)
 */
router.delete(
  '/:id/permissions/:permissionId',
  authenticate,
  hasPermission('role', 'update'),
  roleController.removePermissionFromRole
);

module.exports = router;