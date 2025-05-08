const authorizationService = require('../core/auth/authorization.service');

/**
 * Gán vai trò cho người dùng
 */
const assignRoleToUser = async (req, res) => {
  try {
    const { roleId } = req.body;
    
    if (!roleId) {
      return res.status(400).json({ error: 'Role ID is required' });
    }
    
    const user = await authorizationService.assignRoleToUser(
      req.params.userId,
      roleId
    );
    
    return res.status(200).json({
      message: 'Role assigned successfully',
      user: {
        id: user._id,
        email: user.email,
        roles: user.roles
      }
    });
  } catch (error) {
    console.error('Error assigning role to user:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    if (error.message === 'Role not found') {
      return res.status(404).json({ error: 'Role not found' });
    }
    
    if (error.message === 'Role already assigned to user') {
      return res.status(400).json({ error: 'Role already assigned to user' });
    }
    
    return res.status(500).json({ error: 'Failed to assign role to user' });
  }
};

/**
 * Xóa vai trò khỏi người dùng
 */
const removeRoleFromUser = async (req, res) => {
  try {
    const user = await authorizationService.removeRoleFromUser(
      req.params.userId,
      req.params.roleId
    );
    
    return res.status(200).json({
      message: 'Role removed successfully',
      user: {
        id: user._id,
        email: user.email,
        roles: user.roles
      }
    });
  } catch (error) {
    console.error('Error removing role from user:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    return res.status(500).json({ error: 'Failed to remove role from user' });
  }
};

/**
 * Thêm quyền tùy chỉnh cho người dùng
 */
const addCustomPermissionToUser = async (req, res) => {
  try {
    const { permissionId } = req.body;
    
    if (!permissionId) {
      return res.status(400).json({ error: 'Permission ID is required' });
    }
    
    const user = await authorizationService.addCustomPermissionToUser(
      req.params.userId,
      permissionId
    );
    
    return res.status(200).json({
      message: 'Custom permission added successfully',
      user: {
        id: user._id,
        email: user.email,
        customPermissions: user.customPermissions
      }
    });
  } catch (error) {
    console.error('Error adding custom permission to user:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    if (error.message === 'Permission not found') {
      return res.status(404).json({ error: 'Permission not found' });
    }
    
    if (error.message === 'Permission already assigned to user') {
      return res.status(400).json({ error: 'Permission already assigned to user' });
    }
    
    return res.status(500).json({ error: 'Failed to add custom permission to user' });
  }
};

/**
 * Xóa quyền tùy chỉnh khỏi người dùng
 */
const removeCustomPermissionFromUser = async (req, res) => {
  try {
    const user = await authorizationService.removeCustomPermissionFromUser(
      req.params.userId,
      req.params.permissionId
    );
    
    return res.status(200).json({
      message: 'Custom permission removed successfully',
      user: {
        id: user._id,
        email: user.email,
        customPermissions: user.customPermissions
      }
    });
  } catch (error) {
    console.error('Error removing custom permission from user:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    return res.status(500).json({ error: 'Failed to remove custom permission from user' });
  }
};

/**
 * Kiểm tra quyền của người dùng
 */
const checkPermission = async (req, res) => {
  try {
    const { resource, action } = req.query;
    
    if (!resource || !action) {
      return res.status(400).json({ error: 'Resource and action are required' });
    }
    
    const hasPermission = await authorizationService.checkUserPermission(
      req.params.userId,
      resource,
      action
    );
    
    return res.status(200).json({ hasPermission });
  } catch (error) {
    console.error('Error checking permission:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    return res.status(500).json({ error: 'Failed to check permission' });
  }
};

module.exports = {
  assignRoleToUser,
  removeRoleFromUser,
  addCustomPermissionToUser,
  removeCustomPermissionFromUser,
  checkPermission
};