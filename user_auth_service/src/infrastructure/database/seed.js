const User = require('../../core/users/user.model');
const { connectToDatabase } = require('./connection');

const seedUsers = async () => {
  try {
    // Kết nối database
    await connectToDatabase();
    
    // Xóa dữ liệu cũ
    await User.deleteMany({});
    
    // Tạo người dùng admin
    const admin = new User({
      email: 'admin@example.com',
      password: 'admin1234',
      firstName: 'Admin',
      lastName: 'User',
      role: 'admin',
      isActive: true
    });
    
    // Tạo người dùng thông thường
    const user = new User({
      email: 'user@example.com',
      password: 'user1234',
      firstName: 'Normal',
      lastName: 'User',
      role: 'user',
      isActive: true
    });
    
    // Tạo người dùng manager
    const manager = new User({
      email: 'manager@example.com',
      password: 'manager1234',
      firstName: 'Manager',
      lastName: 'User',
      role: 'manager',
      isActive: true
    });
    
    // Lưu người dùng vào database
    await Promise.all([
      admin.save(),
      user.save(),
      manager.save()
    ]);
    
    console.log('Database seeded successfully!');
    process.exit(0);
  } catch (error) {
    console.error('Error seeding database:', error);
    process.exit(1);
  }
};

// Chạy hàm seed
seedUsers();