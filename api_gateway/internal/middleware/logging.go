package middleware

import (
	"bufio"
	"fmt"
	"net"
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
		requestID := uuid.New().String()

		// Create a custom response writer to capture status code
		responseWriter := &responseWriter{
			ResponseWriter: w,
			status:         http.StatusOK,
			written:        false,
		}
		responseWriter.Header().Set("X-Request-ID", requestID)

		m.logger.Info("Request received",
			zap.String("request_id", requestID),
			zap.String("method", r.Method),
			zap.String("path", r.URL.Path),
			zap.String("remote_addr", r.RemoteAddr),
			zap.String("user_agent", r.UserAgent()),
		)

		// Process request
		next.ServeHTTP(responseWriter, r)

		duration := time.Since(start)

		// Log completion
		m.logger.Info("Request completed",
			zap.String("request_id", requestID),
			zap.Int("status", responseWriter.status),
			zap.Duration("duration", duration),
			zap.Bool("response_written", responseWriter.written),
		)
	})
}

// Custom response writer to capture status code and ensure proper flushing
type responseWriter struct {
	http.ResponseWriter
	status  int
	written bool
}

func (rw *responseWriter) WriteHeader(code int) {
	if !rw.written {
		rw.status = code
		rw.written = true
		rw.ResponseWriter.WriteHeader(code)
	}
}

func (rw *responseWriter) Write(data []byte) (int, error) {
	if !rw.written {
		rw.written = true
		// Ensure status code is written before body
		if rw.status == 0 {
			rw.status = http.StatusOK
		}
		rw.ResponseWriter.WriteHeader(rw.status)
	}
	return rw.ResponseWriter.Write(data)
}

// Flush implements the http.Flusher interface if the underlying ResponseWriter supports it
func (rw *responseWriter) Flush() {
	if flusher, ok := rw.ResponseWriter.(http.Flusher); ok {
		flusher.Flush()
	}
}

// CloseNotify implements the http.CloseNotifier interface if the underlying ResponseWriter supports it
func (rw *responseWriter) CloseNotify() <-chan bool {
	if notifier, ok := rw.ResponseWriter.(http.CloseNotifier); ok {
		return notifier.CloseNotify()
	}
	return nil
}

// Hijack implements the http.Hijacker interface if the underlying ResponseWriter supports it
func (rw *responseWriter) Hijack() (net.Conn, *bufio.ReadWriter, error) {
	if hijacker, ok := rw.ResponseWriter.(http.Hijacker); ok {
		return hijacker.Hijack()
	}
	return nil, nil, fmt.Errorf("ResponseWriter does not support Hijack")
}
