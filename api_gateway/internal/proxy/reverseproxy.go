package proxy

import (
	"fmt"
	"net"
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
	serviceID string
}

// NewServiceProxy creates a new service proxy
func NewServiceProxy(targetURL string, serviceID string, logger *zap.Logger) (*ServiceProxy, error) {
	logger.Info("Creating service proxy",
		zap.String("target_url", targetURL),
		zap.String("service_id", serviceID))

	// Validate serviceID
	validServiceIDs := map[string]bool{
		"user-auth":       true,
		"auth":            true,
		"core-operations": true,
		"core-operation":  true,
		"greenhouse-ai":   true,
	}

	if _, isValid := validServiceIDs[serviceID]; !isValid {
		return nil, fmt.Errorf("invalid service ID: %s", serviceID)
	}

	target, err := url.Parse(targetURL)
	if err != nil {
		logger.Error("Failed to parse target URL",
			zap.String("target_url", targetURL),
			zap.Error(err))
		return nil, fmt.Errorf("failed to parse target URL: %w", err)
	}

	logger.Info("Target URL parsed successfully",
		zap.String("scheme", target.Scheme),
		zap.String("host", target.Host),
		zap.String("path", target.Path))

	proxy := httputil.NewSingleHostReverseProxy(target)

	// Set buffer pool for better memory management
	proxy.BufferPool = newBufferPool()

	// Customize the director to modify the request before sending it to the backend
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		logger.Debug("Proxy Director: Processing request",
			zap.String("service", serviceID),
			zap.String("original_path", req.URL.Path),
			zap.String("method", req.Method))

		logger.Debug("PROXY_DIRECTOR_ENTRY", zap.String("service", serviceID), zap.String("original_client_path", req.URL.Path))

		// Call original director
		originalDirector(req)

		req.URL.Scheme = target.Scheme
		req.URL.Host = target.Host
		req.Header.Set("X-Backend-CORS-Handled", "true")

		originalPath := req.URL.Path
		proxiedPath := originalPath
		logger.Debug("PROXY_DIRECTOR_AFTER_ORIGINAL",
			zap.String("service", serviceID),
			zap.String("path_after_originalDirector", req.URL.Path),
			zap.String("target_scheme", target.Scheme),
			zap.String("target_host", target.Host),
		)

		// Remove /api/v1
		const gatewayAPIPrefix = "/api/v1"
		proxiedPath = strings.TrimPrefix(proxiedPath, gatewayAPIPrefix)

		// Normalize path to avoid multiple leading slashes
		proxiedPath = "/" + strings.TrimLeft(proxiedPath, "/")

		// Process path based on serviceID
		switch serviceID {
		case "user-auth":
			servicePrefix := "/" + serviceID
			proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)
			if strings.HasPrefix(proxiedPath, "/users/") {
				req.URL.Path = "/api/v1" + proxiedPath
			} else {
				req.URL.Path = gatewayAPIPrefix + proxiedPath
			}

		case "auth":
			req.URL.Path = gatewayAPIPrefix + proxiedPath

		case "core-operation", "core-operations":
			servicePrefix := "/" + serviceID
			proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)
			if !strings.HasPrefix(proxiedPath, "/api/") &&
				!strings.HasPrefix(proxiedPath, "/health") &&
				!strings.HasPrefix(proxiedPath, "/version") &&
				!strings.HasPrefix(proxiedPath, "/docs") {
				req.URL.Path = "/api" + proxiedPath
			} else {
				req.URL.Path = proxiedPath
			}

		case "greenhouse-ai":
			servicePrefix := "/" + serviceID
			proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)
			if !strings.HasPrefix(proxiedPath, "/api") &&
				!strings.HasPrefix(proxiedPath, "/health") &&
				!strings.HasPrefix(proxiedPath, "/docs") {
				req.URL.Path = "/api" + proxiedPath
			} else {
				req.URL.Path = proxiedPath
			}

		default:
			logger.Warn("Unknown service ID, using default path handling",
				zap.String("service_id", serviceID))
			servicePrefix := "/" + serviceID
			proxiedPath = strings.TrimPrefix(proxiedPath, servicePrefix)
			req.URL.Path = proxiedPath
		}

		// Ensure path starts with a single slash
		req.URL.Path = "/" + strings.TrimLeft(req.URL.Path, "/")

		logger.Debug("Proxy Director: Request prepared",
			zap.String("final_path", req.URL.Path),
			zap.String("backend_url", fmt.Sprintf("%s://%s%s", req.URL.Scheme, req.URL.Host, req.URL.Path)))

		logger.Info("PROXY_DIRECTOR_FINAL_TARGET", // INFO để dễ thấy
			zap.String("service", serviceID),
			zap.String("method", req.Method),
			zap.String("final_backend_scheme", req.URL.Scheme),
			zap.String("final_backend_host", req.URL.Host),
			zap.String("final_backend_path", req.URL.Path), // Đây là path sẽ gửi đi
			zap.String("full_backend_url", req.URL.String()),
		)
		// Add headers
		req.Header.Set("X-Forwarded-For", req.RemoteAddr)
		req.Header.Set("X-Forwarded-Proto", "http")
		req.Header.Set("X-Gateway-Service", serviceID)
		req.Header.Set("X-Original-Path", originalPath)
	}

	// Custom error handler with better error handling
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		logger.Error("Proxy error occurred",
			zap.String("service", serviceID),
			zap.String("request_url", r.URL.String()),
			zap.String("target_host", target.Host),
			zap.Error(err))

		logger.Error("PROXY_ERROR_HANDLER", // ERROR để dễ thấy
			zap.String("service", serviceID),
			zap.String("request_url_at_error", r.URL.String()),
			zap.String("target_host_at_error", target.Host),
			zap.Error(err), // Lỗi chi tiết
		)
		// Determine appropriate status code
		statusCode := http.StatusBadGateway
		if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
			logger.Error("Backend timeout", zap.String("service", serviceID))
			statusCode = http.StatusGatewayTimeout
		}

		// Set CORS headers for error responses
		if origin := r.Header.Get("Origin"); isValidOrigin(origin) {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Credentials", "true")
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(statusCode)

		errorMsg := fmt.Sprintf(`{"error":"Service temporarily unavailable", "service":"%s", "details":"%s"}`,
			serviceID, err.Error())
		_, _ = w.Write([]byte(errorMsg))
	}

	// Modify response with minimal intervention
	proxy.ModifyResponse = func(resp *http.Response) error {
		logger.Debug("Response received from backend",
			zap.String("service", serviceID),
			zap.Int("status", resp.StatusCode),
			zap.String("content_type", resp.Header.Get("Content-Type")),
			zap.Int64("content_length", resp.ContentLength),
			zap.Any("headers", resp.Header))
		logger.Info("PROXY_MODIFY_RESPONSE", // INFO để dễ thấy
			zap.String("service", serviceID),
			zap.Int("backend_status_code", resp.StatusCode),
			zap.String("backend_content_type", resp.Header.Get("Content-Type")),
			zap.String("backend_content_length_header", resp.Header.Get("Content-Length")),
			zap.Int64("backend_content_length_parsed", resp.ContentLength), // Do Go tự parse
			zap.Strings("backend_transfer_encoding", resp.Header["Transfer-Encoding"]),
			zap.Any("ALL_BACKEND_HEADERS", resp.Header), // Log tất cả các header từ backend
		)

		// Remove backend CORS headers to prevent conflicts
		resp.Header.Del("Access-Control-Allow-Origin")
		resp.Header.Del("Access-Control-Allow-Methods")
		resp.Header.Del("Access-Control-Allow-Headers")
		resp.Header.Del("Access-Control-Allow-Credentials")
		resp.Header.Del("Access-Control-Expose-Headers")
		resp.Header.Del("Access-Control-Max-Age")

		// Add proxy identification
		resp.Header.Set("X-Proxied-By", "API-Gateway")

		return nil
	}

	// Configure transport with appropriate timeouts
	proxy.Transport = &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: (&net.Dialer{
			Timeout:   30 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		ForceAttemptHTTP2:     true,
		MaxIdleConns:          100,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
		MaxIdleConnsPerHost:   10,
		DisableCompression:    false,
		ResponseHeaderTimeout: getTimeoutForService(serviceID),
	}

	return &ServiceProxy{
		target:    target,
		proxy:     proxy,
		logger:    logger,
		serviceID: serviceID,
	}, nil
}

