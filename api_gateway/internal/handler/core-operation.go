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
	serviceProxy, err := proxy.NewServiceProxy(serviceURL, "core-operation", logger)
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
func (h *CoreOperationHandler) RegisterRoutes(router *mux.Router) {
	// All core operation endpoints require authentication (handled by middleware)
	router.PathPrefix("/core-operation/").Handler(h.serviceProxy)

	h.logger.Info("Core Operation routes registered",
		zap.String("service_url", h.serviceURL),
	)
}
