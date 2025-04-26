# litellm/custom_jwt_auth.py

import jwt
from fastapi import Request, HTTPException
from litellm.proxy._types import UserAPIKeyAuth
import os

# Replace with your actual secret key
# In a real application, load this from environment variables or a secure config
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key")
ALGORITHM = "HS256" # Or the algorithm you use for signing JWTs

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
        payload = jwt.decode(api_key, JWT_SECRET_KEY, algorithms=[ALGORITHM])

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

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")
    except Exception as e:
        # Catch any other exceptions during processing
        raise HTTPException(status_code=500, detail=f"Authentication failed: {e}")