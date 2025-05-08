const User = require('./user.model');

/**
 * Repository xử lý truy vấn dữ liệu người dùng
 */
class UserRepository {
  /**
   * Tìm tất cả người dùng với phân trang và lọc
   * @param {Object} filter - Điều kiện lọc
   * @param {Object} options - Tùy chọn phân trang
   * @returns {Promise<Array>} Danh sách người dùng
   */
  async findAll(filter = {}, options = {}) {
    const { page = 1, limit = 10, sort = { createdAt: -1 } } = options;
    const skip = (page - 1) * limit;
    
    // Thực hiện truy vấn với phân trang
    const users = await User.find(filter)
      .sort(sort)
      .skip(skip)
      .limit(limit);
    
    // Đếm tổng số user thỏa mãn điều kiện
    const total = await User.countDocuments(filter);
    
    return {
      users,
      pagination: {
        total,
        page: parseInt(page),
        limit: parseInt(limit),
        totalPages: Math.ceil(total / limit)
      }
    };
  }
  
  /**
   * Tìm người dùng theo ID
   * @param {String} id - ID người dùng
   * @returns {Promise<Object>} Thông tin người dùng
   */
  async findById(id) {
    return User.findById(id);
  }
  
  /**
   * Tìm người dùng theo email
   * @param {String} email - Email người dùng
   * @returns {Promise<Object>} Thông tin người dùng
   */
  async findByEmail(email) {
    return User.findOne({ email });
  }
  
  /**
   * Tạo người dùng mới
   * @param {Object} userData - Dữ liệu người dùng
   * @returns {Promise<Object>} Người dùng đã tạo
   */
  async create(userData) {
    const user = new User(userData);
    return user.save();
  }
  
  /**
   * Cập nhật thông tin người dùng
   * @param {String} id - ID người dùng
   * @param {Object} updateData - Dữ liệu cần cập nhật
   * @returns {Promise<Object>} Người dùng đã cập nhật
   */
  async update(id, updateData) {
    // Sử dụng { new: true } để trả về document đã cập nhật
    return User.findByIdAndUpdate(
      id,
      updateData,
      { new: true, runValidators: true }
    );
  }
  
  /**
   * Đánh dấu người dùng là không hoạt động (soft delete)
   * @param {String} id - ID người dùng
   * @returns {Promise<Object>} Kết quả cập nhật
   */
  async deactivate(id) {
    return User.findByIdAndUpdate(
      id,
      { isActive: false },
      { new: true }
    );
  }
  
  /**
   * Đánh dấu người dùng là hoạt động
   * @param {String} id - ID người dùng
   * @returns {Promise<Object>} Kết quả cập nhật
   */
  async activate(id) {
    return User.findByIdAndUpdate(
      id,
      { isActive: true },
      { new: true }
    );
  }
  
  /**
   * Xóa người dùng (hard delete - thận trọng)
   * @param {String} id - ID người dùng
   * @returns {Promise<Object>} Kết quả xóa
   */
  async delete(id) {
    return User.findByIdAndDelete(id);
  }
  
  /**
   * Tìm kiếm người dùng theo từ khóa
   * @param {String} keyword - Từ khóa tìm kiếm
   * @param {Object} options - Tùy chọn phân trang
   * @returns {Promise<Array>} Danh sách người dùng
   */
  async search(keyword, options = {}) {
    const { page = 1, limit = 10 } = options;
    const skip = (page - 1) * limit;
    
    // Tạo regex pattern để tìm kiếm (case insensitive)
    const pattern = new RegExp(keyword, 'i');
    
    // Tìm kiếm trong các trường phù hợp
    const filter = {
      $or: [
        { firstName: pattern },
        { lastName: pattern },
        { email: pattern }
      ]
    };
    
    const users = await User.find(filter)
      .skip(skip)
      .limit(limit)
      .sort({ createdAt: -1 });
    
    const total = await User.countDocuments(filter);
    
    return {
      users,
      pagination: {
        total,
        page: parseInt(page),
        limit: parseInt(limit),
        totalPages: Math.ceil(total / limit)
      }
    };
  }
}

module.exports = new UserRepository();