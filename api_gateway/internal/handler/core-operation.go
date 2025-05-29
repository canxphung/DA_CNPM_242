package handler

import (
	"github.com/canxphung/DA_CNPM_242/api_gateway/internal/proxy"
	"github.com/gorilla/mux"
	"go.uber.org/zap"
)

// CoreOperationHandler handles requests to the Core Operation Service
type CoreOperationHandler struct {
	serviceProxy *proxy.ServiceProxy
	logger       *zap.Logger
	serviceURL   string
}

// NewCoreOperationHandler creates a new core operation handler
func NewCoreOperationHandler(serviceURL string, logger *zap.Logger) (*CoreOperationHandler, error) {
	serviceProxy, err := proxy.NewServiceProxy(serviceURL, "core-operations", logger)
	if err != nil {
		return nil, err
	}

	return &CoreOperationHandler{
		serviceProxy: serviceProxy,
		logger:       logger,
		serviceURL:   serviceURL,
	}, nil
}

// RegisterRoutes registers the core operation routes
// This method is called on the apiV1 subrouter which already has /api/v1 prefix
func (h *CoreOperationHandler) RegisterRoutes(router *mux.Router) {
	// All core operation endpoints require authentication (handled by middleware)
	// Register with relative path since we're on apiV1 subrouter
	router.PathPrefix("/core-operations/").Handler(h.serviceProxy)

	// Also support the plural form for backward compatibility
	router.PathPrefix("/core-operations/").Handler(h.serviceProxy)

	h.logger.Info("Core Operation routes registered on apiV1 subrouter",
		zap.String("service_url", h.serviceURL),
		zap.String("service_id", "core-operations"),
		zap.String("effective_prefix", "/api/v1/core-operations/"),
	)
}
