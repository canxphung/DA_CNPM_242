const mongoose = require('mongoose');
const bcrypt = require('bcrypt');

// Định nghĩa schema cho user
const userSchema = new mongoose.Schema({
  email: {
    type: String,
    required: [true, 'Email is required'],
    unique: true,
    lowercase: true,
    trim: true,
    match: [/^\S+@\S+\.\S+$/, 'Please enter a valid email address']
  },
  password: {
    type: String,
    required: [true, 'Password is required'],
    minlength: [8, 'Password must be at least 8 characters long']
  },
  firstName: {
    type: String,
    required: [true, 'First name is required'],
    trim: true
  },
  lastName: {
    type: String,
    required: [true, 'Last name is required'],
    trim: true
  },
  role: {
    type: String,
    enum: ['user', 'admin', 'manager'],
    default: 'user'
  },
  phoneNumber: {
    type: String,
    trim: true
  },
  address: {
    street: String,
    city: String,
    state: String,
    zipCode: String,
    country: String
  },
  isActive: {
    type: Boolean,
    default: true
  },
  lastLogin: {
    type: Date
  },
  profileImage: {
    type: String
  },
  refreshTokens: [{
    token: String,
    expiresAt: Date
  }],
  roles: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Role'
  }],
  
  // Quyền tùy chỉnh (ngoài quyền từ vai trò)
  customPermissions: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Permission'
  }]
}, {
  timestamps: true // Tự động thêm createdAt và updatedAt
});

// Thêm index cho tìm kiếm hiệu quả
userSchema.index({ role: 1 });

// Phương thức hash password trước khi lưu user
userSchema.pre('save', async function(next) {
  // Chỉ hash password khi nó được thay đổi
  if (!this.isModified('password')) return next();
  
  try {
    // Tạo salt và hash password
    const salt = await bcrypt.genSalt(10);
    this.password = await bcrypt.hash(this.password, salt);
    next();
  } catch (error) {
    next(error);
  }
});

// Phương thức kiểm tra password
userSchema.methods.comparePassword = async function(candidatePassword) {
  return bcrypt.compare(candidatePassword, this.password);
};

// Phương thức tạo JSON (không bao gồm password)
userSchema.methods.toJSON = function() {
  const user = this.toObject();
  delete user.password;
  delete user.refreshTokens;
  return user;
};
// Phương thức kiểm tra quyền
userSchema.methods.hasPermission = async function(resource, action) {
    // Nếu chưa populate roles và permissions, thực hiện populate
    const user = this.populated('roles') ? 
      this : 
      await this.constructor.findById(this._id)
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
    
    // Kiểm tra quyền tùy chỉnh
    const hasCustomPermission = user.customPermissions.some(
      permission => permission.resource === resource && 
                   (permission.action === action || permission.action === 'manage')
    );
    
    if (hasCustomPermission) return true;
    
    // Kiểm tra quyền từ vai trò
    return user.roles.some(role => 
      role.permissions.some(
        permission => permission.resource === resource && 
                     (permission.action === action || permission.action === 'manage')
      )
    );
  };
  
  // Phương thức kiểm tra vai trò
userSchema.methods.hasRole = function(roleName) {
    if (!this.populated('roles')) {
      throw new Error('Roles not populated');
    }
    
    return this.roles.some(role => role.name === roleName && role.isActive);
};

// Phương thức lấy tên đầy đủ
userSchema.virtual('fullName').get(function() {
  return `${this.firstName} ${this.lastName}`;
});

// Tạo model từ schema
const User = mongoose.model('User', userSchema);

module.exports = User;