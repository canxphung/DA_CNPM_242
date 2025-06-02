package config

import (
	"log"
	"time"

	"github.com/joho/godotenv"
	"github.com/spf13/viper"
)

// Config holds all configuration for our application
type Config struct {
	Server   ServerConfig
	Services ServicesConfig
	JWT      JWTConfig
	Logging  LoggingConfig
}

// ServerConfig holds all server-related configuration
type ServerConfig struct {
	Port            string
	ReadTimeout     time.Duration
	WriteTimeout    time.Duration
	ShutdownTimeout time.Duration
}

// ServicesConfig holds the URLs for all microservices
type ServicesConfig struct {
	UserAuthServiceURL      string
	CoreOperationServiceURL string
	AIServiceURL            string
}

// JWTConfig holds JWT configuration
type JWTConfig struct {
	SecretKey              string
	ExpirationMinutes      int
	RefreshExpirationHours int
}

// LoggingConfig holds logging configuration
type LoggingConfig struct {
	Level  string
	Format string
}

// LoadConfig loads the configuration from environment variables and config files
func LoadConfig() *Config {
	// Load .env file if it exists
	// Try multiple possible locations
	err := godotenv.Load()
	if err != nil {
		// Try loading from the current directory where the binary is run
		err = godotenv.Load(".env")
		if err != nil {
			// Try loading from the project root
			err = godotenv.Load("../../.env")
			if err != nil {
				log.Println("Warning: .env file not found or could not be loaded.")
			} else {
				log.Println(".env file loaded successfully from project root.")
			}
		} else {
			log.Println(".env file loaded successfully from current directory.")
		}
	} else {
		log.Println(".env file loaded successfully.")
	}
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath(".")
	viper.AddConfigPath("./config")
	viper.AddConfigPath("/etc/api-gateway")

	// Set defaults
	viper.SetDefault("server.port", "8000")
	viper.SetDefault("server.readTimeout", "30s")
	viper.SetDefault("server.writeTimeout", "30s")
	viper.SetDefault("server.shutdownTimeout", "5s")

	viper.SetDefault("jwt.expirationMinutes", 30)
	viper.SetDefault("jwt.refreshExpirationHours", 24)

	viper.SetDefault("logging.level", "info")
	viper.SetDefault("logging.format", "json")

	// Bind environment variables
	viper.AutomaticEnv()
	viper.SetEnvPrefix("GATEWAY")

	// Map environment variables to config fields
	viper.BindEnv("server.port", "GATEWAY_PORT")
	viper.BindEnv("services.userAuthServiceURL", "USER_AUTH_SERVICE_URL")
	viper.BindEnv("services.coreOperationServiceURL", "CORE_OPERATION_SERVICE_URL")
	viper.BindEnv("services.aiServiceURL", "AI_SERVICE_URL")
	viper.BindEnv("jwt.secretKey", "JWT_SECRET_KEY")

	// Try to read the config file
	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			log.Fatalf("Error reading config file: %s", err)
		}
		// Config file not found; ignore error if desired
		log.Println("No config file found. Using environment variables and defaults.")
	}

	var config Config

	// Parse durations
	readTimeout, err := time.ParseDuration(viper.GetString("server.readTimeout"))
	if err != nil {
		log.Fatalf("Invalid read timeout: %s", err)
	}

	writeTimeout, err := time.ParseDuration(viper.GetString("server.writeTimeout"))
	if err != nil {
		log.Fatalf("Invalid write timeout: %s", err)
	}

	shutdownTimeout, err := time.ParseDuration(viper.GetString("server.shutdownTimeout"))
	if err != nil {
		log.Fatalf("Invalid shutdown timeout: %s", err)
	}

	config.Server = ServerConfig{
		Port:            viper.GetString("server.port"),
		ReadTimeout:     readTimeout,
		WriteTimeout:    writeTimeout,
		ShutdownTimeout: shutdownTimeout,
	}

	config.Services = ServicesConfig{
		UserAuthServiceURL:      viper.GetString("services.userAuthServiceURL"),
		CoreOperationServiceURL: viper.GetString("services.coreOperationServiceURL"),
		AIServiceURL:            viper.GetString("services.aiServiceURL"),
	}

	config.JWT = JWTConfig{
		SecretKey:              viper.GetString("jwt.secretKey"),
		ExpirationMinutes:      viper.GetInt("jwt.expirationMinutes"),
		RefreshExpirationHours: viper.GetInt("jwt.refreshExpirationHours"),
	}

	config.Logging = LoggingConfig{
		Level:  viper.GetString("logging.level"),
		Format: viper.GetString("logging.format"),
	}

	// Validate required configuration
	if config.JWT.SecretKey == "" {
		log.Fatal("JWT secret key is required")
	}

	if config.Services.UserAuthServiceURL == "" {
		log.Fatal("Auth service URL is required")
	}

	if config.Services.CoreOperationServiceURL == "" {
		log.Fatal("Sensor service URL is required")
	}

	if config.Services.AIServiceURL == "" {
		log.Fatal("AI service URL is required")
	}

	return &config
}
