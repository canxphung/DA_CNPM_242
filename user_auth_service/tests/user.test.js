const request = require('supertest');
const mongoose = require('mongoose');
const app = require('../src/app');
const User = require('../src/core/users/user.model');
const config = require('../src/infrastructure/config');

describe('User API', () => {
  let userId;
  
  // Kết nối database trước khi chạy test
  beforeAll(async () => {
    await mongoose.connect(config.db.mongo.uri, {
      useNewUrlParser: true,
      useUnifiedTopology: true
    });
    
    // Xóa dữ liệu test cũ
    await User.deleteMany({});
  });
  
  // Đóng kết nối database sau khi chạy xong
  afterAll(async () => {
    await User.deleteMany({});
    await mongoose.connection.close();
  });
  
  // Test tạo người dùng
  test('Should create a new user', async () => {
    const response = await request(app)
      .post(`${config.apiPrefix}/users`)
      .send({
        email: 'test@example.com',
        password: 'password123',
        firstName: 'Test',
        lastName: 'User',
        role: 'user'
      });
    
    expect(response.statusCode).toBe(201);
    expect(response.body).toHaveProperty('_id');
    expect(response.body).toHaveProperty('email', 'test@example.com');
    expect(response.body).not.toHaveProperty('password');
    
    userId = response.body._id;
  });
  
  // Test lấy danh sách người dùng
  test('Should get all users', async () => {
    const response = await request(app)
      .get(`${config.apiPrefix}/users`);
    
    expect(response.statusCode).toBe(200);
    expect(response.body).toHaveProperty('users');
    expect(response.body.users).toBeInstanceOf(Array);
    expect(response.body.users.length).toBeGreaterThan(0);
    expect(response.body).toHaveProperty('pagination');
  });
  
  // Test lấy thông tin chi tiết người dùng
  test('Should get user by id', async () => {
    const response = await request(app)
      .get(`${config.apiPrefix}/users/${userId}`);
    
    expect(response.statusCode).toBe(200);
    expect(response.body).toHaveProperty('_id', userId);
    expect(response.body).toHaveProperty('email', 'test@example.com');
  });
  
  // Test cập nhật thông tin người dùng
  test('Should update user', async () => {
    const response = await request(app)
      .put(`${config.apiPrefix}/users/${userId}`)
      .send({
        firstName: 'Updated',
        lastName: 'Name'
      });
    
    expect(response.statusCode).toBe(200);
    expect(response.body).toHaveProperty('firstName', 'Updated');
    expect(response.body).toHaveProperty('lastName', 'Name');
  });
  
  // Test lỗi khi tạo người dùng với email đã tồn tại
  test('Should not create user with duplicate email', async () => {
    const response = await request(app)
      .post(`${config.apiPrefix}/users`)
      .send({
        email: 'test@example.com',
        password: 'password123',
        firstName: 'Another',
        lastName: 'User',
        role: 'user'
      });
    
    expect(response.statusCode).toBe(400);
    expect(response.body).toHaveProperty('error', 'Email already in use');
  });
  
  // Test lỗi validation khi thiếu dữ liệu bắt buộc
  test('Should validate required fields', async () => {
    const response = await request(app)
      .post(`${config.apiPrefix}/users`)
      .send({
        email: 'invalid'
      });
    
    expect(response.statusCode).toBe(400);
    expect(response.body).toHaveProperty('errors');
    expect(response.body.errors).toHaveProperty('email');
  });
  
  // Test vô hiệu hóa người dùng
  test('Should deactivate user', async () => {
    const response = await request(app)
      .put(`${config.apiPrefix}/users/${userId}/deactivate`);
    
    expect(response.statusCode).toBe(200);
    expect(response.body.user).toHaveProperty('isActive', false);
  });
  
  // Test kích hoạt người dùng
  test('Should activate user', async () => {
    const response = await request(app)
      .put(`${config.apiPrefix}/users/${userId}/activate`);
    
    expect(response.statusCode).toBe(200);
    expect(response.body.user).toHaveProperty('isActive', true);
  });
  
  // Test xóa người dùng
  test('Should delete user', async () => {
    const response = await request(app)
      .delete(`${config.apiPrefix}/users/${userId}`);
    
    expect(response.statusCode).toBe(200);
    expect(response.body).toHaveProperty('message', 'User deleted successfully');
    
    // Kiểm tra người dùng đã bị xóa
    const getResponse = await request(app)
      .get(`${config.apiPrefix}/users/${userId}`);
    
    expect(getResponse.statusCode).toBe(404);
  });
});