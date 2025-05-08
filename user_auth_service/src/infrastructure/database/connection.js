const mongoose = require('mongoose');
const config = require('../config');

// Xử lý các sự kiện kết nối
mongoose.connection.on('connected', () => {
  console.log('MongoDB connection established successfully');
});

mongoose.connection.on('error', (err) => {
  console.error(`MongoDB connection error: ${err}`);
  process.exit(1);
});

mongoose.connection.on('disconnected', () => {
  console.log('MongoDB connection disconnected');
});

// Xử lý sự kiện tắt ứng dụng
process.on('SIGINT', async () => {
  await mongoose.connection.close();
  console.log('MongoDB connection closed due to app termination');
  process.exit(0);
});

// Kết nối đến MongoDB
const connectToDatabase = async () => {
  try {
    await mongoose.connect(config.db.mongo.uri);
  } catch (error) {
    console.error(`Could not connect to MongoDB: ${error.message}`);
    process.exit(1);
  }
};

module.exports = { connectToDatabase };