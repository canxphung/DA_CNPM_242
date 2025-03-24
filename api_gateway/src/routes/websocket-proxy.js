// src/routes/websocket-proxy.js
const WebSocket = require('ws');
const http = require('http');
const url = require('url');
const jwt = require('jsonwebtoken');
const gatewayConfig = require('../config/gateway.config');

class WebSocketProxy {
  constructor(server) {
    this.server = server;
    this.wss = new WebSocket.Server({ noServer: true });
    this.setupProxies();
  }

  setupProxies() {
    // Khi có kết nối WebSocket mới
    this.server.on('upgrade', (request, socket, head) => {
      const pathname = url.parse(request.url).pathname;
      
      // Tìm cấu hình phù hợp
      const route = this.findRouteForPath(pathname);
      if (!route) {
        socket.destroy();
        return;
      }
      
      // Xác thực nếu cần
      if (route.protected) {
        try {
          const token = this.extractToken(request);
          if (!token) {
            socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
            socket.destroy();
            return;
          }
          
          const decoded = jwt.verify(token, process.env.JWT_SECRET);
          
          // Kiểm tra role
          if (route.roles && route.roles.length > 0) {
            const hasRequiredRole = route.roles.some(role => 
              decoded.roles && decoded.roles.includes(role)
            );
            
            if (!hasRequiredRole) {
              socket.write('HTTP/1.1 403 Forbidden\r\n\r\n');
              socket.destroy();
              return;
            }
          }
          
          // Gán user vào request để sử dụng sau
          request.user = decoded;
        } catch (err) {
          socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
          socket.destroy();
          return;
        }
      }
      
      // Chuyển tiếp kết nối WebSocket
      this.wss.handleUpgrade(request, socket, head, (ws) => {
        // Lấy thông tin service
        const service = gatewayConfig.services[route.service];
        if (!service) {
          ws.close(1011, 'Internal Server Error');
          return;
        }
        
        // Tạo kết nối đến service thực tế
        let targetPath = pathname;
        if (route.stripPath) {
          targetPath = pathname.replace(new RegExp(`^${route.path.replace('*', '')}`), '');
        }
        
        const targetUrl = service.url.replace(/^http/, 'ws') + targetPath;
        const targetWs = new WebSocket(targetUrl);
        
        // Khi nhận được tin nhắn từ client, chuyển tiếp đến service
        ws.on('message', (message) => {
          if (targetWs.readyState === WebSocket.OPEN) {
            targetWs.send(message);
          }
        });
        
        // Khi nhận được tin nhắn từ service, chuyển tiếp đến client
        targetWs.on('message', (message) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(message);
          }
        });
        
        // Xử lý đóng kết nối
        ws.on('close', (code, reason) => {
          targetWs.close(code, reason);
        });
        
        targetWs.on('close', (code, reason) => {
          ws.close(code, reason);
        });
        
        // Xử lý lỗi
        ws.on('error', (err) => {
          console.error('WebSocket client error:', err);
          targetWs.close(1011, 'Client error');
        });
        
        targetWs.on('error', (err) => {
          console.error('WebSocket target error:', err);
          ws.close(1011, 'Server error');
        });
      });
    });
  }
  
  // Tìm route phù hợp với path
  findRouteForPath(path) {
    for (const route of gatewayConfig.routes) {
      const pattern = route.path.replace('*', '.*');
      const regex = new RegExp(`^${pattern}$`);
      if (regex.test(path)) {
        return route;
      }
    }
    return null;
  }
  
  // Trích xuất token từ request
  extractToken(request) {
    const authorization = request.headers.authorization;
    if (!authorization) {
      return null;
    }
    
    const parts = authorization.split(' ');
    if (parts.length !== 2 || parts[0] !== 'Bearer') {
      return null;
    }
    
    return parts[1];
  }
}

module.exports = WebSocketProxy;