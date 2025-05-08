const jwt = require('jsonwebtoken');
const config = require('../../infrastructure/config');

/**
 * Tạo access token từ thông tin người dùng
 * @param {Object} user - Thông tin người dùng
 * @returns {String} Token JWT
 */
const generateAccessToken = (user) => {
  const payload = {
    sub: user._id,
    email: user.email,
    role: user.role,
    type: 'access'
  };
  
  return jwt.sign(payload, config.jwt.secret, { expiresIn: config.jwt.expiresIn });
};

/**
 * Tạo refresh token từ thông tin người dùng
 * @param {Object} user - Thông tin người dùng
 * @returns {String} Refresh token
 */
const generateRefreshToken = (user) => {
  const payload = {
    sub: user._id,
    type: 'refresh'
  };
  
  return jwt.sign(payload, config.jwt.secret, { expiresIn: config.jwt.refreshExpiresIn });
};

/**
 * Xác thực token JWT
 * @param {String} token - Token JWT cần xác thực
 * @returns {Object} Payload đã giải mã hoặc null nếu không hợp lệ
 */
const verifyToken = (token) => {
  try {
    return jwt.verify(token, config.jwt.secret);
  } catch (error) {
    return null;
  }
};

module.exports = {
  generateAccessToken,
  generateRefreshToken,
  verifyToken
};