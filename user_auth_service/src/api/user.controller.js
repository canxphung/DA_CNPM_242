const userService = require('../core/users/user.service');

/**
 * Lấy danh sách người dùng
 */
const getUsers = async (req, res) => {
  try {
    const result = await userService.getUsers(req.query);
    return res.status(200).json(result);
  } catch (error) {
    console.error('Error fetching users:', error);
    return res.status(500).json({ error: 'Failed to fetch users' });
  }
};

/**
 * Lấy thông tin chi tiết người dùng
 */
const getUserById = async (req, res) => {
  try {
    const user = await userService.getUserById(req.params.id);
    return res.status(200).json(user);
  } catch (error) {
    console.error('Error fetching user:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    return res.status(500).json({ error: 'Failed to fetch user' });
  }
};

/**
 * Lấy thông tin người dùng hiện tại
 */
const getCurrentUser = async (req, res) => {
  try {
    // req.user được thiết lập trong middleware xác thực
    const user = await userService.getUserById(req.user.id);
    return res.status(200).json(user);
  } catch (error) {
    console.error('Error fetching current user:', error);
    return res.status(500).json({ error: 'Failed to fetch user profile' });
  }
};

/**
 * Tạo người dùng mới
 */
const createUser = async (req, res) => {
  try {
    const user = await userService.createUser(req.body);
    return res.status(201).json(user);
  } catch (error) {
    console.error('Error creating user:', error);
    
    if (error.message === 'Email already in use') {
      return res.status(400).json({ error: 'Email already in use' });
    }
    
    return res.status(500).json({ error: 'Failed to create user' });
  }
};

/**
 * Cập nhật thông tin người dùng
 */
const updateUser = async (req, res) => {
  try {
    const user = await userService.updateUser(req.params.id, req.body);
    return res.status(200).json(user);
  } catch (error) {
    console.error('Error updating user:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    if (error.message === 'Email already in use') {
      return res.status(400).json({ error: 'Email already in use' });
    }
    
    return res.status(500).json({ error: 'Failed to update user' });
  }
};

/**
 * Thay đổi mật khẩu người dùng
 */
const changePassword = async (req, res) => {
  try {
    const { currentPassword, newPassword } = req.body;
    
    // Sử dụng ID từ token xác thực
    const result = await userService.changePassword(
      req.user.id,
      currentPassword,
      newPassword
    );
    
    return res.status(200).json(result);
  } catch (error) {
    console.error('Error changing password:', error);
    
    if (error.message === 'Current password is incorrect') {
      return res.status(400).json({ error: 'Current password is incorrect' });
    }
    
    return res.status(500).json({ error: 'Failed to change password' });
  }
};

/**
 * Vô hiệu hóa tài khoản người dùng
 */
const deactivateUser = async (req, res) => {
  try {
    const user = await userService.deactivateUser(req.params.id);
    return res.status(200).json({ message: 'User deactivated successfully', user });
  } catch (error) {
    console.error('Error deactivating user:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    return res.status(500).json({ error: 'Failed to deactivate user' });
  }
};

/**
 * Kích hoạt tài khoản người dùng
 */
const activateUser = async (req, res) => {
  try {
    const user = await userService.activateUser(req.params.id);
    return res.status(200).json({ message: 'User activated successfully', user });
  } catch (error) {
    console.error('Error activating user:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    return res.status(500).json({ error: 'Failed to activate user' });
  }
};

/**
 * Xóa người dùng
 */
const deleteUser = async (req, res) => {
  try {
    await userService.deleteUser(req.params.id);
    return res.status(200).json({ message: 'User deleted successfully' });
  } catch (error) {
    console.error('Error deleting user:', error);
    
    if (error.message === 'User not found') {
      return res.status(404).json({ error: 'User not found' });
    }
    
    return res.status(500).json({ error: 'Failed to delete user' });
  }
};

module.exports = {
  getUsers,
  getUserById,
  getCurrentUser,
  createUser,
  updateUser,
  changePassword,
  deactivateUser,
  activateUser,
  deleteUser
};