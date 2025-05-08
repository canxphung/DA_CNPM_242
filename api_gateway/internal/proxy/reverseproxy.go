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
	serviceID string
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
		originalDirector(req)

		// Update request host and scheme
		req.URL.Scheme = target.Scheme
		req.URL.Host = target.Host

		// Optionally strip the service prefix from the path for microservice compatibility
		// e.g., /sensors/data becomes /data for the sensor service
		if serviceID != "" {
			prefix := "/" + serviceID + "/"
			if strings.HasPrefix(req.URL.Path, prefix) {
				req.URL.Path = "/" + strings.TrimPrefix(req.URL.Path, prefix)
			}
		}

		// Add X-Forwarded headers if not present already
		if _, ok := req.Header["X-Forwarded-For"]; !ok {
			req.Header.Set("X-Forwarded-For", req.RemoteAddr)
		}
		if _, ok := req.Header["X-Forwarded-Proto"]; !ok {
			req.Header.Set("X-Forwarded-Proto", req.URL.Scheme)
		}

		// Add X-Gateway-Service header
		req.Header.Set("X-Gateway-Service", serviceID)
	}

	// Custom error handler
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		logger.Error("Proxy error",
			zap.String("service", serviceID),
			zap.String("url", r.URL.String()),
			zap.Error(err),
		)

		w.WriteHeader(http.StatusBadGateway)
		w.Write([]byte("Service unavailable"))
	}

	// Custom transport with timeouts
	proxy.Transport = &http.Transport{
		MaxIdleConns:       100,
		IdleConnTimeout:    90 * time.Second,
		DisableCompression: true,
	}

	return &ServiceProxy{
		target:    target,
		proxy:     proxy,
		logger:    logger,
		serviceID: serviceID,
	}, nil
}

// ServeHTTP handles the HTTP request
func (p *ServiceProxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	p.proxy.ServeHTTP(w, r)
}
