"""
auth_middleware.py - Authentication and Authorization middleware for ChatOS.

Provides FastAPI dependencies for:
- JWT token validation (Keycloak integration)
- Role-based access control (RBAC)
- IP whitelist verification
- Request logging and auditing
"""

import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import wraps

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

# Security scheme for Bearer tokens
security = HTTPBearer(auto_error=False)

# Keycloak configuration from environment
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "chatos")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "chatos-app")

# JWKS URL for token verification
JWKS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

# Cache for JWKS client
_jwks_client: Optional[PyJWKClient] = None


def get_jwks_client() -> Optional[PyJWKClient]:
    """Get or create JWKS client for token verification."""
    global _jwks_client
    if _jwks_client is None:
        try:
            _jwks_client = PyJWKClient(JWKS_URL)
        except Exception as e:
            logger.warning(f"Failed to initialize JWKS client: {e}")
            return None
    return _jwks_client


class User:
    """Represents an authenticated user from Keycloak token."""
    
    def __init__(self, token_data: Dict[str, Any]):
        self.id = token_data.get("sub", "")
        self.username = token_data.get("preferred_username", "")
        self.email = token_data.get("email", "")
        self.email_verified = token_data.get("email_verified", False)
        self.name = token_data.get("name", "")
        self.given_name = token_data.get("given_name", "")
        self.family_name = token_data.get("family_name", "")
        
        # Extract realm and client roles
        realm_access = token_data.get("realm_access", {})
        self.roles: List[str] = realm_access.get("roles", [])
        
        # Also check resource access for client-specific roles
        resource_access = token_data.get("resource_access", {})
        client_access = resource_access.get(KEYCLOAK_CLIENT_ID, {})
        self.client_roles: List[str] = client_access.get("roles", [])
        
        # Combine all roles
        self.all_roles = list(set(self.roles + self.client_roles))
        
        # Token metadata
        self.token_data = token_data
        self.exp = token_data.get("exp")
        self.iat = token_data.get("iat")
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.all_roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.all_roles for role in roles)
    
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        admin_roles = ["admin", "realm-admin", "chatos-admin"]
        return self.has_any_role(admin_roles)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "roles": self.all_roles,
            "is_admin": self.is_admin(),
        }


async def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token using Keycloak JWKS.
    
    Args:
        token: JWT access token string
        
    Returns:
        Decoded token payload if valid, None otherwise
    """
    jwks_client = get_jwks_client()
    
    if jwks_client is None:
        # Fallback: Try to decode without verification in development
        if os.environ.get("CHATOS_ENV") == "development":
            try:
                # Decode without verification for development
                return jwt.decode(token, options={"verify_signature": False})
            except Exception:
                return None
        return None
    
    try:
        # Get signing key from JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=KEYCLOAK_CLIENT_ID,
            options={"verify_aud": False}  # Keycloak doesn't always set audience
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Extract and validate user from request.
    
    This is an optional dependency - returns None if no valid token.
    Use require_auth for mandatory authentication.
    
    Args:
        request: FastAPI request object
        credentials: Bearer token credentials
        
    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = await verify_token(token)
    
    if payload is None:
        return None
    
    return User(payload)


async def require_auth(
    user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    Require valid authentication.
    
    Raises HTTPException 401 if not authenticated.
    
    Args:
        user: User from get_current_user
        
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: If not authenticated
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin_role(
    user: User = Depends(require_auth)
) -> User:
    """
    Require admin role for access.
    
    Use as a dependency for admin-only endpoints.
    
    Args:
        user: Authenticated user
        
    Returns:
        User object if admin
        
    Raises:
        HTTPException: If user is not an admin
    """
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_role(role: str):
    """
    Create a dependency that requires a specific role.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user: User = Depends(require_role("editor"))):
            ...
    
    Args:
        role: Required role name
        
    Returns:
        Dependency function
    """
    async def role_checker(user: User = Depends(require_auth)) -> User:
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return user
    
    return role_checker


def require_any_role(roles: List[str]):
    """
    Create a dependency that requires any of the specified roles.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user: User = Depends(require_any_role(["admin", "editor"]))):
            ...
    
    Args:
        roles: List of acceptable role names
        
    Returns:
        Dependency function
    """
    async def role_checker(user: User = Depends(require_auth)) -> User:
        if not user.has_any_role(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(roles)}",
            )
        return user
    
    return role_checker


async def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request, considering proxies.
    
    Checks X-Forwarded-For, X-Real-IP headers before falling back
    to direct client IP.
    
    Args:
        request: FastAPI request
        
    Returns:
        Client IP address string
    """
    # Check proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs; first is the client
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


async def verify_ip_whitelist(
    request: Request,
) -> bool:
    """
    Verify client IP is in whitelist.
    
    Args:
        request: FastAPI request
        
    Returns:
        True if IP is whitelisted or whitelist is disabled
    """
    from chatos_backend.database.connection import DatabaseSession
    from chatos_backend.database.auth_models import IPWhitelist
    
    # Get client IP
    client_ip = await get_client_ip(request)
    
    # Check if whitelist enforcement is enabled
    if os.environ.get("CHATOS_ENFORCE_IP_WHITELIST", "false").lower() != "true":
        return True
    
    try:
        with DatabaseSession() as db:
            # Check if IP is in whitelist
            entry = db.query(IPWhitelist).filter(
                IPWhitelist.ip_address == client_ip,
                IPWhitelist.is_active == True
            ).first()
            
            return entry is not None
            
    except Exception as e:
        logger.error(f"IP whitelist check failed: {e}")
        # Fail open in case of database errors
        return True


async def require_whitelisted_ip(
    request: Request,
) -> str:
    """
    Require client IP to be in whitelist.
    
    Use as a dependency for IP-restricted endpoints.
    
    Args:
        request: FastAPI request
        
    Returns:
        Client IP address
        
    Raises:
        HTTPException: If IP is not whitelisted
    """
    client_ip = await get_client_ip(request)
    
    if not await verify_ip_whitelist(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP address {client_ip} is not whitelisted",
        )
    
    return client_ip


# Export all public items
__all__ = [
    "User",
    "security",
    "get_current_user",
    "require_auth",
    "require_admin_role",
    "require_role",
    "require_any_role",
    "get_client_ip",
    "verify_ip_whitelist",
    "require_whitelisted_ip",
]
