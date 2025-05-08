const mongoose = require('mongoose');

const permissionSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    unique: true,
    trim: true
  },
  description: {
    type: String,
    required: true
  },
  resource: {
    type: String,
    required: true,
    trim: true
  },
  action: {
    type: String,
    required: true,
    enum: ['create', 'read', 'update', 'delete', 'manage'],
    trim: true
  },
  isActive: {
    type: Boolean,
    default: true
  }
}, {
  timestamps: true
});

// Tạo index cho tìm kiếm hiệu quả
permissionSchema.index({ resource: 1, action: 1 }, { unique: true });

const Permission = mongoose.model('Permission', permissionSchema);

module.exports = Permission;