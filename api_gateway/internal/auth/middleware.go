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
		// Danh sách các đường dẫn công khai (không yêu cầu xác thực).
		// Các đường dẫn này phải là *đường dẫn đầy đủ mà Gateway nhận được từ client*.
		publicPaths := []string{
			// Gateway's own common endpoints
			"/",              // Gateway root endpoint
			"/health",        // Gateway health check (if direct)
			"/metrics",       // Prometheus metrics endpoint (if exposed)
			"/api/v1/health", // Common API versioned health check (if general)

			// User & Auth Service (Node.js) public endpoints
			// Assuming serviceID "auth" is used for routing to Node.js service
			"/api/v1/auth/login",       // User login endpoint
			"/api/v1/auth/admin/login", // Admin login endpoint
			"/api/v1/auth/register",    // User registration endpoint
			"/api/v1/auth/docs",        // Swagger UI for User & Auth Service
			"/api/v1/auth",             // Root of Node.js User & Auth service (maps to Node.js app.get('/'))

			// Core Operations Service (Python/FastAPI) public endpoints
			// Assuming serviceID "core-operations"
			"/api/v1/core-operations",         // Root of Core Operations Service (maps to FastAPI app.get('/'))
			"/api/v1/core-operations/health",  // Health check of Core Operations Service
			"/api/v1/core-operations/version", // Version info of Core Operations Service
			"/api/v1/core-operations/docs",    // Swagger UI for Core Operations Service (if exposed)

			// Greenhouse AI Service (Python/FastAPI) public endpoints
			// Assuming serviceID "greenhouse-ai"
			"/api/v1/greenhouse-ai",        // Root of Greenhouse AI Service (maps to FastAPI app.get('/'))
			"/api/v1/greenhouse-ai/health", // Health check of Greenhouse AI Service
			"/api/v1/greenhouse-ai/docs",   // Swagger UI for Greenhouse AI Service (if exposed)
		}

		// Kiểm tra xem đường dẫn hiện tại có phải là công khai hay không
		isPublic := false
		for _, path := range publicPaths {
			// Kiểm tra khớp chính xác hoặc đường dẫn con bắt đầu bằng tiền tố công khai
			if r.URL.Path == path || strings.HasPrefix(r.URL.Path, path+"/") {
				isPublic = true
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
