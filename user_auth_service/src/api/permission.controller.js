const authorizationService = require('../core/auth/authorization.service');

/**
 * Lấy danh sách quyền
 */
const getPermissions = async (req, res) => {
  try {
    const { resource, action, isActive } = req.query;
    
    // Xây dựng filter từ query
    const filter = {};
    
    if (resource) filter.resource = resource;
    if (action) filter.action = action;
    if (isActive !== undefined) filter.isActive = isActive === 'true';
    
    const permissions = await authorizationService.getPermissions(filter);
    
    return res.status(200).json(permissions);
  } catch (error) {
    console.error('Error fetching permissions:', error);
    return res.status(500).json({ error: 'Failed to fetch permissions' });
  }
};

/**
 * Tạo quyền mới
 */
const createPermission = async (req, res) => {
  try {
    const { name, description, resource, action } = req.body;
    
    if (!name || !description || !resource || !action) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    const permission = await authorizationService.createPermission(req.body);
    
    return res.status(201).json(permission);
  } catch (error) {
    console.error('Error creating permission:', error);
    
    if (error.message === 'Permission already exists') {
      return res.status(400).json({ error: 'Permission already exists' });
    }
    
    return res.status(500).json({ error: 'Failed to create permission' });
  }
};

/**
 * Cập nhật quyền
 */
const updatePermission = async (req, res) => {
  try {
    const permission = await authorizationService.updatePermission(
      req.params.id,
      req.body
    );
    
    if (!permission) {
      return res.status(404).json({ error: 'Permission not found' });
    }
    
    return res.status(200).json(permission);
  } catch (error) {
    console.error('Error updating permission:', error);
    return res.status(500).json({ error: 'Failed to update permission' });
  }
};

/**
 * Xóa quyền
 */
const deletePermission = async (req, res) => {
  try {
    await authorizationService.deletePermission(req.params.id);
    
    return res.status(200).json({ message: 'Permission deleted successfully' });
  } catch (error) {
    console.error('Error deleting permission:', error);
    
    if (error.message.includes('Permission is used')) {
      return res.status(400).json({ error: error.message });
    }
    
    return res.status(500).json({ error: 'Failed to delete permission' });
  }
};

module.exports = {
  getPermissions,
  createPermission,
  updatePermission,
  deletePermission
};