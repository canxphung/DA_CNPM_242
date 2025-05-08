package handler

import (
	"github.com/canxphung/DA_CNPM_242/api_gateway/internal/proxy"
	"github.com/gorilla/mux"
	"go.uber.org/zap"
)

// AuthHandler handles requests to the Auth Service
type UserAuthHandler struct {
	serviceProxy *proxy.ServiceProxy
	logger       *zap.Logger
}

// NewAuthHandler creates a new auth handler
func NewUserAuthHandler(serviceURL string, logger *zap.Logger) (*UserAuthHandler, error) {
	serviceProxy, err := proxy.NewServiceProxy(serviceURL, "auth", logger)
	if err != nil {
		return nil, err
	}

	return &UserAuthHandler{
		serviceProxy: serviceProxy,
		logger:       logger,
	}, nil
}

// RegisterRoutes registers the auth routes
func (h *UserAuthHandler) RegisterRoutes(router *mux.Router) {
	// No auth required
	router.PathPrefix("/auth/login").Handler(h.serviceProxy)
	router.PathPrefix("/auth/register").Handler(h.serviceProxy)
	router.PathPrefix("/user/").Handler(h.serviceProxy)
	// Auth required (will be handled by auth middleware)
	router.PathPrefix("/auth/").Handler(h.serviceProxy)
}
