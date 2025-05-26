package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/canxphung/DA_CNPM_242/api_gateway/internal/auth"
	"github.com/canxphung/DA_CNPM_242/api_gateway/internal/config"
	"github.com/canxphung/DA_CNPM_242/api_gateway/internal/handler"
	"github.com/canxphung/DA_CNPM_242/api_gateway/internal/middleware"
	"github.com/gorilla/mux"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

func main() {
	// Load configuration
	cfg := config.LoadConfig()

	// Initialize logger
	logger := initLogger(cfg.Logging)
	defer logger.Sync()

	logger.Info("Starting API Gateway",
		zap.String("port", cfg.Server.Port),
		zap.String("environment", os.Getenv("GO_ENV")),
	)

	// Create JWT manager
	jwtManager := auth.NewJWTManager(&cfg.JWT)

	// Create auth middleware
	authMiddleware := auth.NewAuthMiddleware(jwtManager, logger)

	// Create Prometheus registry
	registry := prometheus.NewRegistry()
	registry.MustRegister(prometheus.NewGoCollector())
	registry.MustRegister(prometheus.NewProcessCollector(prometheus.ProcessCollectorOpts{}))

	// Create metrics middleware
	metricsMiddleware := middleware.NewMetricsMiddleware(registry)

	// Create logging middleware
	loggingMiddleware := middleware.NewLoggingMiddleware(logger)

	// Create CORS middleware
	corsMiddleware := middleware.NewCORSMiddleware([]string{
		"http://localhost:5173", // Vite default dev server
		"http://localhost:3000", // Create React App default
		"http://localhost:3001", // Alternative port
		"*",                     // Allow all origins in development
	})

	// Create router
	router := mux.NewRouter()

	// Apply common middleware - ORDER IS IMPORTANT!
	// CORS must come first to handle preflight requests
	router.Use(corsMiddleware.EnableCORS)
	router.Use(loggingMiddleware.LogRequest)
	router.Use(metricsMiddleware.CollectMetrics)

	// Create API v1 subrouter
	apiV1 := router.PathPrefix("/api/v1").Subrouter()
	apiV1.Use(authMiddleware.Authenticate)

	// Health check endpoint (không cần auth)
	router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"healthy"}`)
	}).Methods("GET")

	// Metrics endpoint (không cần auth)
	router.Handle("/metrics", promhttp.HandlerFor(registry, promhttp.HandlerOpts{}))

	// API v1 health check (không cần auth)
	router.HandleFunc("/api/v1/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"healthy","version":"v1"}`)
	}).Methods("GET")

	// Setup service handlers với API v1 prefix
	setupServiceHandlers(apiV1, cfg, logger)

	// Create HTTP server
	server := &http.Server{
		Addr:         ":" + cfg.Server.Port,
		Handler:      router,
		ReadTimeout:  cfg.Server.ReadTimeout,
		WriteTimeout: cfg.Server.WriteTimeout,
		IdleTimeout:  120 * time.Second,
	}

	// Start server in a goroutine
	go func() {
		logger.Info("Server listening", zap.String("addr", server.Addr))
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Server error", zap.Error(err))
		}
	}()

	// Wait for interrupt signal to gracefully shutdown the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down server...")

	// Create a deadline to wait for
	ctx, cancel := context.WithTimeout(context.Background(), cfg.Server.ShutdownTimeout)
	defer cancel()

	// Doesn't block if no connections, otherwise waits for timeout
	if err := server.Shutdown(ctx); err != nil {
		logger.Fatal("Server forced to shutdown", zap.Error(err))
	}

	logger.Info("Server exited properly")
}

// setupServiceHandlers initializes and registers the handlers for all services
func setupServiceHandlers(router *mux.Router, cfg *config.Config, logger *zap.Logger) {
	// Auth Service
	userAuthHandler, err := handler.NewUserAuthHandler(cfg.Services.UserAuthServiceURL, logger)
	if err != nil {
		logger.Fatal("Failed to create user & auth handler", zap.Error(err))
	}
	userAuthHandler.RegisterRoutes(router)

	// Core Operation Service
	coreOperationHandler, err := handler.NewCoreOperationHandler(cfg.Services.CoreOperationServiceURL, logger)
	if err != nil {
		logger.Fatal("Failed to create core operation handler", zap.Error(err))
	}
	coreOperationHandler.RegisterRoutes(router)

	// AI Service
	aiHandler, err := handler.NewAIHandler(cfg.Services.AIServiceURL, logger)
	if err != nil {
		logger.Fatal("Failed to create AI handler", zap.Error(err))
	}
	aiHandler.RegisterRoutes(router)
}

// initLogger initializes the logger based on configuration
func initLogger(cfg config.LoggingConfig) *zap.Logger {
	var zapConfig zap.Config

	// Choose log level
	level := zap.InfoLevel
	if err := level.Set(cfg.Level); err == nil {
		// Only update if valid level
	}

	// Choose log format: json or console
	if cfg.Format == "console" {
		zapConfig = zap.NewDevelopmentConfig()
		zapConfig.EncoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	} else {
		zapConfig = zap.NewProductionConfig()
	}

	zapConfig.Level = zap.NewAtomicLevelAt(level)

	logger, err := zapConfig.Build()
	if err != nil {
		// Fall back to a basic logger if there's an error
		fmt.Printf("Failed to create logger: %v. Using default logger.\n", err)
		return zap.NewExample()
	}

	return logger
}
