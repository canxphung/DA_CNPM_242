const User = require('../users/user.model');
const { generateAccessToken, generateRefreshToken, verifyToken } = require('./jwt.utils');
const config = require('../../infrastructure/config');

/**
 * Dịch vụ xác thực người dùng
 */
class AuthService {
  
  /**
   * Đăng nhập người dùng
   * @param {String} email - Email người dùng
   * @param {String} password - Mật khẩu người dùng
   * @returns {Object} Thông tin người dùng và tokens
   */
  async login(email, password) {
    // Tìm người dùng theo email
    const user = await User.findOne({ email, isActive: true });
    
    if (!user) {
      throw new Error('Invalid credentials');
    }
    
    // Kiểm tra mật khẩu
    const isPasswordValid = await user.comparePassword(password);
    
    if (!isPasswordValid) {
      throw new Error('Invalid credentials');
    }
    
    // Tạo access và refresh token
    const accessToken = generateAccessToken(user);
    const refreshToken = generateRefreshToken(user);
    
    // Lưu refresh token vào database
    const refreshExpiresIn = config.jwt.refreshExpiresIn.replace(/[^0-9]/g, '');
    await user.addRefreshToken(refreshToken, refreshExpiresIn);
    
    return {
      user: {
        id: user._id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role
      },
      tokens: {
        accessToken,
        refreshToken,
        expiresIn: config.jwt.expiresIn
      }
    };
  }
  
  /**
   * Làm mới access token bằng refresh token
   * @param {String} refreshToken - Refresh token
   * @returns {Object} Access token mới
   */
  async refreshToken(refreshToken) {
    // Xác thực refresh token
    const decoded = verifyToken(refreshToken);
    
    if (!decoded || decoded.type !== 'refresh') {
      throw new Error('Invalid refresh token');
    }
    
    // Tìm người dùng
    const user = await User.findById(decoded.sub);
    
    if (!user || !user.isActive || !user.hasValidRefreshToken(refreshToken)) {
      throw new Error('Invalid refresh token');
    }
    
    // Tạo access token mới
    const accessToken = generateAccessToken(user);
    
    return {
      accessToken,
      expiresIn: config.jwt.expiresIn
    };
  }
  
  /**
   * Đăng xuất người dùng (vô hiệu hóa refresh token)
   * @param {String} userId - ID người dùng
   * @param {String} refreshToken - Refresh token cần vô hiệu hóa
   */
  async logout(userId, refreshToken) {
    const user = await User.findById(userId);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    // Xóa refresh token
    await user.removeRefreshToken(refreshToken);
    
    return { success: true };
  }
  
  /**
   * Đăng xuất khỏi tất cả thiết bị
   * @param {String} userId - ID người dùng
   */
  async logoutAll(userId) {
    const user = await User.findById(userId);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    // Xóa tất cả refresh token
    await user.removeAllRefreshTokens();
    
    return { success: true };
  }
}

module.exports = new AuthService();