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
	serviceURL   string
}

// NewUserAuthHandler creates a new user auth handler
func NewUserAuthHandler(serviceURL string, logger *zap.Logger) (*UserAuthHandler, error) {
	// Create proxy with "user-auth" as serviceID to match our API Gateway design
	serviceProxy, err := proxy.NewServiceProxy(serviceURL, "user-auth", logger)
	if err != nil {
		return nil, err
	}

	return &UserAuthHandler{
		serviceProxy: serviceProxy,
		logger:       logger,
		serviceURL:   serviceURL,
	}, nil
}

// RegisterRoutes registers the user and auth routes
// This method is called on the apiV1 subrouter which already has /api/v1 prefix
// So we only need to specify the relative paths
func (h *UserAuthHandler) RegisterRoutes(router *mux.Router) {
	// Register specific routes first before catch-all routes

	// Auth routes - relative to /api/v1 (since called on apiV1 subrouter)
	// Public routes (no auth required) - được định nghĩa trong middleware
	router.PathPrefix("/user-auth/auth/login").Handler(h.serviceProxy)
	router.PathPrefix("/user-auth/auth/admin/login").Handler(h.serviceProxy)
	router.PathPrefix("/user-auth/auth/register").Handler(h.serviceProxy)
	router.PathPrefix("/user-auth/auth/refresh-token").Handler(h.serviceProxy)
	router.PathPrefix("/user-auth/auth/docs").Handler(h.serviceProxy)
	router.PathPrefix("/user-auth/monitoring/health").Handler(h.serviceProxy)

	// Protected routes (auth required) - cần JWT token
	router.PathPrefix("/user-auth/auth/profile").Handler(h.serviceProxy)         // User profile
	router.PathPrefix("/user-auth/auth/user").Handler(h.serviceProxy)            // User operations
	router.PathPrefix("/user-auth/auth/admin").Handler(h.serviceProxy)           // Admin operations
	router.PathPrefix("/user-auth/auth/logout").Handler(h.serviceProxy)          // Logout
	router.PathPrefix("/user-auth/auth/change-password").Handler(h.serviceProxy) // Change password

	// NEW: Add specific route for user IDs to ensure they're matched correctly
	router.PathPrefix("/user-auth/users/").Handler(h.serviceProxy)

	// User management routes (protected)
	router.PathPrefix("/user-auth/user/").Handler(h.serviceProxy)

	// Catch-all for other auth endpoints - đặt cuối cùng để không override các routes cụ thể
	router.PathPrefix("/user-auth/auth/").Handler(h.serviceProxy)

	// Root auth service endpoint
	router.PathPrefix("/user-auth/auth").Handler(h.serviceProxy)

	// Add a final catch-all route for any remaining user-auth paths
	router.PathPrefix("/user-auth/").Handler(h.serviceProxy)

	h.logger.Info("User & Auth routes registered on apiV1 subrouter",
		zap.String("service_url", h.serviceURL),
		zap.String("service_id", "user-auth"),
		zap.String("effective_prefix", "/api/v1/user-auth/"),
	)
}
