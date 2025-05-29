package handler

import (
	"github.com/canxphung/DA_CNPM_242/api_gateway/internal/proxy"
	"github.com/gorilla/mux"
	"go.uber.org/zap"
)

// AIHandler handles requests to the AI Training Service
type AIHandler struct {
	serviceProxy *proxy.ServiceProxy
	logger       *zap.Logger
	serviceURL   string
}

// NewAIHandler creates a new AI handler
func NewAIHandler(serviceURL string, logger *zap.Logger) (*AIHandler, error) {
	serviceProxy, err := proxy.NewServiceProxy(serviceURL, "greenhouse-ai", logger)
	if err != nil {
		return nil, err
	}

	return &AIHandler{
		serviceProxy: serviceProxy,
		logger:       logger,
		serviceURL:   serviceURL,
	}, nil
}

// RegisterRoutes registers the AI routes
// This method is called on the apiV1 subrouter which already has /api/v1 prefix
func (h *AIHandler) RegisterRoutes(router *mux.Router) {
	// All AI endpoints require authentication (handled by middleware)
	// Register with relative path since we're on apiV1 subrouter
	router.PathPrefix("/greenhouse-ai/").Handler(h.serviceProxy)

	h.logger.Info("AI routes registered on apiV1 subrouter",
		zap.String("service_url", h.serviceURL),
		zap.String("service_id", "greenhouse-ai"),
		zap.String("effective_prefix", "/api/v1/greenhouse-ai/"),
	)
}
