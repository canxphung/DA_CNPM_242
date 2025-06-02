package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
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

	// // Create logging middleware
	loggingMiddleware := middleware.NewLoggingMiddleware(logger)

	// Create CORS middleware - UPDATED: Pass logger to CORS middleware
	corsMiddleware := middleware.NewCORSMiddleware([]string{
		"http://localhost:5173", // Vite default dev server
		"http://localhost:3000", // Create React App default
		"http://localhost:3001", // Alternative port
		"http://localhost:4173", // Vite preview
		"http://127.0.0.1:5173", // Alternative localhost
		"http://127.0.0.1:3000", // Alternative localhost
	}, logger) // Pass logger to CORS middleware

	// Create router
	router := mux.NewRouter()

	// NEW: Handle OPTIONS requests for all routes globally
	router.Methods("OPTIONS").HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		logger.Debug("Global OPTIONS handler processing request",
			zap.String("path", r.URL.Path),
			zap.String("origin", r.Header.Get("Origin")))

		w.Header().Set("Access-Control-Allow-Origin", r.Header.Get("Origin"))
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD")
		w.Header().Set("Access-Control-Allow-Headers", "Accept, Authorization, Content-Type, X-CSRF-Token, X-Requested-With, Origin, X-Request-ID")
		w.Header().Set("Access-Control-Allow-Credentials", "true")
		w.Header().Set("Access-Control-Max-Age", "86400") // 24 hours
		w.WriteHeader(http.StatusOK)
	})

	// Apply common middleware - ORDER IS IMPORTANT!
	// CORS must come first to handle preflight requests
	router.Use(corsMiddleware.EnableCORS)
	router.Use(loggingMiddleware.LogRequest)
	router.Use(metricsMiddleware.CollectMetrics)

	// Health check endpoint (không cần auth) - register trước khi apply auth middleware
	router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"healthy"}`)
	}).Methods("GET")

	// Metrics endpoint (không cần auth)
	router.Handle("/metrics", promhttp.HandlerFor(registry, promhttp.HandlerOpts{}))

	// API v1 health check (không cần auth) - register trước auth middleware
	router.HandleFunc("/api/v1/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"healthy","version":"v1"}`)
	}).Methods("GET")
	router.HandleFunc("/debug/echo", func(w http.ResponseWriter, r *http.Request) {
		logger := logger.With(
			zap.String("handler", "debug-echo"),
			zap.String("method", r.Method),
		)

		// Read request body
		body, err := io.ReadAll(r.Body)
		if err != nil {
			logger.Error("Failed to read request body", zap.Error(err))
			http.Error(w, "Failed to read body", http.StatusBadRequest)
			return
		}
		defer r.Body.Close()

		// Log what we received
		logger.Info("Debug echo handler",
			zap.String("request_body", string(body)),
			zap.Int("body_length", len(body)),
		)

		// Prepare response
		response := map[string]interface{}{
			"message":       "Echo response",
			"method":        r.Method,
			"path":          r.URL.Path,
			"headers":       r.Header,
			"body_received": string(body),
			"timestamp":     time.Now().Format(time.RFC3339),
		}

		// Set headers
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("X-Debug-Handler", "true")

		// Write response
		if err := json.NewEncoder(w).Encode(response); err != nil {
			logger.Error("Failed to encode response", zap.Error(err))
			http.Error(w, "Failed to encode response", http.StatusInternalServerError)
			return
		}

		// Force flush if available
		if flusher, ok := w.(http.Flusher); ok {
			flusher.Flush()
			logger.Debug("Response flushed")
		}

		logger.Info("Debug response sent successfully")
	}).Methods("GET", "POST", "PUT")

	// Debug endpoint to test large response
	router.HandleFunc("/debug/large", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		// Generate large response
		data := make([]map[string]interface{}, 1000)
		for i := 0; i < 1000; i++ {
			data[i] = map[string]interface{}{
				"id":          i,
				"name":        fmt.Sprintf("Item %d", i),
				"description": "This is a test item with some data to make the response larger",
				"timestamp":   time.Now().Format(time.RFC3339),
			}
		}

		response := map[string]interface{}{
			"count": len(data),
			"data":  data,
		}

		if err := json.NewEncoder(w).Encode(response); err != nil {
			logger.Error("Failed to encode large response", zap.Error(err))
			http.Error(w, "Failed to encode response", http.StatusInternalServerError)
			return
		}

		// Force flush
		if flusher, ok := w.(http.Flusher); ok {
			flusher.Flush()
		}
	}).Methods("GET")

	// Debug endpoint to test streaming response
	router.HandleFunc("/debug/stream", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		w.Header().Set("X-Content-Type-Options", "nosniff")

		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
			return
		}

		// Stream data
		for i := 0; i < 10; i++ {
			fmt.Fprintf(w, "Chunk %d: %s\n", i, time.Now().Format(time.RFC3339))
			flusher.Flush()
			time.Sleep(100 * time.Millisecond)
		}

		fmt.Fprint(w, "Stream complete\n")
		flusher.Flush()
	}).Methods("GET")
	// Create API v1 subrouter
	apiV1 := router.PathPrefix("/api/v1").Subrouter()

	// UPDATED: Apply CORS middleware BEFORE auth middleware to API v1 subrouter
	apiV1.Use(corsMiddleware.EnableCORS)

	// Then apply auth middleware to all API v1 routes
	apiV1.Use(authMiddleware.Authenticate)

	// Setup service handlers với API v1 subrouter
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
		logger.Info("Server listening",
			zap.String("addr", server.Addr),
			zap.Strings("services", []string{
				"user-auth: " + cfg.Services.UserAuthServiceURL,
				"core-operations: " + cfg.Services.CoreOperationServiceURL,
				"greenhouse-ai: " + cfg.Services.AIServiceURL,
			}),
		)
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
func setupServiceHandlers(apiV1Router *mux.Router, cfg *config.Config, logger *zap.Logger) {
	// User & Auth Service
	logger.Info("Setting up User & Auth service handler",
		zap.String("url", cfg.Services.UserAuthServiceURL))

	userAuthHandler, err := handler.NewUserAuthHandler(cfg.Services.UserAuthServiceURL, logger)
	if err != nil {
		logger.Fatal("Failed to create user & auth handler", zap.Error(err))
	}
	userAuthHandler.RegisterRoutes(apiV1Router)

	// Core Operation Service
	logger.Info("Setting up Core Operation service handler",
		zap.String("url", cfg.Services.CoreOperationServiceURL))

	coreOperationHandler, err := handler.NewCoreOperationHandler(cfg.Services.CoreOperationServiceURL, logger)
	if err != nil {
		logger.Fatal("Failed to create core operation handler", zap.Error(err))
	}
	coreOperationHandler.RegisterRoutes(apiV1Router)

	// Greenhouse AI Service
	logger.Info("Setting up Greenhouse AI service handler",
		zap.String("url", cfg.Services.AIServiceURL))

	aiHandler, err := handler.NewAIHandler(cfg.Services.AIServiceURL, logger)
	if err != nil {
		logger.Fatal("Failed to create AI handler", zap.Error(err))
	}
	aiHandler.RegisterRoutes(apiV1Router)

	logger.Info("All service handlers registered successfully")
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
