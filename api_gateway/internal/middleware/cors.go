package middleware

import (
	"net/http"
	"strings"

	"go.uber.org/zap"
)

// CORSMiddleware handles Cross-Origin Resource Sharing
type CORSMiddleware struct {
	// AllowedOrigins contains the list of allowed origins
	AllowedOrigins []string
	logger         *zap.Logger
}

// NewCORSMiddleware creates a new CORS middleware
func NewCORSMiddleware(allowedOrigins []string, logger *zap.Logger) *CORSMiddleware {
	return &CORSMiddleware{
		AllowedOrigins: allowedOrigins,
		logger:         logger,
	}
}

// EnableCORS adds CORS headers to responses
func (m *CORSMiddleware) EnableCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")

		m.logger.Debug("CORS middleware processing request",
			zap.String("method", r.Method),
			zap.String("path", r.URL.Path),
			zap.String("origin", origin))

		// Check if origin is allowed
		allowed := false
		for _, allowedOrigin := range m.AllowedOrigins {
			if allowedOrigin == "*" {
				allowed = true
				break
			}
			if allowedOrigin == origin {
				allowed = true
				break
			}
			// Support wildcard subdomains like *.localhost
			if strings.Contains(allowedOrigin, "*") {
				pattern := strings.ReplaceAll(allowedOrigin, "*", "")
				if strings.Contains(origin, pattern) {
					allowed = true
					break
				}
			}
		}

		// Set CORS headers for allowed origins
		if allowed && origin != "" {
			// Only set the header once
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Vary", "Origin")
			m.logger.Debug("CORS: Origin allowed", zap.String("origin", origin))
		} else if len(m.AllowedOrigins) > 0 && m.AllowedOrigins[0] == "*" {
			// If first origin is *, allow all
			w.Header().Set("Access-Control-Allow-Origin", "*")
			m.logger.Debug("CORS: Wildcard origin allowed")
		} else if origin == "" {
			// Same-origin request, no CORS headers needed
			m.logger.Debug("CORS: Same-origin request, no headers needed")
		} else {
			m.logger.Warn("CORS: Origin not allowed",
				zap.String("origin", origin),
				zap.Strings("allowed_origins", m.AllowedOrigins))
		}

		// Always set these CORS headers for proper handling when origin is present
		if origin != "" {
			w.Header().Set("Access-Control-Allow-Credentials", "true")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD")
			w.Header().Set("Access-Control-Allow-Headers", "Accept, Authorization, Content-Type, X-CSRF-Token, X-Requested-With, Origin, X-Request-ID")
			w.Header().Set("Access-Control-Expose-Headers", "X-Request-ID, X-Proxied-By")
			w.Header().Set("Access-Control-Max-Age", "86400") // Cache preflight for 24 hours
		}

		// Handle preflight requests (OPTIONS method)
		if r.Method == "OPTIONS" {
			m.logger.Debug("CORS: Handling OPTIONS preflight request",
				zap.String("path", r.URL.Path))
			w.WriteHeader(http.StatusOK)
			return
		}

		// Continue with the next handler
		next.ServeHTTP(w, r)
	})
}
