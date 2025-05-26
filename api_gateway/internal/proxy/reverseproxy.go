package proxy

import (
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
	serviceID string // ID của dịch vụ, ví dụ: "auth", "core-operations", "greenhouse-ai"
}

// NewServiceProxy creates a new service proxy
func NewServiceProxy(targetURL string, serviceID string, logger *zap.Logger) (*ServiceProxy, error) {
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

		// Lấy đường dẫn gốc từ request đến gateway (ví dụ: "/api/v1/auth/login")
		originalPath := req.URL.Path
		proxiedPath := originalPath // Biến tạm để sửa đổi đường dẫn

		// Bước 1: Loại bỏ tiền tố API chung của gateway (/api/v1)
		// Gateway nhận request dạng: /api/v1/{serviceID}/{backendPath}
		const gatewayAPIPrefix = "/api/v1"
		if strings.HasPrefix(proxiedPath, gatewayAPIPrefix) {
			proxiedPath = strings.TrimPrefix(proxiedPath, gatewayAPIPrefix)
		}

		// Bước 2: Xử lý đường dẫn dựa trên serviceID để phù hợp với yêu cầu của backend
		switch serviceID { // serviceID được capture từ scope của NewServiceProxy
		case "auth":
			// Đối với User & Auth Service (Node.js/Express):
			// Node.js Express app được cấu hình với `app.use(`${config.apiPrefix}/auth`, authRoutes);`
			// Nếu `config.apiPrefix` là `/api/v1`, thì nó mong đợi các request dạng `/api/v1/auth/...`
			// Vì vậy, chúng ta cần đưa tiền tố `/api/v1` trở lại trước khi forward.
			//
			// Ví dụ:
			// Gateway nhận:   /api/v1/auth/login
			// proxiedPath sau Bước 1: /auth/login
			// -> req.URL.Path = "/api/v1/auth/login" (để Node.js có thể xử lý `app.use('/api/v1/auth', authRoutes)`)
			req.URL.Path = gatewayAPIPrefix + proxiedPath

			// Xử lý trường hợp đặc biệt cho root của Node.js service
			// Nếu Gateway nhận /api/v1/auth/ (hoặc chỉ /api/v1/auth)
			// thì proxiedPath sau Bước 1 là /auth (hoặc /auth/)
			// Chúng ta forward nó thành /api/v1/ để khớp với `app.get('/')` của Node.js service
			if proxiedPath == "/auth" || proxiedPath == "/auth/" {
				req.URL.Path = gatewayAPIPrefix + "/" // Trở thành /api/v1/
			}

		case "core-operations", "greenhouse-ai":
			// Đối với Core Operations Service và Greenhouse AI Service (Python/FastAPI):
			// Các dịch vụ này không mong đợi tiền tố /api/v1 hoặc serviceID trong đường dẫn của chúng.
			//
			// Ví dụ (Core Operations):
			// Gateway nhận:   /api/v1/core-operations/health
			// proxiedPath sau Bước 1: /core-operations/health
			// -> proxiedPath sau trim serviceID: /health (FastAPI mong đợi)
			//
			// Ví dụ (Greenhouse AI):
			// Gateway nhận:   /api/v1/greenhouse-ai/api/chat/predict
			// proxiedPath sau Bước 1: /greenhouse-ai/api/chat/predict
			// -> proxiedPath sau trim serviceID: /api/chat/predict (FastAPI mong đợi)
			servicePrefix := "/" + serviceID // serviceID được capture từ scope của NewServiceProxy
			if strings.HasPrefix(proxiedPath, servicePrefix) {
				proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)
			}
			req.URL.Path = proxiedPath // Sử dụng đường dẫn đã cắt

		default:
			// Xử lý mặc định cho các serviceID không xác định khác (nếu có), loại bỏ tiền tố serviceID
			servicePrefix := "/" + serviceID // serviceID được capture từ scope của NewServiceProxy
			if strings.HasPrefix(proxiedPath, servicePrefix) {
				proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)
			}
			req.URL.Path = proxiedPath
		}

		// Đảm bảo đường dẫn luôn bắt đầu bằng '/' để tránh các lỗi routing
		if !strings.HasPrefix(req.URL.Path, "/") {
			req.URL.Path = "/" + req.URL.Path
		}

		// logger được capture từ scope của NewServiceProxy
		logger.Debug("Proxying request",
			zap.String("service", serviceID), // serviceID được capture
			zap.String("original_path", originalPath),
			zap.String("proxied_path_to_backend", req.URL.Path),
			zap.String("target_url", target.String()), // target được capture
		)

		// Thêm X-Forwarded headers nếu chưa có để backend có thông tin về request gốc
		if _, ok := req.Header["X-Forwarded-For"]; !ok {
			req.Header.Set("X-Forwarded-For", req.RemoteAddr)
		}
		if _, ok := req.Header["X-Forwarded-Proto"]; !ok {
			// Sử dụng scheme của target URL để phản ánh giao thức thực tế của backend
			req.Header.Set("X-Forwarded-Proto", target.Scheme)
		}

		// Thêm X-Gateway-Service header để dịch vụ backend biết request đến từ gateway nào
		req.Header.Set("X-Gateway-Service", serviceID) // serviceID được capture

		// Chuyển tiếp đường dẫn gốc dưới dạng header trong trường hợp backend cần để logging/debug
		req.Header.Set("X-Original-Path", originalPath)
	}

	// Custom error handler để ghi log chi tiết hơn khi có lỗi proxy
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		logger.Error("Proxy error", // logger được capture
			zap.String("service", serviceID), // serviceID được capture
			zap.String("url", r.URL.String()),
			zap.Error(err),
			zap.String("client_ip", r.RemoteAddr),
		)

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadGateway) // 502 Bad Gateway
		// Trả về lỗi chi tiết hơn trong môi trường phát triển, hoặc lỗi chung trong prod
		w.Write([]byte(`{"error":"Service temporarily unavailable", "details":"` + err.Error() + `"}`))
	}

	// Custom modify response handler cho mục đích debug hoặc sửa đổi response trước khi trả về client
	proxy.ModifyResponse = func(resp *http.Response) error {
		logger.Debug("Response from backend", // logger được capture
			zap.String("service", serviceID), // serviceID được capture
			zap.Int("status", resp.StatusCode),
			zap.String("path_received_by_backend", resp.Request.URL.Path),                  // Đường dẫn mà backend đã xử lý
			zap.String("target_url", target.String()),                                      // target được capture
			zap.String("original_client_path", resp.Request.Header.Get("X-Original-Path")), // Lấy lại đường dẫn gốc từ header
		)
		// Có thể thêm hoặc sửa đổi headers ở đây, ví dụ:
		// resp.Header.Set("X-Proxied-By", "Go-Gateway")
		return nil
	}

	// Custom transport với timeouts để kiểm soát hành vi kết nối đến backend
	proxy.Transport = &http.Transport{
		MaxIdleConns:          100,
		IdleConnTimeout:       90 * time.Second,
		DisableCompression:    true,
		ResponseHeaderTimeout: 30 * time.Second, // Thời gian chờ nhận header từ backend
		ExpectContinueTimeout: 1 * time.Second,  // Thời gian chờ 100-continue (nếu có)
		// Add other transport settings if needed, e.g., TLSClientConfig
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
	p.proxy.ServeHTTP(w, r)
}
