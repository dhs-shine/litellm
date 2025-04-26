# litellm/custom_jwt_auth.py

import jwt
from fastapi import Request, HTTPException
from litellm.proxy._types import UserAPIKeyAuth
import os
from typing import Optional
# Replace with your actual secret key
# In a real application, load this from environment variables or a secure config
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key")
JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY", "-----BEGIN PUBLIC KEY-----your-rsa-public-key-----END PUBLIC KEY-----")

def get_jwt_key(algorithm: str) -> str:
    if algorithm == "HS256":
        return JWT_SECRET_KEY
    elif algorithm == "RS256":
        return JWT_PUBLIC_KEY
    else:
        raise HTTPException(status_code=400, detail="Unsupported algorithm")

async def user_api_key_auth(request: Request, api_key: str) -> UserAPIKeyAuth:
    """
    Custom authentication handler for JWT.

    Args:
        request: The incoming request object.
        api_key: The JWT string provided in the Authorization header (Bearer <token>).

    Returns:
        UserAPIKeyAuth: An object containing user information if authentication is successful.

    Raises:
        HTTPException: If the JWT is invalid or verification fails.
    """
    try:
        # Assuming api_key is the JWT string
        # Decode and verify the JWT
        header = jwt.get_unverified_header(api_key)
        algorithm: Optional[str] = header.get("alg")
        if algorithm is None:
            raise HTTPException(status_code=400, detail="Algorithm not specified in JWT header")
        key = get_jwt_key(algorithm)
        payload = jwt.decode(api_key, key, algorithms=[algorithm])

        # Extract user information from the payload
        # You can customize this based on your JWT payload structure
        user_id = payload.get("user_id")
        team_id = payload.get("team_id")
        max_budget = payload.get("max_budget") # Optional: if budget is in JWT

        if not user_id:
            # JWT is valid but doesn't contain required user_id claim
            raise HTTPException(status_code=401, detail="Invalid JWT: user_id claim missing")

        # Return UserAPIKeyAuth object
        # The api_key here is typically the user identifier, not the JWT itself
        # We use user_id from the payload as the identifier for logging/tracking
        return UserAPIKeyAuth(api_key=user_id, team_id=team_id, max_budget=max_budget)

    except Exception as e:
        # Catch any other exceptions during processing
        raise HTTPException(status_code=500, detail=f"Authentication failed: {e}")