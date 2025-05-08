const authService = require('../core/auth/auth.service');

/**
 * Xử lý yêu cầu đăng nhập
 */
const login = async (req, res) => {
  try {
    const { email, password } = req.body;
    
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password required' });
    }
    
    const authData = await authService.login(email, password);
    
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

module.exports = {
  login,
  refreshToken,
  logout,
  logoutAll,
  me
};