package auth

import (
	"context"
	"net/http"
	"strings"

	"go.uber.org/zap"
)

// User context key được dùng để lưu trữ thông tin người dùng đã xác thực vào context của request
type contextKey string

const userContextKey contextKey = "user"

// User represents the authenticated user (thông tin được lấy từ JWT)
type User struct {
	ID   string
	Role string
}

// AuthMiddleware provides JWT authentication middleware
type AuthMiddleware struct {
	jwtManager *JWTManager
	logger     *zap.Logger
}

// NewAuthMiddleware creates a new auth middleware
func NewAuthMiddleware(jwtManager *JWTManager, logger *zap.Logger) *AuthMiddleware {
	return &AuthMiddleware{
		jwtManager: jwtManager,
		logger:     logger,
	}
}

// Authenticate là một middleware xác thực JWT.
// Nó cho phép các đường dẫn công khai (public paths) đi qua mà không cần xác thực.
func (m *AuthMiddleware) Authenticate(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Log all requests that reach the auth middleware
		m.logger.Debug("Auth middleware processing request",
			zap.String("method", r.Method),
			zap.String("path", r.URL.Path),
			zap.String("origin", r.Header.Get("Origin")))

		// Always allow OPTIONS requests (CORS preflight) to pass through
		if r.Method == "OPTIONS" {
			m.logger.Debug("Auth middleware: OPTIONS request detected, passing through",
				zap.String("path", r.URL.Path))
			next.ServeHTTP(w, r)
			return
		}

		// Danh sách các đường dẫn công khai (không yêu cầu xác thực).
		// Các đường dẫn này phải là *đường dẫn đầy đủ mà Gateway nhận được từ client*.
		publicPaths := []string{
			// Gateway's own common endpoints
			"/",              // Gateway root endpoint
			"/health",        // Gateway health check
			"/metrics",       // Prometheus metrics endpoint
			"/api/v1/health", // Common API versioned health check

			// === User & Auth Service (Node.js) endpoints ===
			"/api/v1/user-auth/auth/login",         // User login endpoint
			"/api/v1/user-auth/auth/admin/login",   // Admin login endpoint
			"/api/v1/user-auth/auth/register",      // User registration endpoint
			"/api/v1/user-auth/auth/refresh-token", // Refresh access token
			"/api/v1/user-auth/auth/docs",          // Swagger UI for Auth Service
			"/api/v1/user-auth/auth",               // Root of Auth service
			"/api/v1/user-auth/monitoring/health",  // Health check for monitoring
			// user profile and operations
			"/api/v1/user-auth/users",  // gốc
			"/api/v1/user-auth/users/", // để dùng với strings.HasPrefix

			// === Core Operations Service (Python/FastAPI) endpoints ===
			// Hỗ trợ cả hai dạng tiền tố "/api/v1/core-operations" và "/api/v1/core-operation"
			"/api/v1/core-operations", "/api/v1/core-operation", // Root endpoint
			"/api/v1/core-operations/", "/api/v1/core-operation/", // Root endpoint with trailing slash
			"/api/v1/core-operations/health", "/api/v1/core-operation/health", // Health check
			"/api/v1/core-operations/version", "/api/v1/core-operation/version", // Version info
			"/api/v1/core-operations/docs", "/api/v1/core-operation/docs", // Swagger UI

			// System Config endpoints
			"/api/v1/core-operations/system/config", "/api/v1/core-operation/system/config", // GET system config

			// Sensor Data endpoints (NẾU MUỐN CÔNG KHAI - xóa nếu cần authentication)
			"/api/v1/core-operations/sensors/", "/api/v1/core-operation/sensors/", // List available sensors
			"/api/v1/core-operations/sensors/collect", "/api/v1/core-operation/sensors/collect", // Collect sensor data
			"/api/v1/core-operations/sensors/snapshot", "/api/v1/core-operation/sensors/snapshot", // Environmental snapshot
			"/api/v1/core-operations/sensors/light", "/api/v1/core-operation/sensors/light", // Light sensor data
			"/api/v1/core-operations/sensors/temperature", "/api/v1/core-operation/sensors/temperature", // Temperature data
			"/api/v1/core-operations/sensors/humidity", "/api/v1/core-operation/sensors/humidity", // Humidity data
			"/api/v1/core-operations/sensors/soil_moisture", "/api/v1/core-operation/sensors/soil_moisture", // Soil moisture
			"/api/v1/core-operations/sensors/analyze/soil_moisture", "/api/v1/core-operation/sensors/analyze/soil_moisture", // Analysis

			// Status endpoints
			"/api/v1/core-operations/control/status", "/api/v1/core-operation/control/status", // Irrigation system status
			"/api/v1/core-operations/control/pump/status", "/api/v1/core-operation/control/pump/status", // Pump status
			"/api/v1/core-operations/control/schedules", "/api/v1/core-operation/control/schedules", // List irrigation schedules
			"/api/v1/core-operations/control/auto", "/api/v1/core-operation/control/auto", // Auto-irrigation config

			// === Greenhouse AI Service (Python/FastAPI) endpoints ===
			"/api/v1/greenhouse-ai",        // Root endpoint
			"/api/v1/greenhouse-ai/health", // Health check
			"/api/v1/greenhouse-ai/docs",   // Swagger UI

			// Sensors & data endpoints
			"/api/v1/greenhouse-ai/api/sensors/current", // Current sensor data
			"/api/v1/greenhouse-ai/api/sensors/history", // Sensor history

			// Analytics endpoints cho data công khai
			"/api/v1/greenhouse-ai/api/analytics/model-performance", // Model performance
		}

		// Kiểm tra xem đường dẫn hiện tại có phải là công khai hay không
		isPublic := false
		for _, path := range publicPaths {
			// Kiểm tra khớp chính xác hoặc đường dẫn con bắt đầu bằng tiền tố công khai
			if r.URL.Path == path || strings.HasPrefix(r.URL.Path, path) {
				isPublic = true
				m.logger.Debug("Public path match found",
					zap.String("request_path", r.URL.Path),
					zap.String("matched_path", path))
				break
			}
		}

		if isPublic {
			m.logger.Debug("Public path detected, no authentication required",
				zap.String("path", r.URL.Path),
				zap.String("method", r.Method),
			)
			next.ServeHTTP(w, r) // Cho phép request đi tiếp
			return
		}

		// Nếu không phải đường dẫn công khai, kiểm tra Authorization header
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			m.logger.Debug("No authorization header present for protected path",
				zap.String("path", r.URL.Path),
				zap.String("method", r.Method),
			)
			http.Error(w, "Authorization header required", http.StatusUnauthorized)
			return
		}

		// Định dạng expected: "Bearer {token}"
		authParts := strings.Split(authHeader, " ")
		if len(authParts) != 2 || authParts[0] != "Bearer" {
			m.logger.Warn("Invalid authorization header format",
				zap.String("header", authHeader),
				zap.String("path", r.URL.Path),
			)
			http.Error(w, "Invalid authorization format", http.StatusUnauthorized)
			return
		}

		tokenString := authParts[1]

		// Xác thực token JWT
		claims, err := m.jwtManager.ValidateToken(tokenString)
		if err != nil {
			m.logger.Warn("Invalid or expired token",
				zap.Error(err),
				zap.String("path", r.URL.Path),
				zap.String("client_ip", r.RemoteAddr),
			)
			http.Error(w, "Invalid or expired token", http.StatusUnauthorized)
			return
		}

		// Nếu token hợp lệ, thêm thông tin người dùng vào context của request
		user := &User{
			ID:   claims.UserID,
			Role: claims.Role,
		}
		ctx := context.WithValue(r.Context(), userContextKey, user)

		m.logger.Debug("Request authenticated successfully",
			zap.String("user_id", user.ID),
			zap.String("role", user.Role),
			zap.String("path", r.URL.Path),
		)

		// Cho phép request đi tiếp với context đã cập nhật
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// GetUserFromContext extracts the user from the request context.
// Đây là hàm tiện ích để các handler có thể lấy thông tin người dùng.
func GetUserFromContext(ctx context.Context) *User {
	user, ok := ctx.Value(userContextKey).(*User)
	if !ok {
		return nil // Hoặc panic nếu đây là một endpoint được bảo vệ
	}
	return user
}
