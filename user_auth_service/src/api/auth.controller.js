const authService = require('../core/auth/auth.service');
const logger = require('../infrastructure/logging/logger');
const userService = require('../core/users/user.service');
const { generateAccessToken, generateRefreshToken } = require('../core/auth/jwt.utils');
const config = require('../infrastructure/config/index');
/**
 * Xử lý yêu cầu đăng nhập
 */
const login = async (req, res) => {
  logger.info('[AUTH CONTROLLER] Login endpoint hit.');
  logger.info('[AUTH CONTROLLER] Request body for login:', req.body);
  logger.info('[AUTH CONTROLLER] Request headers for login:', req.headers); // Kiểm tra headers
  try {
    const { email, password } = req.body;
    
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password required' });
    }
    
    const authData = await authService.login(email, password);
    console.log('[AUTH CONTROLLER] Login response data:', authData);

    logger.info('Login response data:', authData);
    return res.status(200).json(authData);
  } catch (error) {
    console.error('Login error:', error);
    
    if (error.message === 'Invalid credentials') {
      return res.status(401).json({ error: 'Invalid email or password' });
    }
    
    return res.status(500).json({ error: 'Authentication failed' });
  }
};

/**
 * Xử lý yêu cầu làm mới token
 */
const refreshToken = async (req, res) => {
  try {
    const { refreshToken } = req.body;
    
    if (!refreshToken) {
      return res.status(400).json({ error: 'Refresh token required' });
    }
    
    const tokenData = await authService.refreshToken(refreshToken);
    
    return res.status(200).json(tokenData);
  } catch (error) {
    console.error('Refresh token error:', error);
    return res.status(401).json({ error: 'Invalid refresh token' });
  }
};

/**
 * Xử lý yêu cầu đăng xuất
 */
const logout = async (req, res) => {
  try {
    const { refreshToken } = req.body;
    const userId = req.user.id;
    
    if (!refreshToken) {
      return res.status(400).json({ error: 'Refresh token required' });
    }
    
    await authService.logout(userId, refreshToken);
    
    return res.status(200).json({ message: 'Successfully logged out' });
  } catch (error) {
    console.error('Logout error:', error);
    return res.status(500).json({ error: 'Logout failed' });
  }
};

/**
 * Xử lý yêu cầu đăng xuất khỏi tất cả thiết bị
 */
const logoutAll = async (req, res) => {
  try {
    const userId = req.user.id;
    
    await authService.logoutAll(userId);
    
    return res.status(200).json({ message: 'Successfully logged out from all devices' });
  } catch (error) {
    console.error('Logout all error:', error);
    return res.status(500).json({ error: 'Logout failed' });
  }
};

/**
 * Trả về thông tin người dùng hiện tại
 */
const me = async (req, res) => {
  return res.status(200).json({
    id: req.user.id,
    email: req.user.email,
    role: req.user.role
  });
};

const register = async (req, res) => {
  try {
    const { email, password, firstName, lastName } = req.body;
    
    // Validation cơ bản
    if (!email || !password || !firstName || !lastName) {
      return res.status(400).json({ 
        error: 'All fields are required' 
      });
    }
    
    // Kiểm tra email đã tồn tại
    const existingUser = await userService.getUserByEmail(email);
    if (existingUser) {
      return res.status(400).json({ 
        error: 'Email already registered' 
      });
    }
    
    // Tạo user mới với role mặc định là 'user'
    const userData = {
      email,
      password,
      firstName,
      lastName,
      role: 'user',        // ← Role mặc định
      isActive: true
    };
    
    const user = await userService.createUser(userData);
    
    // Tự động đăng nhập sau khi đăng ký
    const accessToken = generateAccessToken(user);
    const refreshToken = generateRefreshToken(user);
    
    // Lưu refresh token
    await user.addRefreshToken(refreshToken);
    
    return res.status(201).json({
      message: 'Registration successful',
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
    });
    
  } catch (error) {
    console.error('Registration error:', error);
    return res.status(500).json({ 
      error: 'Registration failed' 
    });
  }
};

module.exports = {
  login,
  register,
  refreshToken,
  logout,
  logoutAll,
  me
};