const userRepository = require('./user.repository');

/**
 * Service xử lý logic nghiệp vụ người dùng
 */
class UserService {
  /**
   * Lấy danh sách người dùng với phân trang
   * @param {Object} query - Truy vấn từ request
   * @returns {Promise<Object>} Danh sách người dùng và thông tin phân trang
   */
  async getUsers(query = {}) {
    const { page, limit, role, isActive, search } = query;
    
    // Xây dựng filter dựa trên query
    const filter = {};
    
    if (role) filter.role = role;
    if (isActive !== undefined) filter.isActive = isActive === 'true';
    
    // Nếu có từ khóa tìm kiếm, gọi phương thức search
    if (search) {
      return userRepository.search(search, { page, limit });
    }
    
    // Nếu không, lấy tất cả theo filter
    return userRepository.findAll(filter, { page, limit });
  }
  
  /**
   * Lấy thông tin chi tiết người dùng
   * @param {String} id - ID người dùng
   * @returns {Promise<Object>} Thông tin người dùng
   */
  async getUserById(id) {
    const user = await userRepository.findById(id);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    return user;
  }
  
  /**
   * Tạo người dùng mới
   * @param {Object} userData - Dữ liệu người dùng
   * @returns {Promise<Object>} Người dùng đã tạo
   */
  async createUser(userData) {
    // Kiểm tra email đã tồn tại chưa
    const existingUser = await userRepository.findByEmail(userData.email);
    
    if (existingUser) {
      throw new Error('Email already in use');
    }
    
    // Tạo người dùng mới
    return userRepository.create(userData);
  }
  
  /**
   * Cập nhật thông tin người dùng
   * @param {String} id - ID người dùng
   * @param {Object} updateData - Dữ liệu cần cập nhật
   * @returns {Promise<Object>} Người dùng đã cập nhật
   */
  async updateUser(id, updateData) {
    // Kiểm tra người dùng tồn tại
    const user = await userRepository.findById(id);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    // Không cho phép cập nhật email thành email đã tồn tại của người dùng khác
    if (updateData.email && updateData.email !== user.email) {
      const existingUser = await userRepository.findByEmail(updateData.email);
      
      if (existingUser) {
        throw new Error('Email already in use');
      }
    }
    
    // Loại bỏ trường role nếu không phải admin
    // (logic này thường sẽ được xử lý ở middleware authorization)
    
    return userRepository.update(id, updateData);
  }
  
  /**
   * Thay đổi mật khẩu người dùng
   * @param {String} id - ID người dùng
   * @param {String} currentPassword - Mật khẩu hiện tại
   * @param {String} newPassword - Mật khẩu mới
   * @returns {Promise<Object>} Kết quả thay đổi
   */
  async changePassword(id, currentPassword, newPassword) {
    // Tìm người dùng
    const user = await userRepository.findById(id);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    // Kiểm tra mật khẩu hiện tại
    const isMatch = await user.comparePassword(currentPassword);
    
    if (!isMatch) {
      throw new Error('Current password is incorrect');
    }
    
    // Thay đổi mật khẩu
    user.password = newPassword;
    await user.save();
    
    return { success: true, message: 'Password changed successfully' };
  }
  
  /**
   * Vô hiệu hóa tài khoản người dùng
   * @param {String} id - ID người dùng
   * @returns {Promise<Object>} Người dùng đã cập nhật
   */
  async deactivateUser(id) {
    const user = await userRepository.findById(id);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    return userRepository.deactivate(id);
  }
  
  /**
   * Kích hoạt tài khoản người dùng
   * @param {String} id - ID người dùng
   * @returns {Promise<Object>} Người dùng đã cập nhật
   */
  async activateUser(id) {
    const user = await userRepository.findById(id);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    return userRepository.activate(id);
  }
  
  /**
   * Xóa người dùng (cẩn thận với thao tác này)
   * @param {String} id - ID người dùng
   * @returns {Promise<Object>} Kết quả xóa
   */
  async deleteUser(id) {
    const user = await userRepository.findById(id);
    
    if (!user) {
      throw new Error('User not found');
    }
    
    // Thường nên sử dụng soft delete (deactivateUser) thay vì xóa hoàn toàn
    return userRepository.delete(id);
  }
}

module.exports = new UserService();