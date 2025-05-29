package proxy

import (
	"fmt"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"go.uber.org/zap"
)

// ServiceProxy handles proxying requests to backend services
type ServiceProxy struct {
	target    *url.URL
	proxy     *httputil.ReverseProxy
	logger    *zap.Logger
	serviceID string // ID của dịch vụ, ví dụ: "user-auth", "core-operation", "greenhouse-ai"
}

// NewServiceProxy creates a new service proxy
func NewServiceProxy(targetURL string, serviceID string, logger *zap.Logger) (*ServiceProxy, error) {
	// Xác thực serviceID
	validServiceIDs := map[string]bool{
		"user-auth":       true, // User & Auth Service (Node.js)
		"auth":            true, // Backward compatibility
		"core-operations": true,
		"core-operation":  true, // Hỗ trợ cả hai phiên bản của serviceID
		"greenhouse-ai":   true,
	}

	if _, isValid := validServiceIDs[serviceID]; !isValid {
		return nil, fmt.Errorf("invalid service ID: %s", serviceID)
	}

	target, err := url.Parse(targetURL)
	if err != nil {
		return nil, err
	}

	proxy := httputil.NewSingleHostReverseProxy(target)

	// Customize the director to modify the request before sending it to the backend
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		// Gọi director gốc để thiết lập các headers cơ bản (Host, User-Agent, v.v.)
		originalDirector(req)

		// Cập nhật host và scheme của request để khớp với target backend
		req.URL.Scheme = target.Scheme
		req.URL.Host = target.Host

		// IMPORTANT: Add a special header to tell backend services that CORS is being handled by the gateway
		req.Header.Set("X-Backend-CORS-Handled", "true")

		// Lấy đường dẫn gốc từ request đến gateway
		originalPath := req.URL.Path
		proxiedPath := originalPath // Biến tạm để sửa đổi đường dẫn

		// Bước 1: Loại bỏ tiền tố API chung của gateway (/api/v1)
		// Gateway nhận request dạng: /api/v1/{serviceID}/{backendPath}
		const gatewayAPIPrefix = "/api/v1"
		proxiedPath = strings.TrimPrefix(proxiedPath, gatewayAPIPrefix)

		// Bước 2: Xử lý đường dẫn dựa trên serviceID
		switch serviceID {
		case "user-auth":
			// Đối với User & Auth Service (Node.js/Express):
			// Gateway nhận: /api/v1/user-auth/auth/login
			// Cần cắt bỏ /user-auth và giữ lại /auth/login
			// Sau đó thêm lại tiền tố /api/v1 cho Node.js service

			servicePrefix := "/" + serviceID
			proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)

			// Special handling for user paths
			if strings.HasPrefix(proxiedPath, "/users/") {
				// Keep /users/ path for Node.js service
				req.URL.Path = "/api/v1" + proxiedPath
				logger.Debug("User path special handling",
					zap.String("original_path", originalPath),
					zap.String("modified_path", req.URL.Path))
			} else {
				// Node.js Express app được cấu hình với tiền tố API
				// Vì vậy, chúng ta cần đưa tiền tố `/api/v1` trở lại trước khi forward.
				req.URL.Path = gatewayAPIPrefix + proxiedPath

				// Xử lý trường hợp đặc biệt cho root của Node.js service
				if proxiedPath == "/auth" || proxiedPath == "/auth/" {
					req.URL.Path = gatewayAPIPrefix + proxiedPath
				}
			}

		case "auth":
			// Backward compatibility: Đối với User & Auth Service (Node.js/Express)
			// Gateway nhận: /api/v1/auth/login (old format)
			// Node.js Express app được cấu hình với tiền tố API
			req.URL.Path = gatewayAPIPrefix + proxiedPath

			// Xử lý trường hợp đặc biệt cho root của Node.js service
			if proxiedPath == "/auth" || proxiedPath == "/auth/" {
				req.URL.Path = gatewayAPIPrefix + "/" // Trở thành /api/v1/
			}

		case "core-operation", "core-operations":
			// Core Operations Service expects paths like /api/control/..., /api/system/..., /api/sensors/...
			servicePrefix := "/" + serviceID
			proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)

			// Core Ops expects /api prefix on its paths
			if !strings.HasPrefix(proxiedPath, "/api") && !strings.HasPrefix(proxiedPath, "/health") && !strings.HasPrefix(proxiedPath, "/version") {
				req.URL.Path = "/api" + proxiedPath
			} else {
				req.URL.Path = proxiedPath
			}

		case "greenhouse-ai":
			// AI Service expects paths like /api/chat/..., /api/sensors/..., /api/analytics/...
			servicePrefix := "/" + serviceID
			proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)

			// AI Service expects /api prefix on most paths
			if !strings.HasPrefix(proxiedPath, "/api") && !strings.HasPrefix(proxiedPath, "/health") && !strings.HasPrefix(proxiedPath, "/docs") {
				req.URL.Path = "/api" + proxiedPath
			} else {
				req.URL.Path = proxiedPath
			}

		default:
			// Xử lý mặc định cho các serviceID không xác định khác
			servicePrefix := "/" + serviceID
			proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)
			req.URL.Path = proxiedPath
		}

		// Đảm bảo đường dẫn luôn bắt đầu bằng '/' để tránh các lỗi routing
		if !strings.HasPrefix(req.URL.Path, "/") {
			req.URL.Path = "/" + req.URL.Path
		}

		// Log request để debug
		logger.Debug("Proxying request",
			zap.String("service", serviceID),
			zap.String("original_path", originalPath),
			zap.String("proxied_path_to_backend", req.URL.Path),
			zap.String("target_url", target.String()),
			zap.String("method", req.Method),
			zap.String("origin", req.Header.Get("Origin")),
		)

		// Thêm X-Forwarded headers nếu chưa có để backend có thông tin về request gốc
		if _, ok := req.Header["X-Forwarded-For"]; !ok {
			req.Header.Set("X-Forwarded-For", req.RemoteAddr)
		}
		if _, ok := req.Header["X-Forwarded-Proto"]; !ok {
			req.Header.Set("X-Forwarded-Proto", target.Scheme)
		}

		// Thêm X-Gateway-Service header để dịch vụ backend biết request đến từ gateway nào
		req.Header.Set("X-Gateway-Service", serviceID)

		// Chuyển tiếp đường dẫn gốc dưới dạng header trong trường hợp backend cần để logging/debug
		req.Header.Set("X-Original-Path", originalPath)
	}

	// Custom error handler để ghi log chi tiết hơn khi có lỗi proxy
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		logger.Error("Proxy error",
			zap.String("service", serviceID),
			zap.String("url", r.URL.String()),
			zap.Error(err),
			zap.String("client_ip", r.RemoteAddr),
			zap.String("method", r.Method),
			zap.String("origin", r.Header.Get("Origin")),
		)

		// Set CORS headers even on error responses
		if origin := r.Header.Get("Origin"); origin != "" {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Credentials", "true")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD")
			w.Header().Set("Access-Control-Allow-Headers", "Accept, Authorization, Content-Type, X-CSRF-Token, X-Requested-With, Origin, X-Request-ID")
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadGateway) // 502 Bad Gateway

		// Tùy chỉnh thông báo lỗi dựa trên dịch vụ
		var errorMessage string
		switch serviceID {
		case "user-auth", "auth":
			errorMessage = "Dịch vụ xác thực tạm thời không khả dụng"
		case "core-operation", "core-operations":
			errorMessage = "Dịch vụ vận hành cốt lõi tạm thời không khả dụng"
		case "greenhouse-ai":
			errorMessage = "Dịch vụ AI nhà kính tạm thời không khả dụng"
		default:
			errorMessage = "Dịch vụ tạm thời không khả dụng"
		}

		w.Write([]byte(`{"error":"` + errorMessage + `", "details":"` + err.Error() + `"}`))
	}

	// Custom modify response handler to handle CORS conflicts
	proxy.ModifyResponse = func(resp *http.Response) error {
		// Check if the backend has already added CORS headers despite our request
		backendCORS := resp.Header.Get("Access-Control-Allow-Origin")

		if backendCORS != "" {
			// If backend added CORS headers, REMOVE them to prevent conflicts
			logger.Debug("Removing backend CORS headers to prevent conflicts",
				zap.String("backend_cors", backendCORS),
				zap.String("path", resp.Request.URL.Path))

			resp.Header.Del("Access-Control-Allow-Origin")
			resp.Header.Del("Access-Control-Allow-Methods")
			resp.Header.Del("Access-Control-Allow-Headers")
			resp.Header.Del("Access-Control-Allow-Credentials")
			resp.Header.Del("Access-Control-Expose-Headers")
			resp.Header.Del("Access-Control-Max-Age")
		}

		// Add X-Proxied-By header
		resp.Header.Set("X-Proxied-By", "API-Gateway")

		logger.Debug("Response from backend",
			zap.String("service", serviceID),
			zap.Int("status", resp.StatusCode),
			zap.String("path_received_by_backend", resp.Request.URL.Path),
			zap.String("target_url", target.String()),
			zap.String("original_client_path", resp.Request.Header.Get("X-Original-Path")),
			zap.String("method", resp.Request.Method),
		)

		return nil
	}

	// Điều chỉnh timeout dựa trên loại dịch vụ
	var responseTimeout time.Duration
	switch serviceID {
	case "greenhouse-ai":
		// Dịch vụ AI có thể cần nhiều thời gian hơn để xử lý
		responseTimeout = 60 * time.Second
	case "user-auth", "auth":
		// Xác thực nên nhanh
		responseTimeout = 15 * time.Second
	default:
		responseTimeout = 30 * time.Second
	}

	// Custom transport với timeouts để kiểm soát hành vi kết nối đến backend
	proxy.Transport = &http.Transport{
		MaxIdleConns:          100,
		IdleConnTimeout:       90 * time.Second,
		DisableCompression:    true,
		ResponseHeaderTimeout: responseTimeout,
		ExpectContinueTimeout: 1 * time.Second,
	}

	return &ServiceProxy{
		target:    target,
		proxy:     proxy,
		logger:    logger,
		serviceID: serviceID,
	}, nil
}

// ServeHTTP handles the HTTP request by forwarding it through the reverse proxy
func (p *ServiceProxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Handle OPTIONS requests directly
	if r.Method == "OPTIONS" {
		origin := r.Header.Get("Origin")
		if origin != "" {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD")
			w.Header().Set("Access-Control-Allow-Headers", "Accept, Authorization, Content-Type, X-CSRF-Token, X-Requested-With, Origin, X-Request-ID")
			w.Header().Set("Access-Control-Allow-Credentials", "true")
			w.Header().Set("Access-Control-Max-Age", "86400") // 24 hours
		}
		w.WriteHeader(http.StatusOK)
		return
	}

	p.proxy.ServeHTTP(w, r)
}
