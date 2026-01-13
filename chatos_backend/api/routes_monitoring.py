"""
routes_monitoring.py - API routes for system monitoring and session management.

Provides endpoints for:
- Viewing active user sessions
- API usage statistics
- Feature usage analytics
- Session termination
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, desc

from chatos_backend.api.auth_middleware import (
    User,
    require_admin_role,
    get_client_ip,
)
from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.auth_models import (
    UserSession,
    APIUsageLog,
    FeatureUsage,
    AuditLog,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/monitoring", tags=["Monitoring"])


# =============================================================================
# Pydantic Models
# =============================================================================

class SessionResponse(BaseModel):
    """Response model for a user session."""
    id: str
    keycloak_user_id: str
    username: str
    email: Optional[str]
    roles: List[str]
    login_time: datetime
    logout_time: Optional[datetime]
    last_activity: Optional[datetime]
    ip_address: Optional[str]
    is_active: bool
    duration_minutes: Optional[int]


class SessionListResponse(BaseModel):
    """Response model for listing sessions."""
    sessions: List[SessionResponse]
    total: int
    active_count: int


class APIUsageStats(BaseModel):
    """Response model for API usage statistics."""
    total_requests: int
    requests_today: int
    requests_this_hour: int
    avg_response_time_ms: Optional[float]
    error_rate: float
    top_endpoints: List[Dict[str, Any]]
    requests_by_hour: List[Dict[str, Any]]


class FeatureUsageStats(BaseModel):
    """Response model for feature usage statistics."""
    total_actions: int
    actions_today: int
    top_features: List[Dict[str, Any]]
    feature_breakdown: List[Dict[str, Any]]


class SystemHealthResponse(BaseModel):
    """Response model for overall system health."""
    status: str
    active_sessions: int
    requests_last_hour: int
    error_rate_last_hour: float
    database_connected: bool
    timestamp: datetime


class TerminateSessionResponse(BaseModel):
    """Response model for session termination."""
    terminated: int
    message: str


# =============================================================================
# Session Management Endpoints
# =============================================================================

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(require_admin_role),
):
    """
    List user sessions.
    
    Shows who's logged in and when they were last active.
    
    Args:
        active_only: Only show active sessions
        limit: Maximum results to return
        offset: Pagination offset
        user: Authenticated admin user
        
    Returns:
        List of sessions
    """
    try:
        with DatabaseSession() as db:
            query = db.query(UserSession)
            
            if active_only:
                query = query.filter(UserSession.is_active == True)
            
            total = query.count()
            active_count = db.query(UserSession).filter(
                UserSession.is_active == True
            ).count()
            
            sessions = query.order_by(
                desc(UserSession.last_activity)
            ).offset(offset).limit(limit).all()
            
            return SessionListResponse(
                sessions=[
                    SessionResponse(
                        id=str(s.id),
                        keycloak_user_id=s.keycloak_user_id,
                        username=s.username,
                        email=s.email,
                        roles=s.roles or [],
                        login_time=s.login_time,
                        logout_time=s.logout_time,
                        last_activity=s.last_activity,
                        ip_address=str(s.ip_address) if s.ip_address else None,
                        is_active=s.is_active,
                        duration_minutes=int(
                            (datetime.utcnow() - s.login_time).total_seconds() / 60
                        ) if s.login_time else None,
                    )
                    for s in sessions
                ],
                total=total,
                active_count=active_count,
            )
            
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions",
        )


@router.post("/sessions/{session_id}/terminate", response_model=TerminateSessionResponse)
async def terminate_session(
    request: Request,
    session_id: UUID,
    user: User = Depends(require_admin_role),
):
    """
    Terminate a specific user session.
    
    Kicks out a user by ending their session.
    
    Args:
        request: FastAPI request
        session_id: UUID of session to terminate
        user: Authenticated admin user
        
    Returns:
        Termination result
    """
    try:
        with DatabaseSession() as db:
            session = db.query(UserSession).filter(
                UserSession.id == session_id
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found",
                )
            
            if not session.is_active:
                return TerminateSessionResponse(
                    terminated=0,
                    message="Session was already inactive",
                )
            
            # End the session
            session.end_session()
            
            # Create audit log
            client_ip = await get_client_ip(request)
            audit = AuditLog(
                action="session_terminate",
                resource_type="user_session",
                resource_id=str(session_id),
                details={
                    "username": session.username,
                    "terminated_by": user.username,
                },
                ip_address=client_ip,
                severity="warning",
            )
            db.add(audit)
            db.commit()
            
            return TerminateSessionResponse(
                terminated=1,
                message=f"Session for user '{session.username}' terminated",
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to terminate session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate session",
        )


@router.post("/sessions/terminate-all", response_model=TerminateSessionResponse)
async def terminate_all_sessions(
    request: Request,
    exclude_current: bool = True,
    user: User = Depends(require_admin_role),
):
    """
    Terminate all active sessions.
    
    Kicks out everyone! Use carefully.
    
    Args:
        request: FastAPI request
        exclude_current: Don't terminate the admin's own session
        user: Authenticated admin user
        
    Returns:
        Termination result
    """
    try:
        with DatabaseSession() as db:
            query = db.query(UserSession).filter(UserSession.is_active == True)
            
            # Optionally exclude current admin's session
            if exclude_current and user.id:
                query = query.filter(UserSession.keycloak_user_id != user.id)
            
            sessions = query.all()
            count = 0
            
            for session in sessions:
                session.end_session()
                count += 1
            
            # Create audit log
            client_ip = await get_client_ip(request)
            audit = AuditLog(
                action="session_terminate_all",
                resource_type="user_session",
                details={
                    "terminated_count": count,
                    "exclude_current": exclude_current,
                    "terminated_by": user.username,
                },
                ip_address=client_ip,
                severity="critical",
            )
            db.add(audit)
            db.commit()
            
            return TerminateSessionResponse(
                terminated=count,
                message=f"Terminated {count} active sessions",
            )
            
    except Exception as e:
        logger.error(f"Failed to terminate all sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate sessions",
        )


# =============================================================================
# API Usage Statistics Endpoints
# =============================================================================

@router.get("/api-usage", response_model=APIUsageStats)
async def get_api_usage_stats(
    hours: int = 24,
    user: User = Depends(require_admin_role),
):
    """
    Get API usage statistics.
    
    Shows how much the API is being used.
    
    Args:
        hours: Hours of history to include
        user: Authenticated admin user
        
    Returns:
        API usage statistics
    """
    try:
        with DatabaseSession() as db:
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(hours=hours)
            
            # Total requests
            total_requests = db.query(APIUsageLog).count()
            
            # Requests today
            requests_today = db.query(APIUsageLog).filter(
                APIUsageLog.request_time >= day_ago
            ).count()
            
            # Requests this hour
            requests_this_hour = db.query(APIUsageLog).filter(
                APIUsageLog.request_time >= hour_ago
            ).count()
            
            # Average response time
            avg_response = db.query(
                func.avg(APIUsageLog.response_time_ms)
            ).filter(
                APIUsageLog.request_time >= day_ago,
                APIUsageLog.response_time_ms != None
            ).scalar()
            
            # Error rate
            error_count = db.query(APIUsageLog).filter(
                APIUsageLog.request_time >= day_ago,
                APIUsageLog.status_code >= 400
            ).count()
            error_rate = (error_count / requests_today * 100) if requests_today > 0 else 0
            
            # Top endpoints
            top_endpoints_query = db.query(
                APIUsageLog.endpoint,
                func.count(APIUsageLog.id).label('count'),
                func.avg(APIUsageLog.response_time_ms).label('avg_time')
            ).filter(
                APIUsageLog.request_time >= day_ago
            ).group_by(
                APIUsageLog.endpoint
            ).order_by(
                desc('count')
            ).limit(10).all()
            
            top_endpoints = [
                {
                    "endpoint": e.endpoint,
                    "count": e.count,
                    "avg_response_ms": round(e.avg_time, 2) if e.avg_time else None,
                }
                for e in top_endpoints_query
            ]
            
            # Requests by hour
            requests_by_hour = []
            for h in range(min(hours, 24)):
                hour_start = now - timedelta(hours=h+1)
                hour_end = now - timedelta(hours=h)
                count = db.query(APIUsageLog).filter(
                    APIUsageLog.request_time >= hour_start,
                    APIUsageLog.request_time < hour_end
                ).count()
                requests_by_hour.append({
                    "hour": hour_start.strftime("%H:00"),
                    "count": count,
                })
            
            return APIUsageStats(
                total_requests=total_requests,
                requests_today=requests_today,
                requests_this_hour=requests_this_hour,
                avg_response_time_ms=round(avg_response, 2) if avg_response else None,
                error_rate=round(error_rate, 2),
                top_endpoints=top_endpoints,
                requests_by_hour=list(reversed(requests_by_hour)),
            )
            
    except Exception as e:
        logger.error(f"Failed to get API usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API usage statistics",
        )


# =============================================================================
# Feature Usage Statistics Endpoints
# =============================================================================

@router.get("/feature-usage", response_model=FeatureUsageStats)
async def get_feature_usage_stats(
    hours: int = 24,
    user: User = Depends(require_admin_role),
):
    """
    Get feature usage statistics.
    
    Shows which features people are using.
    
    Args:
        hours: Hours of history to include
        user: Authenticated admin user
        
    Returns:
        Feature usage statistics
    """
    try:
        with DatabaseSession() as db:
            now = datetime.utcnow()
            day_ago = now - timedelta(hours=hours)
            
            # Total actions
            total_actions = db.query(FeatureUsage).count()
            
            # Actions today
            actions_today = db.query(FeatureUsage).filter(
                FeatureUsage.created_at >= day_ago
            ).count()
            
            # Top features
            top_features_query = db.query(
                FeatureUsage.feature_name,
                func.count(FeatureUsage.id).label('count')
            ).filter(
                FeatureUsage.created_at >= day_ago
            ).group_by(
                FeatureUsage.feature_name
            ).order_by(
                desc('count')
            ).limit(10).all()
            
            top_features = [
                {"feature": f.feature_name, "count": f.count}
                for f in top_features_query
            ]
            
            # Feature breakdown by action
            feature_breakdown_query = db.query(
                FeatureUsage.feature_name,
                FeatureUsage.action,
                func.count(FeatureUsage.id).label('count')
            ).filter(
                FeatureUsage.created_at >= day_ago
            ).group_by(
                FeatureUsage.feature_name,
                FeatureUsage.action
            ).order_by(
                desc('count')
            ).limit(20).all()
            
            feature_breakdown = [
                {
                    "feature": f.feature_name,
                    "action": f.action,
                    "count": f.count,
                }
                for f in feature_breakdown_query
            ]
            
            return FeatureUsageStats(
                total_actions=total_actions,
                actions_today=actions_today,
                top_features=top_features,
                feature_breakdown=feature_breakdown,
            )
            
    except Exception as e:
        logger.error(f"Failed to get feature usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feature usage statistics",
        )


# =============================================================================
# System Health Endpoint
# =============================================================================

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    user: User = Depends(require_admin_role),
):
    """
    Get overall system health status.
    
    Quick overview of how the system is doing.
    
    Args:
        user: Authenticated admin user
        
    Returns:
        System health status
    """
    try:
        with DatabaseSession() as db:
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            
            # Active sessions
            active_sessions = db.query(UserSession).filter(
                UserSession.is_active == True
            ).count()
            
            # Requests last hour
            requests_last_hour = db.query(APIUsageLog).filter(
                APIUsageLog.request_time >= hour_ago
            ).count()
            
            # Error rate last hour
            errors_last_hour = db.query(APIUsageLog).filter(
                APIUsageLog.request_time >= hour_ago,
                APIUsageLog.status_code >= 400
            ).count()
            error_rate = (errors_last_hour / requests_last_hour * 100) if requests_last_hour > 0 else 0
            
            # Database connectivity (we're already connected if we got here)
            database_connected = True
            
            # Determine overall status
            if error_rate > 10:
                status_str = "degraded"
            elif error_rate > 25:
                status_str = "critical"
            else:
                status_str = "healthy"
            
            return SystemHealthResponse(
                status=status_str,
                active_sessions=active_sessions,
                requests_last_hour=requests_last_hour,
                error_rate_last_hour=round(error_rate, 2),
                database_connected=database_connected,
                timestamp=now,
            )
            
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return SystemHealthResponse(
            status="error",
            active_sessions=0,
            requests_last_hour=0,
            error_rate_last_hour=0,
            database_connected=False,
            timestamp=datetime.utcnow(),
        )


# =============================================================================
# Audit Log Endpoint
# =============================================================================

@router.get("/audit-log")
async def get_audit_log(
    hours: int = 24,
    severity: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(require_admin_role),
):
    """
    Get recent audit log entries.
    
    Shows what sensitive actions have happened.
    
    Args:
        hours: Hours of history to include
        severity: Filter by severity level
        limit: Maximum results
        user: Authenticated admin user
        
    Returns:
        List of audit log entries
    """
    try:
        with DatabaseSession() as db:
            day_ago = datetime.utcnow() - timedelta(hours=hours)
            
            query = db.query(AuditLog).filter(
                AuditLog.created_at >= day_ago
            )
            
            if severity:
                query = query.filter(AuditLog.severity == severity)
            
            entries = query.order_by(
                desc(AuditLog.created_at)
            ).limit(limit).all()
            
            return {
                "entries": [e.to_dict() for e in entries],
                "total": len(entries),
            }
            
    except Exception as e:
        logger.error(f"Failed to get audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log",
        )
