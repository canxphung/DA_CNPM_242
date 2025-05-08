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
}

// NewAIHandler creates a new AI handler
func NewAIHandler(serviceURL string, logger *zap.Logger) (*AIHandler, error) {
	serviceProxy, err := proxy.NewServiceProxy(serviceURL, "ai", logger)
	if err != nil {
		return nil, err
	}

	return &AIHandler{
		serviceProxy: serviceProxy,
		logger:       logger,
	}, nil
}

// RegisterRoutes registers the AI routes
func (h *AIHandler) RegisterRoutes(router *mux.Router) {
	// All AI endpoints require authentication (handled by middleware)
	router.PathPrefix("/ai/").Handler(h.serviceProxy)
}
