package jwt

import (
	"fmt"
	"time"

	"github.com/golang-jwt/jwt"
)

func SignAPIJWT(secret string) (string, error) {
	tkn := jwt.NewWithClaims(jwt.SigningMethodHS256, &jwt.MapClaims{
		"kid": "isardvdi",
		"exp": time.Now().Add(20 * time.Second).Unix(),
		"data": map[string]interface{}{
			"role_id":     "admin", // we need the role to be admin in order
			"category_id": "default",
			"user_id":     "local-default-admin-admin",
		},
	})

	ss, err := tkn.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign token: %w", err)
	}

	return ss, nil
}
