import unittest
from unittest.mock import MagicMock, patch
from fastapi import Request, HTTPException
from litellm.proxy.keycloak_auth import keycloak_auth
from litellm.proxy._types import UserAPIKeyAuth, LitellmUserRoles
import asyncio

class TestKeycloakAuth(unittest.IsolatedAsyncioTestCase):
    async def test_keycloak_auth_success(self):
        mock_request = MagicMock(spec=Request)
        
        with patch("litellm.proxy.keycloak_auth.get_jwks_client") as mock_get_jwks:
            mock_jwks_client = MagicMock()
            mock_signing_key = MagicMock()
            mock_signing_key.key = "mock_public_key"
            mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_get_jwks.return_value = mock_jwks_client
            
            with patch("jwt.decode") as mock_jwt_decode:
                mock_jwt_decode.return_value = {
                    "sub": "test-user-123",
                    "email": "test@example.com",
                    "realm_access": {"roles": ["offline_access", "uma_authorization"]},
                    "resource_access": {
                        "litellm-proxy": {"roles": ["admin"]}
                    }
                }
                
                result = await keycloak_auth(mock_request, "Bearer mock_token")
                
                self.assertIsInstance(result, UserAPIKeyAuth)
                self.assertEqual(result.user_id, "test-user-123")
                self.assertEqual(result.user_role, LitellmUserRoles.PROXY_ADMIN)
                self.assertEqual(result.user_email, "test@example.com")

    async def test_keycloak_auth_failure_invalid_token(self):
        mock_request = MagicMock(spec=Request)
        
        with patch("litellm.proxy.keycloak_auth.get_jwks_client") as mock_get_jwks:
            mock_jwks_client = MagicMock()
            mock_get_jwks.return_value = mock_jwks_client
            
            with patch("jwt.decode") as mock_jwt_decode:
                from jwt import PyJWTError
                mock_jwt_decode.side_effect = PyJWTError("Signature verification failed")
                
                with self.assertRaises(HTTPException) as cm:
                    await keycloak_auth(mock_request, "Bearer invalid_token")
                
                self.assertEqual(cm.exception.status_code, 401)
                self.assertIn("Invalid Token", cm.exception.detail)

    async def test_keycloak_auth_missing_config(self):
        mock_request = MagicMock(spec=Request)
        
        with patch("litellm.proxy.keycloak_auth.KEYCLOAK_URL", None):
            with self.assertRaises(HTTPException) as cm:
                await keycloak_auth(mock_request, "Bearer token")
            
            self.assertEqual(cm.exception.status_code, 500)
            self.assertIn("Keycloak configuration missing", cm.exception.detail)

if __name__ == "__main__":
    unittest.main()
