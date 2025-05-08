const Permission = require('./permission.model');
const Role = require('./role.model');
const User = require('../users/user.model');

/**
 * Dịch vụ quản lý quyền và vai trò
 */
class AuthorizationService {
  /**
   * Tạo quyền mới
   * @param {Object} permissionData - Dữ liệu quyền
   * @returns {Promise<Object>} Quyền đã tạo
   */
  async createPermission(permissionData) {
    const existingPermission = await Permission.findOne({
      resource: permissionData.resource,
      action: permissionData.action
    });
    
    if (existingPermission) {
      throw new Error('Permission already exists');
    }
    
    const permission = new Permission(permissionData);
    return permission.save();
  }
  
  /**
   * Lấy tất cả quyền
   * @param {Object} filter - Điều kiện lọc
   * @returns {Promise<Array>} Danh sách quyền
   */
  async getPermissions(filter = {}) {
    return Permission.find(filter).sort({ resource: 1, action: 1 });
  }
  
  /**
   * Cập nhật quyền
   * @param {String} id - ID quyền
   * @param {Object} updateData - Dữ liệu cập nhật
   * @returns {Promise<Object>} Quyền đã cập nhật
   */
  async updatePermission(id, updateData) {
    return Permission.findByIdAndUpdate(
      id,
      updateData,
      { new: true, runValidators: true }
    );
  }
  
  /**
   * Xóa quyền
   * @param {String} id - ID quyền
   * @returns {Promise<Object>} Kết quả xóa
   */
  async deletePermission(id) {
    // Kiểm tra quyền có được sử dụng trong vai trò nào không
    const roleWithPermission = await Role.findOne({ permissions: id });
    
    if (roleWithPermission) {
      throw new Error(`Permission is used in role: ${roleWithPermission.name}`);
    }
    
    // Kiểm tra quyền có được sử dụng trong quyền tùy chỉnh của người dùng không
    const userWithCustomPermission = await User.findOne({ customPermissions: id });
    
    if (userWithCustomPermission) {
      throw new Error('Permission is used in user custom permissions');
    }
    
    return Permission.findByIdAndDelete(id);
  }
  
  /**
   * Tạo vai trò mới
   * @param {Object} roleData - Dữ liệu vai trò
   * @returns {Promise<Object>} Vai trò đã tạo
   */
  async createRole(roleData) {
    const existingRole = await Role.findOne({ name: roleData.name });
    
    if (existingRole) {
      throw new Error('Role already exists');
    }
    
    const role = new Role(roleData);
    return role.save();
  }
  
  /**
   * Lấy tất cả vai trò
   * @param {Object} filter - Điều kiện lọc
   * @returns {Promise<Array>} Danh sách vai trò
   */
  async getRoles(filter = {}) {
    return Role.find(filter)
      .populate('permissions')
      .sort({ name: 1 });
  }
  
  /**
   * Lấy chi tiết vai trò
   * @param {String} id - ID vai trò
   * @returns {Promise<Object>} Thông tin vai trò
   */
  async getRoleById(id) {
    return Role.findById(id).populate('permissions');
  }
  
  /**
   * Cập nhật vai trò
   * @param {String} id - ID vai trò
   * @param {Object} updateData - Dữ liệu cập nhật
   * @returns {Promise<Object>} Vai trò đã cập nhật
   */
  async updateRole(id, updateData) {
    const role = await Role.findById(id);
    
    if (!role) {
      throw new Error('Role not found');
    }
    
    // Không cho phép cập nhật vai trò hệ thống
    if (role.isSystem && updateData.name) {
      throw new Error('Cannot change name of system role');
    }
    
    return Role.findByIdAndUpdate(
      id,
      updateData,
      { new: true, runValidators: true }
    );
  }
  
  /**
   * Thêm quyền vào vai trò
   * @param {String} roleId - ID vai trò
   * @param {String} permissionId - ID quyền
   * @returns {Promise<Object>} Vai trò đã cập nhật
   */
  async addPermissionToRole(roleId, permissionId) {
    const role = await Role.findById(roleId);
    
    if (!role) {
      throw new Error('Role not found');
    }
    
    const permission = await Permission.findById(permissionId);
    
    if (!permission) {
      throw new Error('Permission not found');
    }
    
    // Kiểm tra quyền đã tồn tại trong vai trò chưa
    if (role.permissions.includes(permissionId)) {
      throw new Error('Permission already assigned to role');
    }
    
    role.permissions.push(permissionId);
    return role.save();
  }
  
