package auth

import (
	"errors"
	"fmt"
	"time"

	"github.com/canxphung/DA_CNPM_242/api_gateway/internal/config"
	"github.com/golang-jwt/jwt/v5"
)

// Claims defines the custom JWT claims structure
type Claims struct {
	UserID string `json:"user_id"`
	Role   string `json:"role"`
	jwt.RegisteredClaims
}

// JWTManager handles JWT token operations
type JWTManager struct {
	secretKey         []byte
	expiration        time.Duration
	refreshExpiration time.Duration
}

// NewJWTManager creates a new JWT manager
func NewJWTManager(config *config.JWTConfig) *JWTManager {
	return &JWTManager{
		secretKey:         []byte(config.SecretKey),
		expiration:        time.Duration(config.ExpirationMinutes) * time.Minute,
		refreshExpiration: time.Duration(config.RefreshExpirationHours) * time.Hour,
	}
}

// GenerateToken creates a new JWT token for the given user
func (m *JWTManager) GenerateToken(userID, role string) (string, error) {
	now := time.Now()

	claims := Claims{
		UserID: userID,
		Role:   role,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(now.Add(m.expiration)),
			IssuedAt:  jwt.NewNumericDate(now),
			NotBefore: jwt.NewNumericDate(now),
			Issuer:    "agriculture-iot-gateway",
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	return token.SignedString(m.secretKey)
}

// ValidateToken validates a JWT token and returns the claims
func (m *JWTManager) ValidateToken(tokenString string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(
		tokenString,
		&Claims{},
		func(token *jwt.Token) (interface{}, error) {
			// Validate the signing algorithm
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
			}
			return m.secretKey, nil
		},
	)

	if err != nil {
		return nil, err
	}

	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, errors.New("invalid token")
	}

	return claims, nil
}
