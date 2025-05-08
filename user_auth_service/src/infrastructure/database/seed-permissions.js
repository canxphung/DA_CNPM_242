const mongoose = require('mongoose');
const { connectToDatabase } = require('./connection');
const Permission = require('../../core/auth/permission.model');
const Role = require('../../core/auth/role.model');
const User = require('../../core/users/user.model');
const config = require('../config');

const seedPermissionsAndRoles = async () => {
  try {
    // Kết nối database
    await connectToDatabase();
    
    console.log('Seeding permissions and roles...');
    
    // Xóa dữ liệu cũ
    await Permission.deleteMany({});
    await Role.deleteMany({});
    
    // Tạo các quyền cơ bản
    const permissions = await Permission.insertMany([
      // Quyền quản lý người dùng
      {
        name: 'Read Users',
        description: 'Allows reading user information',
        resource: 'user',
        action: 'read',
        isActive: true
      },
      {
        name: 'Create Users',
        description: 'Allows creating new users',
        resource: 'user',
        action: 'create',
        isActive: true
      },
      {
        name: 'Update Users',
        description: 'Allows updating user information',
        resource: 'user',
        action: 'update',
        isActive: true
      },
      {
        name: 'Delete Users',
        description: 'Allows deleting users',
        resource: 'user',
        action: 'delete',
        isActive: true
      },
      {
        name: 'Manage Users',
        description: 'Allows complete management of users',
        resource: 'user',
        action: 'manage',
        isActive: true
      },
      
      // Quyền quản lý vai trò
      {
        name: 'Read Roles',
        description: 'Allows reading role information',
        resource: 'role',
        action: 'read',
        isActive: true
      },
      {
        name: 'Create Roles',
        description: 'Allows creating new roles',
        resource: 'role',
        action: 'create',
        isActive: true
      },
      {
        name: 'Update Roles',
        description: 'Allows updating role information',
        resource: 'role',
        action: 'update',
        isActive: true
      },
      {
        name: 'Delete Roles',
        description: 'Allows deleting roles',
        resource: 'role',
        action: 'delete',
        isActive: true
      },
      {
        name: 'Manage Roles',
        description: 'Allows complete management of roles',
        resource: 'role',
        action: 'manage',
        isActive: true
      },
      
      // Quyền quản lý permissions
      {
        name: 'Read Permissions',
        description: 'Allows reading permission information',
        resource: 'permission',
        action: 'read',
        isActive: true
      },
      {
        name: 'Create Permissions',
        description: 'Allows creating new permissions',
        resource: 'permission',
        action: 'create',
        isActive: true
      },
      {
        name: 'Update Permissions',
        description: 'Allows updating permission information',
        resource: 'permission',
        action: 'update',
        isActive: true
      },
      {
        name: 'Delete Permissions',
        description: 'Allows deleting permissions',
        resource: 'permission',
        action: 'delete',
        isActive: true
      },
      {
        name: 'Manage Permissions',
        description: 'Allows complete management of permissions',
        resource: 'permission',
        action: 'manage',
        isActive: true
      }
    ]);
    
    console.log(`${permissions.length} permissions created`);
    
    // Tạo các vai trò cơ bản
    const adminRole = await Role.create({
      name: 'admin',
      description: 'Administrator with full access',
      permissions: permissions.map(p => p._id),
      isSystem: true,
      isActive: true
    });
    
    const managerRole = await Role.create({
      name: 'manager',
      description: 'Manager with limited access',
      permissions: permissions
        .filter(p => p.action !== 'delete' && p.action !== 'manage')
        .map(p => p._id),
      isSystem: true,
      isActive: true
    });
    
    const userRole = await Role.create({
      name: 'user',
      description: 'Regular user with basic access',
      permissions: permissions
        .filter(p => p.action === 'read' && p.resource !== 'permission')
        .map(p => p._id),
      isSystem: true,
      isActive: true
    });
    
    console.log(`Created roles: ${adminRole.name}, ${managerRole.name}, ${userRole.name}`);
    
    // Cập nhật quyền cho người dùng có sẵn
    const adminUser = await User.findOne({ email: 'admin@example.com' });
    
    if (adminUser) {
      adminUser.roles = [adminRole._id];
      await adminUser.save();
      console.log(`Updated admin user with admin role`);
    }
    
    const managerUser = await User.findOne({ email: 'manager@example.com' });
    
    if (managerUser) {
      managerUser.roles = [managerRole._id];
      await managerUser.save();
      console.log(`Updated manager user with manager role`);
    }
    
    const regularUser = await User.findOne({ email: 'user@example.com' });
    
    if (regularUser) {
      regularUser.roles = [userRole._id];
      await regularUser.save();
      console.log(`Updated regular user with user role`);
    }
    
    console.log('Permissions and roles seeded successfully!');
    process.exit(0);
  } catch (error) {
    console.error('Error seeding permissions and roles:', error);
    process.exit(1);
  }
};

// Chạy hàm seed
seedPermissionsAndRoles();