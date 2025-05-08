package middleware

import (
	"net/http"
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

		// Determine service based on path
		service := "unknown"
		if len(path) > 1 {
			pathWithoutLeadingSlash := path[1:]
			switch {
			case len(pathWithoutLeadingSlash) >= 9 && pathWithoutLeadingSlash[:9] == "user-auth":
				service = "user-auth"
			case len(pathWithoutLeadingSlash) >= 14 && pathWithoutLeadingSlash[:14] == "core-operation":
				service = "core-operation"
			case len(pathWithoutLeadingSlash) >= 2 && pathWithoutLeadingSlash[:2] == "ai":
				service = "ai"
			}
		}

		// Track in-flight requests
		m.requestsInFlight.WithLabelValues(method, path).Inc()
		defer m.requestsInFlight.WithLabelValues(method, path).Dec()

		// Create a custom response writer to capture status code
		respWriter := &metricsResponseWriter{w, http.StatusOK}

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

// Custom response writer for metrics
type metricsResponseWriter struct {
	http.ResponseWriter
	status int
}

// WriteHeader captures the status code for metrics
func (mrw *metricsResponseWriter) WriteHeader(code int) {
	mrw.status = code
	mrw.ResponseWriter.WriteHeader(code)
}
