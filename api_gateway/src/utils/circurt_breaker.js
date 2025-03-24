const CircuitBreaker = require('opossum');

// Factory tạo circuit breaker
function createCircuitBreaker(serviceFunction, options = {}) {
  // Cấu hình mặc định
  const defaultOptions = {
    timeout: 5000, // 5 giây timeout
    errorThresholdPercentage: 50, // nếu 50% request lỗi, mở circuit
    resetTimeout: 30000, // sau 30 giây, thử lại
    rollingCountTimeout: 10000, // cửa sổ 10 giây để tính % lỗi
    rollingCountBuckets: 10 // chia thành 10 bucket
  };

  // Kết hợp options
  const circuitOptions = { ...defaultOptions, ...options };
  
  // Tạo circuit breaker
  const breaker = new CircuitBreaker(serviceFunction, circuitOptions);
  
  // Thêm event handlers
  breaker.on('open', () => {
    console.log(`Circuit breaker opened for service`);
  });
  
  breaker.on('close', () => {
    console.log(`Circuit breaker closed for service`);
  });
  
  breaker.on('halfOpen', () => {
    console.log(`Circuit breaker half-opened for service`);
  });

  breaker.on('fallback', (result) => {
    console.log(`Circuit breaker fallback called for service`);
  });

  return breaker;
}

module.exports = { createCircuitBreaker };