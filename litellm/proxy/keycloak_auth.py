import os
import logging
from typing import Union, Optional
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException
from litellm.proxy._types import UserAPIKeyAuth, LitellmUserRoles

logger = logging.getLogger("litellm.proxy.custom_auth.keycloak")

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL") 
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "litellm-proxy")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "account")

def get_jwks_client() -> Optional[PyJWKClient]:
    if not KEYCLOAK_URL or not KEYCLOAK_REALM:
        logger.warning("KEYCLOAK_URL or KEYCLOAK_REALM not set. Keycloak auth will fail.")
        return None
    
    jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    return PyJWKClient(jwks_url)

async def keycloak_auth(request: Request, api_key: str) -> Union[UserAPIKeyAuth, str]:
    """
    Validates Keycloak JWTs and maps claims to LiteLLM user roles.
    """
    try:
        token = api_key.replace("Bearer ", "").strip()
        
        if not token:
            raise HTTPException(status_code=401, detail="Missing API Key/Token")

        jwks_client = get_jwks_client()
        if not jwks_client:
             raise HTTPException(status_code=500, detail="Keycloak configuration missing")

        signing_key = jwks_client.get_signing_key_from_jwt(token)

        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=KEYCLOAK_AUDIENCE,
            options={"verify_aud": False}
        )

        user_id = data.get("sub")
        email = data.get("email")
        
        if not user_id:
             raise HTTPException(status_code=401, detail="Invalid Token: No 'sub' claim")

        realm_roles = data.get("realm_access", {}).get("roles", [])
        resource_access = data.get("resource_access", {})
        client_roles = resource_access.get(KEYCLOAK_CLIENT_ID, {}).get("roles", [])
        
        all_roles = set(realm_roles + client_roles)
        
        user_role = LitellmUserRoles.INTERNAL_USER
        
        if "admin" in all_roles or "litellm-admin" in all_roles:
            user_role = LitellmUserRoles.PROXY_ADMIN
        elif "team-manager" in all_roles:
            user_role = LitellmUserRoles.TEAM

        logger.info(f"Authenticated Keycloak user: {user_id} ({email}) as {user_role}")

        return UserAPIKeyAuth(
            user_id=user_id,
            user_role=user_role,
            user_email=email
        )

    except jwt.PyJWTError as e:
        logger.error(f"JWT Validation Error: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid Token: {str(e)}")
    except Exception as e:
        logger.error(f"Keycloak Auth Unexpected Error: {e}")
        raise HTTPException(status_code=401, detail="Authentication Failed")
