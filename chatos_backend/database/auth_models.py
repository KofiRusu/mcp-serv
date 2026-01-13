"""
auth_models.py - SQLAlchemy models for authentication and usage logging.

Provides relational storage for:
- User sessions (linked to Keycloak)
- API usage logging
- Feature usage tracking
- Security audit trail
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET, UUID

from chatos_backend.database.models import Base, JSONType


# =============================================================================
# User Session Model
# =============================================================================

class UserSession(Base):
    """
    SQLAlchemy model for user sessions.
    
    Links Keycloak authentication to application sessions,
    enabling user-level tracking across all features.
    """
    __tablename__ = "user_sessions"
    __table_args__ = {"schema": "chatos"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    keycloak_user_id = Column(String(255), nullable=False, index=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255))
    session_id = Column(String(100), nullable=False, index=True)
    roles = Column(JSONType, default=list)
    login_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    logout_time = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(INET)
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "keycloak_user_id": self.keycloak_user_id,
            "username": self.username,
            "email": self.email,
            "session_id": self.session_id,
            "roles": self.roles or [],
            "login_time": self.login_time.isoformat() if self.login_time else None,
            "logout_time": self.logout_time.isoformat() if self.logout_time else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "is_active": self.is_active,
        }

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def end_session(self):
        """Mark session as ended."""
        self.logout_time = datetime.utcnow()
        self.is_active = False


# =============================================================================
# API Usage Log Model
# =============================================================================

class APIUsageLog(Base):
    """
    SQLAlchemy model for API usage logging.
    
    Tracks all API calls with timing, status, and user attribution.
    """
    __tablename__ = "api_usage_log"
    __table_args__ = {"schema": "chatos"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_session_id = Column(UUID(as_uuid=True), ForeignKey("chatos.user_sessions.id", ondelete="SET NULL"))
    endpoint = Column(String(512), nullable=False)
    method = Column(String(10), nullable=False)
    request_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    response_time_ms = Column(Integer)
    status_code = Column(Integer)
    request_size = Column(Integer)
    response_size = Column(Integer)
    error_message = Column(Text)
    request_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_session_id": str(self.user_session_id) if self.user_session_id else None,
            "endpoint": self.endpoint,
            "method": self.method,
            "request_time": self.request_time.isoformat() if self.request_time else None,
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
            "error_message": self.error_message,
        }


# =============================================================================
# Feature Usage Model
# =============================================================================

class FeatureUsage(Base):
    """
    SQLAlchemy model for feature usage tracking.
    
    Tracks user engagement with specific features for analytics.
    """
    __tablename__ = "feature_usage"
    __table_args__ = {"schema": "chatos"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_session_id = Column(UUID(as_uuid=True), ForeignKey("chatos.user_sessions.id", ondelete="SET NULL"))
    feature_name = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    extra_data = Column("metadata", JSONType, default=dict)  # Renamed to avoid reserved word
    duration_ms = Column(Integer)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_session_id": str(self.user_session_id) if self.user_session_id else None,
            "feature_name": self.feature_name,
            "action": self.action,
            "metadata": self.extra_data or {},
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# Audit Log Model
# =============================================================================

class AuditLog(Base):
    """
    SQLAlchemy model for security audit logging.
    
    Tracks sensitive operations for compliance and security review.
    """
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "chatos"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_session_id = Column(UUID(as_uuid=True), ForeignKey("chatos.user_sessions.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    old_value = Column(JSONType)
    new_value = Column(JSONType)
    details = Column(JSONType, default=dict)
    ip_address = Column(INET)
    severity = Column(String(20), default="info")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_session_id": str(self.user_session_id) if self.user_session_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details or {},
            "severity": self.severity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# IP Whitelist Model
# =============================================================================

class IPWhitelist(Base):
    """
    SQLAlchemy model for IP address whitelist.
    
    Controls which IP addresses are allowed to access the system
    when IP whitelisting is enabled.
    """
    __tablename__ = "ip_whitelist"
    __table_args__ = (
        Index("ix_ip_whitelist_active", "is_active"),
        {"schema": "chatos"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ip_address = Column(INET, nullable=False, unique=True)
    description = Column(String(255))
    created_by_session_id = Column(UUID(as_uuid=True), ForeignKey("chatos.user_sessions.id", ondelete="SET NULL"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Optional: CIDR notation support for IP ranges
    cidr_notation = Column(String(50))  # e.g., "192.168.1.0/24"
    
    # Optional: Expiration for temporary access
    expires_at = Column(DateTime)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "description": self.description,
            "cidr_notation": self.cidr_notation,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_expired(self) -> bool:
        """Check if the whitelist entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


# =============================================================================
# Export all models
# =============================================================================

__all__ = [
    "UserSession",
    "APIUsageLog",
    "FeatureUsage",
    "AuditLog",
    "IPWhitelist",
]

