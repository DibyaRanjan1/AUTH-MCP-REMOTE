"""
Auth0 OAuth token verification for YouTube MCP Server.
"""

import os
import asyncio
import ssl
from typing import Optional
from wsgiref import headers
import certifi
from jwt import PyJWKClient, decode, InvalidTokenError
from mcp.server.auth.provider import AccessToken, TokenVerifier
import requests
from model.UserInfo import UserInfo


class Auth0TokenVerifier(TokenVerifier):
    """Verifies OAuth tokens issued by Auth0."""

    def __init__(self, domain: str, audience: str, algorithms: Optional[list[str]] = None):
        self.domain = domain
        self.audience = audience
        self.algorithms = algorithms or ["RS256"]
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.issuer = f"https://{domain}/"
        # PyJWKClient handles JWKS fetching and caching
        self.jwks_client = PyJWKClient(self.jwks_url,ssl_context=self.ssl_context)
        self.userinfo_url = f"https://{domain}/userinfo"

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify Auth0 JWT token and return access information."""
        try:
            # Get signing key from JWKS (PyJWKClient handles this synchronously)
            # Run in thread pool to avoid blocking async event loop
            signing_key = await asyncio.to_thread(
                self.jwks_client.get_signing_key_from_jwt, token
            )

            # Decode and verify JWT
            payload = decode(
                token,
                signing_key.key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_aud": False,
                    "verify_iat": True,
                    "verify_exp": True,
                    "verify_iss": True,
                }
            )

            # Extract scopes from token (optional; no enforcement)
            scopes = []
            if "scope" in payload:
                scopes = payload["scope"].split()
            elif "permissions" in payload:
                scopes = payload["permissions"]

            # Return AccessToken model (issuer/audience already validated)
            return AccessToken(
                token=token,
                client_id=payload.get("azp") or payload.get("client_id", "unknown"),
                scopes=scopes,
                expires_at=payload.get("exp"),
                resource=self.audience,
            )

        except InvalidTokenError as e:
            print(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            print(f"Token verification error: {e}")
            return None

    def get_userinfo(self,access_token: str) -> UserInfo:
       headers = {
        "Authorization": f"{access_token}",
        "Content-Type": "application/json"
        }
       response = requests.get(self.userinfo_url, headers=headers, timeout=10)
       response.raise_for_status()

       return UserInfo(**response.json())

def create_auth0_verifier() -> Auth0TokenVerifier:
    """Create Auth0TokenVerifier from environment variables."""
    domain = os.getenv("AUTH0_DOMAIN")
    audience = os.getenv("AUTH0_AUDIENCE")
    algorithms_str = os.getenv("AUTH0_ALGORITHMS", "RS256")

    if not domain:
        raise ValueError("AUTH0_DOMAIN environment variable is required")
    if not audience:
        raise ValueError("AUTH0_AUDIENCE environment variable is required")

    algorithms = [alg.strip() for alg in algorithms_str.split(",")]

    return Auth0TokenVerifier(
        domain=domain,
        audience=audience,
        algorithms=algorithms
    )