  /**
   * Xóa quyền khỏi vai trò
   * @param {String} roleId - ID vai trò
   * @param {String} permissionId - ID quyền
   * @returns {Promise<Object>} Vai trò đã cập nhật
   */
  async removePermissionFromRole(roleId, permissionId) {
    const role = await Role.findById(roleId);
    
    if (!role) {
      throw new Error('Role not found');
    }
    
    // Xóa quyền khỏi danh sách
    role.permissions = role.permissions.filter(
      p => p.toString() !== permissionId
    );
    
    return role.save();
  }
  
  /**
   * Xóa vai trò
   * @param {String} id - ID vai trò
   * @returns {Promise<Object>} Kết quả xóa
   */
  async deleteRole(id) {
    const role = await Role.findById(id);
    
    if (!role) {
      throw new Error('Role not found');
    }
    
    // Không cho phép xóa vai trò hệ thống
    if (role.isSystem) {
      throw new Error('Cannot delete system role');
    }
    
    // Kiểm tra vai trò có được sử dụng bởi người dùng nào không
    const userWithRole = await User.findOne({ roles: id });
    
    if (userWithRole) {
      throw new Error('Role is assigned to users');
    }
    
    return Role.findByIdAndDelete(id);
  }
  
  /**
   * Gán vai trò cho người dùng
   * @param {String} userId - ID người dùng
   * @param {String} roleId - ID vai trò
   * @returns {Promise<Object>} Người dùng đã cập nhật
   */
  async assignRoleToUser(userId, roleId) {
    const user = await User.findById(userId);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    const role = await Role.findById(roleId);
    
    if (!role) {
      throw new Error('Role not found');
    }
    
    // Kiểm tra vai trò đã được gán cho người dùng chưa
    if (user.roles.includes(roleId)) {
      throw new Error('Role already assigned to user');
    }
    
    user.roles.push(roleId);
    return user.save();
  }
  
  /**
   * Xóa vai trò khỏi người dùng
   * @param {String} userId - ID người dùng
   * @param {String} roleId - ID vai trò
   * @returns {Promise<Object>} Người dùng đã cập nhật
   */
  async removeRoleFromUser(userId, roleId) {
    const user = await User.findById(userId);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    // Xóa vai trò khỏi danh sách
    user.roles = user.roles.filter(
      r => r.toString() !== roleId
    );
    
    return user.save();
  }
  
  /**
   * Thêm quyền tùy chỉnh cho người dùng
   * @param {String} userId - ID người dùng
   * @param {String} permissionId - ID quyền
   * @returns {Promise<Object>} Người dùng đã cập nhật
   */
  async addCustomPermissionToUser(userId, permissionId) {
    const user = await User.findById(userId);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    const permission = await Permission.findById(permissionId);
    
    if (!permission) {
      throw new Error('Permission not found');
    }
    
    // Kiểm tra quyền đã tồn tại chưa
    if (user.customPermissions.includes(permissionId)) {
      throw new Error('Permission already assigned to user');
    }
    
    user.customPermissions.push(permissionId);
    return user.save();
  }
  
  /**
   * Xóa quyền tùy chỉnh khỏi người dùng
   * @param {String} userId - ID người dùng
   * @param {String} permissionId - ID quyền
   * @returns {Promise<Object>} Người dùng đã cập nhật
   */
  async removeCustomPermissionFromUser(userId, permissionId) {
    const user = await User.findById(userId);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    // Xóa quyền khỏi danh sách
    user.customPermissions = user.customPermissions.filter(
      p => p.toString() !== permissionId
    );
    
    return user.save();
  }
  
  /**
   * Kiểm tra người dùng có quyền không
   * @param {String} userId - ID người dùng
   * @param {String} resource - Tài nguyên
   * @param {String} action - Hành động
   * @returns {Promise<Boolean>} Kết quả kiểm tra
   */
  async checkUserPermission(userId, resource, action) {
    const user = await User.findById(userId)
      .populate({
        path: 'roles',
        match: { isActive: true },
        populate: {
          path: 'permissions',
          match: { isActive: true }
        }
      })
      .populate({
        path: 'customPermissions',
        match: { isActive: true }
      });
    
    if (!user) {
      throw new Error('User not found');
    }
    
    return user.hasPermission(resource, action);
  }
}

module.exports = new AuthorizationService();