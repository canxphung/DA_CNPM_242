package auth

import (
	"context"
	"net/http"
	"strings"

	"go.uber.org/zap"
)

// User context key
type contextKey string

const userContextKey contextKey = "user"

// User represents the authenticated user
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

// Authenticate is a middleware that validates JWT tokens
func (m *AuthMiddleware) Authenticate(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Public paths that don't require authentication
		if r.URL.Path == "/health" ||
			r.URL.Path == "/metrics" ||
			strings.HasPrefix(r.URL.Path, "/auth/login") ||
			strings.HasPrefix(r.URL.Path, "/auth/register") {
			next.ServeHTTP(w, r)
			return
		}

		// Extract token from Authorization header
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			http.Error(w, "Authorization header required", http.StatusUnauthorized)
			return
		}

		// Expected format: "Bearer {token}"
		authParts := strings.Split(authHeader, " ")
		if len(authParts) != 2 || authParts[0] != "Bearer" {
			http.Error(w, "Invalid authorization format", http.StatusUnauthorized)
			return
		}

		tokenString := authParts[1]

		// Validate token
		claims, err := m.jwtManager.ValidateToken(tokenString)
		if err != nil {
			m.logger.Warn("Invalid token", zap.Error(err))
			http.Error(w, "Invalid or expired token", http.StatusUnauthorized)
			return
		}

		// Add user info to request context
		user := &User{
			ID:   claims.UserID,
			Role: claims.Role,
		}

		ctx := context.WithValue(r.Context(), userContextKey, user)

		// Continue with the authenticated request
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// GetUserFromContext extracts the user from the request context
func GetUserFromContext(ctx context.Context) *User {
	user, ok := ctx.Value(userContextKey).(*User)
	if !ok {
		return nil
	}
	return user
}
