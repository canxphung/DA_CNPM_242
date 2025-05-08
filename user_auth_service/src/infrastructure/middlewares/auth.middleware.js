const { verifyToken } = require('../../core/auth/jwt.utils');
const authorizationService = require('../../core/auth/authorization.service');
const User = require('../../core/users/user.model');

/**
 * Middleware xác thực người dùng qua JWT
 */
const authenticate = (req, res, next) => {
  // Lấy token từ header
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  
  const token = authHeader.split(' ')[1];
  
  // Xác thực token
  const decoded = verifyToken(token);
  
  if (!decoded || decoded.type !== 'access') {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
  
  // Lưu thông tin người dùng vào request
  req.user = {
    id: decoded.sub,
    email: decoded.email,
    role: decoded.role
  };
  
  next();
};

/**
 * Middleware kiểm tra vai trò của người dùng
 * @param {String[]} roles - Danh sách các vai trò được phép truy cập
 */
const hasRoles = (roles = []) => {
  return async (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }
    
    try {
      // Lấy thông tin người dùng với vai trò
      const user = await User.findById(req.user.id).populate('roles');
      
      if (!user) {
        return res.status(401).json({ error: 'User not found' });
      }
      
      // Kiểm tra người dùng có vai trò nào trong danh sách không
      const hasRole = roles.some(role => user.hasRole(role));
      
      if (!hasRole) {
        return res.status(403).json({ error: 'Access forbidden' });
      }
      
      next();
    } catch (error) {
      console.error('Role check error:', error);
      return res.status(500).json({ error: 'Authorization check failed' });
    }
  };
};

/**
 * Middleware kiểm tra quyền của người dùng
 * @param {String} resource - Tài nguyên cần kiểm tra
 * @param {String} action - Hành động cần kiểm tra
 */
const hasPermission = (resource, action) => {
  return async (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }
    
    try {
      // Kiểm tra quyền
      const hasPermission = await authorizationService.checkUserPermission(
        req.user.id,
        resource,
        action
      );
      
      if (!hasPermission) {
        return res.status(403).json({ error: 'Access forbidden' });
      }
      
      next();
    } catch (error) {
      console.error('Permission check error:', error);
      return res.status(500).json({ error: 'Authorization check failed' });
    }
  };
};

/**
 * Middleware kiểm tra quyền hoặc quyền sở hữu
 * @param {String} resource - Tài nguyên cần kiểm tra
 * @param {String} action - Hành động cần kiểm tra
 * @param {Function} getOwnerId - Hàm lấy ID chủ sở hữu từ request
 */
const hasPermissionOrOwnership = (resource, action, getOwnerId) => {
  return async (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }
    
    try {
      // Kiểm tra quyền
      const hasPermission = await authorizationService.checkUserPermission(
        req.user.id,
        resource,
        action
      );
      
      // Nếu có quyền, cho phép truy cập
      if (hasPermission) {
        return next();
      }
      
      // Nếu không có quyền, kiểm tra quyền sở hữu
      const ownerId = getOwnerId(req);
      
      if (ownerId && req.user.id === ownerId.toString()) {
        return next();
      }
      
      return res.status(403).json({ error: 'Access forbidden' });
    } catch (error) {
      console.error('Permission check error:', error);
      return res.status(500).json({ error: 'Authorization check failed' });
    }
  };
};

module.exports = {
  authenticate,
  hasRoles,
  hasPermission,
  hasPermissionOrOwnership
};