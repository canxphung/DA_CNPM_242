package middleware

import (
	"bufio"
	"fmt"
	"net"
	"net/http"
	"strings"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// MetricsMiddleware collects metrics about requests
type MetricsMiddleware struct {
	requestCounter   *prometheus.CounterVec
	requestDuration  *prometheus.HistogramVec
	requestsInFlight *prometheus.GaugeVec
}

// NewMetricsMiddleware creates a new metrics middleware
func NewMetricsMiddleware(reg prometheus.Registerer) *MetricsMiddleware {
	const namespace = "api_gateway"

	requestCounter := promauto.With(reg).NewCounterVec(
		prometheus.CounterOpts{
			Namespace: namespace,
			Name:      "requests_total",
			Help:      "Total number of requests by method, path, and status",
		},
		[]string{"method", "path", "service", "status"},
	)

	requestDuration := promauto.With(reg).NewHistogramVec(
		prometheus.HistogramOpts{
			Namespace: namespace,
			Name:      "request_duration_seconds",
			Help:      "Duration of requests in seconds",
			Buckets:   prometheus.DefBuckets,
		},
		[]string{"method", "path", "service"},
	)

	requestsInFlight := promauto.With(reg).NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: namespace,
			Name:      "requests_in_flight",
			Help:      "Current number of requests being processed",
		},
		[]string{"method", "path"},
	)

	return &MetricsMiddleware{
		requestCounter:   requestCounter,
		requestDuration:  requestDuration,
		requestsInFlight: requestsInFlight,
	}
}

// CollectMetrics collects metrics for requests
func (m *MetricsMiddleware) CollectMetrics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		method := r.Method

		// Determine service based on path with improved detection
		service := m.detectService(path)

		// Track in-flight requests
		m.requestsInFlight.WithLabelValues(method, path).Inc()
		defer m.requestsInFlight.WithLabelValues(method, path).Dec()

		// Create a custom response writer to capture status code
		respWriter := &metricsResponseWriter{
			ResponseWriter: w,
			status:         http.StatusOK,
			written:        false,
		}

		// Track request duration
		start := time.Now()
		next.ServeHTTP(respWriter, r)
		duration := time.Since(start).Seconds()

		// Record request count and duration
		status := http.StatusText(respWriter.status)
		m.requestCounter.WithLabelValues(method, path, service, status).Inc()
		m.requestDuration.WithLabelValues(method, path, service).Observe(duration)
	})
}

// detectService determines which service the request is for based on the path
func (m *MetricsMiddleware) detectService(path string) string {
	// Handle gateway endpoints
	if path == "/" || path == "/health" || path == "/metrics" {
		return "gateway"
	}

	// Handle API v1 endpoints
	if strings.HasPrefix(path, "/api/v1/") {
		pathSegments := strings.Split(strings.TrimPrefix(path, "/api/v1/"), "/")
		if len(pathSegments) > 0 {
			switch pathSegments[0] {
			case "user-auth":
				return "user-auth"
			case "core-operation", "core-operations":
				return "core-operation"
			case "greenhouse-ai":
				return "greenhouse-ai"
			case "health":
				return "gateway"
			}
		}
	}

	return "unknown"
}

// Custom response writer for metrics
type metricsResponseWriter struct {
	http.ResponseWriter
	status  int
	written bool
}

// WriteHeader captures the status code for metrics
func (mrw *metricsResponseWriter) WriteHeader(code int) {
	if !mrw.written {
		mrw.status = code
		mrw.ResponseWriter.WriteHeader(code)
	}
}

// Write implements the http.ResponseWriter interface
func (mrw *metricsResponseWriter) Write(data []byte) (int, error) {
	if !mrw.written {
		mrw.written = true
		// Ensure status code is written before body
		if mrw.status == 0 {
			mrw.status = http.StatusOK
		}
		mrw.ResponseWriter.WriteHeader(mrw.status)
	}
	return mrw.ResponseWriter.Write(data)
}

// Flush implements the http.Flusher interface if the underlying ResponseWriter supports it
func (mrw *metricsResponseWriter) Flush() {
	if flusher, ok := mrw.ResponseWriter.(http.Flusher); ok {
		flusher.Flush()
	}
}

// CloseNotify implements the http.CloseNotifier interface if the underlying ResponseWriter supports it
func (mrw *metricsResponseWriter) CloseNotify() <-chan bool {
	if notifier, ok := mrw.ResponseWriter.(http.CloseNotifier); ok {
		return notifier.CloseNotify()
	}
	return nil
}

// Hijack implements the http.Hijacker interface if the underlying ResponseWriter supports it
func (mrw *metricsResponseWriter) Hijack() (net.Conn, *bufio.ReadWriter, error) {
	if hijacker, ok := mrw.ResponseWriter.(http.Hijacker); ok {
		return hijacker.Hijack()
	}
	return nil, nil, fmt.Errorf("ResponseWriter does not support Hijack")
}
