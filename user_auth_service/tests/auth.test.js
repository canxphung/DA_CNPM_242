const request = require('supertest');
const mongoose = require('mongoose');
const app = require('../src/app');
const User = require('../src/core/users/user.model');
const config = require('../src/infrastructure/config');

describe('Authentication API', () => {
  let testUser;
  let accessToken;
  let refreshToken;
  
  // Kết nối database và tạo user test trước khi chạy test
  beforeAll(async () => {
    await mongoose.connect(config.db.mongo.uri, {
      useNewUrlParser: true,
      useUnifiedTopology: true
    });
    
    // Tạo user test
    testUser = new User({
      email: 'test@example.com',
      password: 'password123',
      firstName: 'Test',
      lastName: 'User',
      role: 'user'
    });
    
    await testUser.save();
  });
  
  // Xóa dữ liệu test sau khi chạy xong
  afterAll(async () => {
    await User.deleteMany({});
    await mongoose.connection.close();
  });
  
  // Test đăng nhập
  test('Should login a user and return tokens', async () => {
    const response = await request(app)
      .post(`${config.apiPrefix}/auth/login`)
      .send({
        email: 'test@example.com',
        password: 'password123'
      });
    
    expect(response.statusCode).toBe(200);
    expect(response.body).toHaveProperty('tokens');
    expect(response.body.tokens).toHaveProperty('accessToken');
    expect(response.body.tokens).toHaveProperty('refreshToken');
    
    accessToken = response.body.tokens.accessToken;
    refreshToken = response.body.tokens.refreshToken;
  });
  
  // Test lấy thông tin người dùng
  test('Should get user profile with valid token', async () => {
    const response = await request(app)
      .get(`${config.apiPrefix}/auth/me`)
      .set('Authorization', `Bearer ${accessToken}`);
    
    expect(response.statusCode).toBe(200);
    expect(response.body).toHaveProperty('email', 'test@example.com');
  });
  
  // Test làm mới token
  test('Should refresh token with valid refresh token', async () => {
    const response = await request(app)
      .post(`${config.apiPrefix}/auth/refresh-token`)
      .send({ refreshToken });
    
    expect(response.statusCode).toBe(200);
    expect(response.body).toHaveProperty('accessToken');
  });
  
  // Test đăng xuất
  test('Should logout with valid token', async () => {
    const response = await request(app)
      .post(`${config.apiPrefix}/auth/logout`)
      .set('Authorization', `Bearer ${accessToken}`)
      .send({ refreshToken });
    
    expect(response.statusCode).toBe(200);
    expect(response.body).toHaveProperty('message', 'Successfully logged out');
  });
});