const express = require('express');
const userController = require('./user.controller');
const { 
    createUserRules, 
    updateUserRules, 
    changePasswordRules 
  } = require('../infrastructure/middlewares/validation.middleware');
const { authenticate, hasPermission, hasPermissionOrOwnership } = require('../infrastructure/middlewares/auth.middleware');

const router = express.Router();

/**
 * @route GET /api/v1/users
 * @desc Lấy danh sách người dùng
 * @access Private (Yêu cầu quyền đọc người dùng)
 */
router.get(
  '/',
  authenticate,
  hasPermission('user', 'read'),
  userController.getUsers
);

/**
 * @route GET /api/v1/users/me
 * @desc Lấy thông tin người dùng hiện tại
 * @access Private
 */
router.get(
  '/me',
  authenticate,
  userController.getCurrentUser
);

/**
 * @route GET /api/v1/users/:id
 * @desc Lấy thông tin chi tiết người dùng
 * @access Private (Yêu cầu quyền đọc người dùng hoặc là chính người dùng đó)
 */
router.get(
  '/:id',
  authenticate,
  hasPermissionOrOwnership('user', 'read', req => req.params.id),
  userController.getUserById
);

/**
 * @route POST /api/v1/users
 * @desc Tạo người dùng mới
 * @access Private (Yêu cầu quyền tạo người dùng)
 */
router.post(
    '/',
  authenticate,
  hasPermission('user', 'create'),
  createUserRules, // Đã sửa thành createUserRules
  userController.createUser
);

/**
 * @route PUT /api/v1/users/:id
 * @desc Cập nhật thông tin người dùng
 * @access Private (Yêu cầu quyền cập nhật người dùng hoặc là chính người dùng đó)
 */
router.put(
  '/:id',
  authenticate,
  hasPermissionOrOwnership('user', 'update', req => req.params.id),
  updateUserRules,
  userController.updateUser
);

/**
 * @route POST /api/v1/users/change-password
 * @desc Thay đổi mật khẩu người dùng
 * @access Private
 */
router.post(
  '/change-password',
  authenticate,
  changePasswordRules,
  userController.changePassword
);

/**
 * @route PUT /api/v1/users/:id/deactivate
 * @desc Vô hiệu hóa tài khoản người dùng
 * @access Private (Yêu cầu quyền quản lý người dùng)
 */
router.put(
  '/:id/deactivate',
  authenticate,
  hasPermission('user', 'manage'),
  userController.deactivateUser
);

/**
 * @route PUT /api/v1/users/:id/activate
 * @desc Kích hoạt tài khoản người dùng
 * @access Private (Yêu cầu quyền quản lý người dùng)
 */
router.put(
  '/:id/activate',
  authenticate,
  hasPermission('user', 'manage'),
  userController.activateUser
);

/**
 * @route DELETE /api/v1/users/:id
 * @desc Xóa người dùng
 * @access Private (Yêu cầu quyền xóa người dùng)
 */
router.delete(
  '/:id',
  authenticate,
  hasPermission('user', 'delete'),
  userController.deleteUser
);

module.exports = router;