const rateLimit = require('express-rate-limit');
const slowDown = require('express-slow-down');

// Giới hạn số lượng request
const rateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 phút
  max: 100, // giới hạn mỗi IP tối đa 100 request trong 15 phút
  standardHeaders: true, // Trả về thông tin rate limit trong header `RateLimit-*`
  legacyHeaders: false, // Vô hiệu hóa header `X-RateLimit-*`
  message: {
    error: 'Quá nhiều yêu cầu từ địa chỉ IP này, vui lòng thử lại sau 15 phút'
  }
});

// Middleware làm chậm các request quá mức
const speedLimiter = slowDown({
  windowMs: 15 * 60 * 1000, // 15 phút
  delayAfter: 50, // bắt đầu làm chậm sau 50 request
  delayMs: () => 500,    // ✔ static 500 ms
  maxDelayMs: 2000       // ✔ giờ sẽ hiệu lực
});

// Rate limit cụ thể cho API đăng nhập/đăng ký
const authLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 giờ
  max: 10, // giới hạn 10 lần thử đăng nhập trong 1 giờ
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    error: 'Quá nhiều yêu cầu đăng nhập, vui lòng thử lại sau 1 giờ'
  }
});

module.exports = {
  rateLimiter,
  speedLimiter,
  authLimiter
};