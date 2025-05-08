const authorizationService = require('../core/auth/authorization.service');

/**
 * Lấy danh sách vai trò
 */
const getRoles = async (req, res) => {
  try {
    const { name, isActive } = req.query;
    
    // Xây dựng filter từ query
    const filter = {};
    
    if (name) filter.name = name;
    if (isActive !== undefined) filter.isActive = isActive === 'true';
    
    const roles = await authorizationService.getRoles(filter);
    
    return res.status(200).json(roles);
  } catch (error) {
    console.error('Error fetching roles:', error);
    return res.status(500).json({ error: 'Failed to fetch roles' });
  }
};

/**
 * Lấy chi tiết vai trò
 */
const getRoleById = async (req, res) => {
  try {
    const role = await authorizationService.getRoleById(req.params.id);
    
    if (!role) {
      return res.status(404).json({ error: 'Role not found' });
    }
    
    return res.status(200).json(role);
  } catch (error) {
    console.error('Error fetching role:', error);
    return res.status(500).json({ error: 'Failed to fetch role' });
  }
};

/**
 * Tạo vai trò mới
 */
const createRole = async (req, res) => {
  try {
    const { name, description, permissions } = req.body;
    
    if (!name || !description) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    const role = await authorizationService.createRole(req.body);
    
    return res.status(201).json(role);
  } catch (error) {
    console.error('Error creating role:', error);
    
    if (error.message === 'Role already exists') {
      return res.status(400).json({ error: 'Role already exists' });
    }
    
    return res.status(500).json({ error: 'Failed to create role' });
  }
};

/**
 * Cập nhật vai trò
 */
const updateRole = async (req, res) => {
  try {
    const role = await authorizationService.updateRole(
      req.params.id,
      req.body
    );
    
    if (!role) {
      return res.status(404).json({ error: 'Role not found' });
    }
    
    return res.status(200).json(role);
  } catch (error) {
    console.error('Error updating role:', error);
    
    if (error.message === 'Cannot change name of system role') {
      return res.status(400).json({ error: 'Cannot change name of system role' });
    }
    
    return res.status(500).json({ error: 'Failed to update role' });
  }
};

/**
 * Xóa vai trò
 */
const deleteRole = async (req, res) => {
  try {
    await authorizationService.deleteRole(req.params.id);
    
    return res.status(200).json({ message: 'Role deleted successfully' });
  } catch (error) {
    console.error('Error deleting role:', error);
    
    if (error.message === 'Cannot delete system role') {
      return res.status(400).json({ error: 'Cannot delete system role' });
    }
    
    if (error.message === 'Role is assigned to users') {
      return res.status(400).json({ error: 'Role is assigned to users' });
    }
    
    return res.status(500).json({ error: 'Failed to delete role' });
  }
};

/**
 * Thêm quyền cho vai trò
 */
const addPermissionToRole = async (req, res) => {
  try {
    const { permissionId } = req.body;
    
    if (!permissionId) {
      return res.status(400).json({ error: 'Permission ID is required' });
    }
    
    const role = await authorizationService.addPermissionToRole(
      req.params.id,
      permissionId
    );
    
    return res.status(200).json(role);
  } catch (error) {
    console.error('Error adding permission to role:', error);
    
    if (error.message === 'Role not found') {
      return res.status(404).json({ error: 'Role not found' });
    }
    
    if (error.message === 'Permission not found') {
      return res.status(404).json({ error: 'Permission not found' });
    }
    
    if (error.message === 'Permission already assigned to role') {
      return res.status(400).json({ error: 'Permission already assigned to role' });
    }
    
    return res.status(500).json({ error: 'Failed to add permission to role' });
  }
};

/**
 * Xóa quyền khỏi vai trò
 */
const removePermissionFromRole = async (req, res) => {
  try {
    const role = await authorizationService.removePermissionFromRole(
      req.params.id,
      req.params.permissionId
    );
    
    return res.status(200).json(role);
  } catch (error) {
    console.error('Error removing permission from role:', error);
    
    if (error.message === 'Role not found') {
      return res.status(404).json({ error: 'Role not found' });
    }
    
    return res.status(500).json({ error: 'Failed to remove permission from role' });
  }
};

module.exports = {
  getRoles,
  getRoleById,
  createRole,
  updateRole,
  deleteRole,
  addPermissionToRole,
  removePermissionFromRole
};