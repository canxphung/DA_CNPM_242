const redis = require('redis');
const { promisify } = require('util');
const config = require('../config');

// Khởi tạo client Redis
const redisClient = redis.createClient(config.db.redis.uri);

// Xử lý lỗi kết nối
redisClient.on('error', (error) => {
  console.error(`Redis Error: ${error}`);
});

redisClient.on('connect', () => {
  console.log('Redis connection established successfully');
});

// Promisify các phương thức Redis
const getAsync = promisify(redisClient.get).bind(redisClient);
const setAsync = promisify(redisClient.set).bind(redisClient);
const delAsync = promisify(redisClient.del).bind(redisClient);
const expireAsync = promisify(redisClient.expire).bind(redisClient);

/**
 * Lưu token vào blacklist
 * @param {String} token - JWT token
 * @param {Number} expireTime - Thời gian hết hạn (giây)
 */
const addToBlacklist = async (token, expireTime) => {
  await setAsync(`bl_${token}`, '1');
  await expireAsync(`bl_${token}`, expireTime);
};

/**
 * Kiểm tra token có trong blacklist không
 * @param {String} token - JWT token
 * @returns {Boolean} Kết quả kiểm tra
 */
const isBlacklisted = async (token) => {
  const result = await getAsync(`bl_${token}`);
  return result === '1';
};

module.exports = {
  redisClient,
  addToBlacklist,
  isBlacklisted
};