// isValidOrigin checks if the provided origin is allowed
func isValidOrigin(origin string) bool {
	if origin == "" {
		return false
	}
	// Add logic to validate against a list of allowed origins
	// For example, use a configuration file or environment variable
	allowedOrigins := []string{
		"http://localhost:3000", // Example allowed origin
		"https://example.com",
	}
	for _, allowed := range allowedOrigins {
		if origin == allowed {
			return true
		}
	}
	return false
}

// getTimeoutForService returns appropriate timeout for each service
func getTimeoutForService(serviceID string) time.Duration {
	switch serviceID {
	case "greenhouse-ai":
		return 60 * time.Second
	case "user-auth", "auth":
		return 15 * time.Second
	case "core-operation", "core-operations":
		return 45 * time.Second
	default:
		return 30 * time.Second
	}
}

// ServeHTTP handles the HTTP request by forwarding it through the reverse proxy
func (p *ServiceProxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Handle OPTIONS requests directly
	if r.Method == "OPTIONS" {
		p.handleOptionsRequest(w, r)
		return
	}

	// Ensure the ResponseWriter supports flushing
	var flusher http.Flusher
	if f, ok := w.(http.Flusher); !ok {
		p.logger.Warn("ResponseWriter does not support flushing, wrapping it")
		w = &flushResponseWriter{ResponseWriter: w}
	} else {
		flusher = f
	}

	// Forward the request
	p.proxy.ServeHTTP(w, r)

	// Flush if possible
	if flusher != nil {
		flusher.Flush()
	}
}

