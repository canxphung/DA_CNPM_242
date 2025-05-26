package handler

import (
	"github.com/canxphung/DA_CNPM_242/api_gateway/internal/proxy"
	"github.com/gorilla/mux"
	"go.uber.org/zap"
)

// UserAuthHandler handles requests to the User & Auth Service
type UserAuthHandler struct {
	serviceProxy *proxy.ServiceProxy
	logger       *zap.Logger
	serviceURL   string // Thêm field này để lưu service URL
}

// NewUserAuthHandler creates a new user auth handler
func NewUserAuthHandler(serviceURL string, logger *zap.Logger) (*UserAuthHandler, error) {
	// Create proxy with "auth" as serviceID to match frontend expectations
	serviceProxy, err := proxy.NewServiceProxy(serviceURL, "auth", logger)
	if err != nil {
		return nil, err
	}

	return &UserAuthHandler{
		serviceProxy: serviceProxy,
		logger:       logger,
		serviceURL:   serviceURL, // Lưu serviceURL vào struct
	}, nil
}

// RegisterRoutes registers the user and auth routes
func (h *UserAuthHandler) RegisterRoutes(router *mux.Router) {
	// Auth routes - these match what the frontend is calling
	// Public routes (no auth required)
	router.PathPrefix("/auth/login").Handler(h.serviceProxy)
	router.PathPrefix("/auth/admin/login").Handler(h.serviceProxy)
	router.PathPrefix("/auth/register").Handler(h.serviceProxy)

	// Protected routes (auth required)
	router.PathPrefix("/auth/user").Handler(h.serviceProxy)  // Handles GET all users, GET/DELETE specific user
	router.PathPrefix("/auth/admin").Handler(h.serviceProxy) // Handles admin user operations
	router.PathPrefix("/auth/").Handler(h.serviceProxy)      // Catch-all for other auth endpoints

	// User routes (if separate from auth)
	router.PathPrefix("/user/").Handler(h.serviceProxy)

	h.logger.Info("User & Auth routes registered",
		zap.String("service_url", h.serviceURL),
	)
}
