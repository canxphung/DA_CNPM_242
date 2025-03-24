const jwt = require('jsonwebtoken');

// Middleware xác thực token JWT
const authMiddleware = (requiredRoles = []) => {
  return (req, res, next) => {
    // Kiểm tra header Authorization
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Unauthorized - No token provided' });
    }

    // Lấy token
    const token = authHeader.split(' ')[1];

    try {
      // Xác thực token
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      
      // Gán thông tin user vào request
      req.user = decoded;
      
      // Kiểm tra role nếu cần
      if (requiredRoles.length > 0) {
        const hasRequiredRole = requiredRoles.some(role => 
          decoded.roles && decoded.roles.includes(role)
        );
        
        if (!hasRequiredRole) {
          return res.status(403).json({ 
            error: 'Forbidden - Insufficient permissions' 
          });
        }
      }
      
      next();
    } catch (error) {
      if (error.name === 'TokenExpiredError') {
        return res.status(401).json({ error: 'Unauthorized - Token expired' });
      }
      
      return res.status(401).json({ error: 'Unauthorized - Invalid token' });
    }
  };
};

module.exports = authMiddleware;