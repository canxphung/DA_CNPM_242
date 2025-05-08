package middleware

import (
	"net/http"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"
)

// LoggingMiddleware logs request and response details
type LoggingMiddleware struct {
	logger *zap.Logger
}

// NewLoggingMiddleware creates a new logging middleware
func NewLoggingMiddleware(logger *zap.Logger) *LoggingMiddleware {
	return &LoggingMiddleware{
		logger: logger,
	}
}

// LogRequest logs information about incoming requests and their responses
func (m *LoggingMiddleware) LogRequest(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Generate request ID
		requestID := uuid.New().String()

		// Create a custom response writer to capture status code
		responseWriter := &responseWriter{w, http.StatusOK}

		// Add request ID to response headers
		responseWriter.Header().Set("X-Request-ID", requestID)

		// Log request
		m.logger.Info("Request received",
			zap.String("request_id", requestID),
			zap.String("method", r.Method),
			zap.String("path", r.URL.Path),
			zap.String("remote_addr", r.RemoteAddr),
			zap.String("user_agent", r.UserAgent()),
		)

		// Process request
		next.ServeHTTP(responseWriter, r)

		// Calculate duration
		duration := time.Since(start)

		// Log response
		m.logger.Info("Request completed",
			zap.String("request_id", requestID),
			zap.Int("status", responseWriter.status),
			zap.Duration("duration", duration),
		)
	})
}

// Custom response writer to capture status code
type responseWriter struct {
	http.ResponseWriter
	status int
}

// WriteHeader captures the status code before delegating to the underlying ResponseWriter
func (rw *responseWriter) WriteHeader(code int) {
	rw.status = code
	rw.ResponseWriter.WriteHeader(code)
}
