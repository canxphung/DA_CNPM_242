const { body, param, query, validationResult } = require('express-validator');

/**
 * Middleware kiểm tra lỗi validation
 */
const validate = (req, res, next) => {
  const errors = validationResult(req);
  
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }
  
  next();
};

/**
 * Validation rules cho tạo người dùng
 */
const createUserRules = [
  body('email')
    .isEmail().withMessage('Email không hợp lệ')
    .normalizeEmail()
    .notEmpty().withMessage('Email là bắt buộc'),
  
  body('password')
    .isLength({ min: 8 }).withMessage('Mật khẩu phải có ít nhất 8 ký tự')
    .matches(/[A-Z]/).withMessage('Mật khẩu phải có ít nhất 1 chữ hoa')
    .matches(/[a-z]/).withMessage('Mật khẩu phải có ít nhất 1 chữ thường')
    .matches(/[0-9]/).withMessage('Mật khẩu phải có ít nhất 1 số')
    .matches(/[!@#$%^&*]/).withMessage('Mật khẩu phải có ít nhất 1 ký tự đặc biệt'),
  
  body('firstName')
    .notEmpty().withMessage('Tên là bắt buộc')
    .isString().withMessage('Tên phải là chuỗi')
    .trim(),
  
  body('lastName')
    .notEmpty().withMessage('Họ là bắt buộc')
    .isString().withMessage('Họ phải là chuỗi')
    .trim(),
  
  body('role')
    .optional()
    .isIn(['user', 'admin', 'manager']).withMessage('Vai trò không hợp lệ'),
  
  body('phoneNumber')
    .optional()
    .isMobilePhone().withMessage('Số điện thoại không hợp lệ'),
  
  validate
];

/**
 * Validation rules cho cập nhật người dùng
 */
const updateUserRules = [
  param('id')
    .isMongoId().withMessage('ID người dùng không hợp lệ'),
  
  body('email')
    .optional()
    .isEmail().withMessage('Email không hợp lệ')
    .normalizeEmail(),
  
  body('firstName')
    .optional()
    .isString().withMessage('Tên phải là chuỗi')
    .trim(),
  
  body('lastName')
    .optional()
    .isString().withMessage('Họ phải là chuỗi')
    .trim(),
  
  body('role')
    .optional()
    .isIn(['user', 'admin', 'manager']).withMessage('Vai trò không hợp lệ'),
  
  body('phoneNumber')
    .optional()
    .isMobilePhone().withMessage('Số điện thoại không hợp lệ'),
  
  // Không cho phép cập nhật mật khẩu qua API này
  body('password')
    .not().exists().withMessage('Không thể cập nhật mật khẩu thông qua endpoint này'),
  
  validate
];

/**
 * Validation rules cho thay đổi mật khẩu
 */
const changePasswordRules = [
  body('currentPassword')
    .notEmpty().withMessage('Mật khẩu hiện tại là bắt buộc'),
  
  body('newPassword')
    .isLength({ min: 8 }).withMessage('Mật khẩu mới phải có ít nhất 8 ký tự')
    .matches(/[A-Z]/).withMessage('Mật khẩu mới phải có ít nhất 1 chữ hoa')
    .matches(/[a-z]/).withMessage('Mật khẩu mới phải có ít nhất 1 chữ thường')
    .matches(/[0-9]/).withMessage('Mật khẩu mới phải có ít nhất 1 số')
    .matches(/[!@#$%^&*]/).withMessage('Mật khẩu mới phải có ít nhất 1 ký tự đặc biệt')
    .custom((value, { req }) => {
      if (value === req.body.currentPassword) {
        throw new Error('Mật khẩu mới phải khác mật khẩu hiện tại');
      }
      return true;
    }),
  
  validate
];

/**
 * Validation rules cho đăng nhập
 */
const loginRules = [
  body('email')
    .isEmail().withMessage('Email không hợp lệ')
    .normalizeEmail()
    .notEmpty().withMessage('Email là bắt buộc'),
  
  body('password')
    .notEmpty().withMessage('Mật khẩu là bắt buộc'),
  
  validate
];

/**
 * Validation rules cho làm mới token
 */
const refreshTokenRules = [
  body('refreshToken')
    .notEmpty().withMessage('Refresh token là bắt buộc'),
  
  validate
];

/**
 * Validation rules cho tạo vai trò
 */
const createRoleRules = [
  body('name')
    .notEmpty().withMessage('Tên vai trò là bắt buộc')
    .isString().withMessage('Tên vai trò phải là chuỗi')
    .isLength({ min: 3 }).withMessage('Tên vai trò phải có ít nhất 3 ký tự')
    .trim(),
  
  body('description')
    .notEmpty().withMessage('Mô tả vai trò là bắt buộc')
    .isString().withMessage('Mô tả vai trò phải là chuỗi')
    .trim(),
  
  body('permissions')
    .optional()
    .isArray().withMessage('Danh sách quyền phải là mảng'),
  
  body('permissions.*')
    .optional()
    .isMongoId().withMessage('ID quyền không hợp lệ'),
  
  validate
];

/**
 * Validation rules cho tạo quyền
 */
const createPermissionRules = [
  body('name')
    .notEmpty().withMessage('Tên quyền là bắt buộc')
    .isString().withMessage('Tên quyền phải là chuỗi')
    .trim(),
  
  body('description')
    .notEmpty().withMessage('Mô tả quyền là bắt buộc')
    .isString().withMessage('Mô tả quyền phải là chuỗi')
    .trim(),
  
  body('resource')
    .notEmpty().withMessage('Tài nguyên là bắt buộc')
    .isString().withMessage('Tài nguyên phải là chuỗi')
    .trim(),
  
  body('action')
    .notEmpty().withMessage('Hành động là bắt buộc')
    .isIn(['create', 'read', 'update', 'delete', 'manage']).withMessage('Hành động không hợp lệ'),
  
  validate
];

/**
 * Validation rules cho gán vai trò cho người dùng
 */
const assignRoleRules = [
  param('userId')
    .isMongoId().withMessage('ID người dùng không hợp lệ'),
  
  body('roleId')
    .notEmpty().withMessage('ID vai trò là bắt buộc')
    .isMongoId().withMessage('ID vai trò không hợp lệ'),
  
  validate
];

/**
 * Validation rules cho thêm quyền vào vai trò
 */
const addPermissionToRoleRules = [
  param('id')
    .isMongoId().withMessage('ID vai trò không hợp lệ'),
  
  body('permissionId')
    .notEmpty().withMessage('ID quyền là bắt buộc')
    .isMongoId().withMessage('ID quyền không hợp lệ'),
  
  validate
];

module.exports = {
  validate,
  createUserRules,
  updateUserRules,
  changePasswordRules,
  loginRules,
  refreshTokenRules,
  createRoleRules,
  createPermissionRules,
  assignRoleRules,
  addPermissionToRoleRules
};