// handleOptionsRequest handles CORS preflight requests
func (p *ServiceProxy) handleOptionsRequest(w http.ResponseWriter, r *http.Request) {
	origin := r.Header.Get("Origin")
	if isValidOrigin(origin) {
		w.Header().Set("Access-Control-Allow-Origin", origin)
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD")
		w.Header().Set("Access-Control-Allow-Headers", "Accept, Authorization, Content-Type, X-CSRF-Token, X-Requested-With, Origin, X-Request-ID")
		w.Header().Set("Access-Control-Allow-Credentials", "true")
		w.Header().Set("Access-Control-Max-Age", "86400")
	}
	w.WriteHeader(http.StatusOK)
}

// bufferPool implements httputil.BufferPool
type bufferPool struct {
	pool chan []byte
}

func newBufferPool() httputil.BufferPool {
	return &bufferPool{
		pool: make(chan []byte, 100),
	}
}

func (bp *bufferPool) Get() []byte {
	select {
	case buf := <-bp.pool:
		return buf
	default:
		return make([]byte, 32*1024) // 32KB buffer
	}
}

func (bp *bufferPool) Put(buf []byte) {
	select {
	case bp.pool <- buf:
	default:
		// Log discarded buffers for observability
		// Note: Avoid logging sensitive data in production
	}
}

// flushResponseWriter wraps a ResponseWriter to support flushing
type flushResponseWriter struct {
	http.ResponseWriter
}

func (f *flushResponseWriter) Flush() {
	if flusher, ok := f.ResponseWriter.(http.Flusher); ok {
		flusher.Flush()
	}
}

// Ensure flushResponseWriter implements http.Flusher
var _ http.Flusher = &flushResponseWriter{}
