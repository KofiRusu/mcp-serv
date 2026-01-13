"""
routes_ip_whitelist.py - API routes for IP whitelist management.

Provides endpoints for:
- Listing whitelisted IPs
- Adding/removing IPs
- Bulk import of IPs
- Checking if an IP is whitelisted
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from pydantic import BaseModel, Field, validator
import ipaddress

from chatos_backend.api.auth_middleware import (
    User,
    require_admin_role,
    get_client_ip,
)
from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.auth_models import IPWhitelist, AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/whitelist", tags=["IP Whitelist"])


# =============================================================================
# Pydantic Models
# =============================================================================

class IPWhitelistCreate(BaseModel):
    """Request model for creating a whitelist entry."""
    ip_address: str = Field(..., description="IP address or CIDR notation")
    description: Optional[str] = Field(None, max_length=255)
    expires_at: Optional[datetime] = None
    
    @validator("ip_address")
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        try:
            # Try parsing as IP address
            ipaddress.ip_address(v)
            return v
        except ValueError:
            pass
        
        try:
            # Try parsing as CIDR network
            ipaddress.ip_network(v, strict=False)
            return v
        except ValueError:
            raise ValueError("Invalid IP address or CIDR notation")


class IPWhitelistUpdate(BaseModel):
    """Request model for updating a whitelist entry."""
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class IPWhitelistResponse(BaseModel):
    """Response model for a whitelist entry."""
    id: str
    ip_address: str
    description: Optional[str]
    cidr_notation: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class IPWhitelistListResponse(BaseModel):
    """Response model for listing whitelist entries."""
    entries: List[IPWhitelistResponse]
    total: int
    active_count: int


class IPCheckResponse(BaseModel):
    """Response model for IP check."""
    ip_address: str
    is_whitelisted: bool
    matched_entry: Optional[IPWhitelistResponse]


class BulkImportResult(BaseModel):
    """Response model for bulk import."""
    added: int
    skipped: int
    errors: List[str]


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response_model=IPWhitelistListResponse)
async def list_whitelisted_ips(
    include_inactive: bool = False,
    include_expired: bool = False,
    user: User = Depends(require_admin_role),
):
    """
    List all whitelisted IP addresses.
    
    Args:
        include_inactive: Include deactivated entries
        include_expired: Include expired entries
        user: Authenticated admin user
        
    Returns:
        List of whitelist entries
    """
    try:
        with DatabaseSession() as db:
            query = db.query(IPWhitelist)
            
            if not include_inactive:
                query = query.filter(IPWhitelist.is_active == True)
            
            if not include_expired:
                query = query.filter(
                    (IPWhitelist.expires_at == None) | 
                    (IPWhitelist.expires_at > datetime.utcnow())
                )
            
            entries = query.order_by(IPWhitelist.created_at.desc()).all()
            
            # Count active entries
            active_count = sum(
                1 for e in entries 
                if e.is_active and not e.is_expired()
            )
            
            return IPWhitelistListResponse(
                entries=[
                    IPWhitelistResponse(
                        id=str(e.id),
                        ip_address=str(e.ip_address),
                        description=e.description,
                        cidr_notation=e.cidr_notation,
                        is_active=e.is_active,
                        expires_at=e.expires_at,
                        created_at=e.created_at,
                        updated_at=e.updated_at,
                    )
                    for e in entries
                ],
                total=len(entries),
                active_count=active_count,
            )
            
    except Exception as e:
        logger.error(f"Failed to list whitelisted IPs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve whitelist entries",
        )


@router.post("", response_model=IPWhitelistResponse, status_code=status.HTTP_201_CREATED)
async def add_ip_to_whitelist(
    request: Request,
    data: IPWhitelistCreate,
    user: User = Depends(require_admin_role),
):
    """
    Add an IP address to the whitelist.
    
    Args:
        request: FastAPI request
        data: IP whitelist entry data
        user: Authenticated admin user
        
    Returns:
        Created whitelist entry
    """
    try:
        with DatabaseSession() as db:
            # Check if IP already exists
            existing = db.query(IPWhitelist).filter(
                IPWhitelist.ip_address == data.ip_address
            ).first()
            
            if existing:
                if existing.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"IP address {data.ip_address} is already whitelisted",
                    )
                else:
                    # Reactivate existing entry
                    existing.is_active = True
                    existing.description = data.description or existing.description
                    existing.expires_at = data.expires_at
                    existing.updated_at = datetime.utcnow()
                    db.commit()
                    db.refresh(existing)
                    entry = existing
            else:
                # Determine if it's CIDR notation
                cidr_notation = None
                try:
                    ipaddress.ip_network(data.ip_address, strict=False)
                    if "/" in data.ip_address:
                        cidr_notation = data.ip_address
                except ValueError:
                    pass
                
                # Create new entry
                entry = IPWhitelist(
                    ip_address=data.ip_address.split("/")[0],  # Store base IP
                    description=data.description,
                    cidr_notation=cidr_notation,
                    expires_at=data.expires_at,
                    is_active=True,
                )
                db.add(entry)
                db.commit()
                db.refresh(entry)
            
            # Create audit log
            client_ip = await get_client_ip(request)
            audit = AuditLog(
                action="ip_whitelist_add",
                resource_type="ip_whitelist",
                resource_id=str(entry.id),
                new_value={"ip_address": data.ip_address},
                ip_address=client_ip,
                severity="info",
            )
            db.add(audit)
            db.commit()
            
            return IPWhitelistResponse(
                id=str(entry.id),
                ip_address=str(entry.ip_address),
                description=entry.description,
                cidr_notation=entry.cidr_notation,
                is_active=entry.is_active,
                expires_at=entry.expires_at,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add IP to whitelist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add IP to whitelist",
        )


@router.get("/check", response_model=IPCheckResponse)
async def check_ip_whitelisted(
    request: Request,
    ip: Optional[str] = None,
    user: User = Depends(require_admin_role),
):
    """
    Check if an IP address is whitelisted.
    
    Args:
        request: FastAPI request
        ip: IP address to check (defaults to client IP)
        user: Authenticated admin user
        
    Returns:
        Whether the IP is whitelisted and matching entry
    """
    # Use provided IP or client IP
    check_ip = ip or await get_client_ip(request)
    
    try:
        with DatabaseSession() as db:
            # Check exact match
            entry = db.query(IPWhitelist).filter(
                IPWhitelist.ip_address == check_ip,
                IPWhitelist.is_active == True,
                (IPWhitelist.expires_at == None) | 
                (IPWhitelist.expires_at > datetime.utcnow())
            ).first()
            
            if entry:
                return IPCheckResponse(
                    ip_address=check_ip,
                    is_whitelisted=True,
                    matched_entry=IPWhitelistResponse(
                        id=str(entry.id),
                        ip_address=str(entry.ip_address),
                        description=entry.description,
                        cidr_notation=entry.cidr_notation,
                        is_active=entry.is_active,
                        expires_at=entry.expires_at,
                        created_at=entry.created_at,
                        updated_at=entry.updated_at,
                    ),
                )
            
            # Check CIDR matches
            try:
                check_addr = ipaddress.ip_address(check_ip)
                
                cidr_entries = db.query(IPWhitelist).filter(
                    IPWhitelist.cidr_notation != None,
                    IPWhitelist.is_active == True,
                    (IPWhitelist.expires_at == None) | 
                    (IPWhitelist.expires_at > datetime.utcnow())
                ).all()
                
                for entry in cidr_entries:
                    try:
                        network = ipaddress.ip_network(entry.cidr_notation, strict=False)
                        if check_addr in network:
                            return IPCheckResponse(
                                ip_address=check_ip,
                                is_whitelisted=True,
                                matched_entry=IPWhitelistResponse(
                                    id=str(entry.id),
                                    ip_address=str(entry.ip_address),
                                    description=entry.description,
                                    cidr_notation=entry.cidr_notation,
                                    is_active=entry.is_active,
                                    expires_at=entry.expires_at,
                                    created_at=entry.created_at,
                                    updated_at=entry.updated_at,
                                ),
                            )
                    except ValueError:
                        continue
                        
            except ValueError:
                pass
            
            return IPCheckResponse(
                ip_address=check_ip,
                is_whitelisted=False,
                matched_entry=None,
            )
            
    except Exception as e:
        logger.error(f"Failed to check IP whitelist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check whitelist",
        )


@router.patch("/{entry_id}", response_model=IPWhitelistResponse)
async def update_whitelist_entry(
    request: Request,
    entry_id: UUID,
    data: IPWhitelistUpdate,
    user: User = Depends(require_admin_role),
):
    """
    Update a whitelist entry.
    
    Args:
        request: FastAPI request
        entry_id: UUID of entry to update
        data: Fields to update
        user: Authenticated admin user
        
    Returns:
        Updated whitelist entry
    """
    try:
        with DatabaseSession() as db:
            entry = db.query(IPWhitelist).filter(
                IPWhitelist.id == entry_id
            ).first()
            
            if not entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Whitelist entry not found",
                )
            
            # Track changes for audit
            old_values = entry.to_dict()
            
            # Apply updates
            if data.description is not None:
                entry.description = data.description
            if data.is_active is not None:
                entry.is_active = data.is_active
            if data.expires_at is not None:
                entry.expires_at = data.expires_at
            
            entry.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(entry)
            
            # Create audit log
            client_ip = await get_client_ip(request)
            audit = AuditLog(
                action="ip_whitelist_update",
                resource_type="ip_whitelist",
                resource_id=str(entry.id),
                old_value=old_values,
                new_value=entry.to_dict(),
                ip_address=client_ip,
                severity="info",
            )
            db.add(audit)
            db.commit()
            
            return IPWhitelistResponse(
                id=str(entry.id),
                ip_address=str(entry.ip_address),
                description=entry.description,
                cidr_notation=entry.cidr_notation,
                is_active=entry.is_active,
                expires_at=entry.expires_at,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update whitelist entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update whitelist entry",
        )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_ip_from_whitelist(
    request: Request,
    entry_id: UUID,
    permanent: bool = False,
    user: User = Depends(require_admin_role),
):
    """
    Remove an IP address from the whitelist.
    
    Args:
        request: FastAPI request
        entry_id: UUID of entry to remove
        permanent: If True, delete permanently; otherwise deactivate
        user: Authenticated admin user
    """
    try:
        with DatabaseSession() as db:
            entry = db.query(IPWhitelist).filter(
                IPWhitelist.id == entry_id
            ).first()
            
            if not entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Whitelist entry not found",
                )
            
            old_values = entry.to_dict()
            
            if permanent:
                db.delete(entry)
                action = "ip_whitelist_delete"
            else:
                entry.is_active = False
                entry.updated_at = datetime.utcnow()
                action = "ip_whitelist_deactivate"
            
            # Create audit log
            client_ip = await get_client_ip(request)
            audit = AuditLog(
                action=action,
                resource_type="ip_whitelist",
                resource_id=str(entry_id),
                old_value=old_values,
                ip_address=client_ip,
                severity="warning",
            )
            db.add(audit)
            db.commit()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove IP from whitelist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove IP from whitelist",
        )


@router.post("/import", response_model=BulkImportResult)
async def import_ips_from_file(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_admin_role),
):
    """
    Bulk import IP addresses from a file.
    
    File should contain one IP address per line.
    Lines starting with # are treated as comments.
    Format: IP_ADDRESS [# description]
    
    Args:
        request: FastAPI request
        file: Uploaded file
        user: Authenticated admin user
        
    Returns:
        Import results
    """
    try:
        content = await file.read()
        lines = content.decode("utf-8").strip().split("\n")
        
        added = 0
        skipped = 0
        errors: List[str] = []
        
        with DatabaseSession() as db:
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Parse line: IP [# description]
                parts = line.split("#", 1)
                ip_str = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else None
                
                # Validate IP
                try:
                    try:
                        ipaddress.ip_address(ip_str)
                    except ValueError:
                        ipaddress.ip_network(ip_str, strict=False)
                except ValueError:
                    errors.append(f"Line {line_num}: Invalid IP '{ip_str}'")
                    continue
                
                # Check if exists
                existing = db.query(IPWhitelist).filter(
                    IPWhitelist.ip_address == ip_str.split("/")[0]
                ).first()
                
                if existing:
                    if not existing.is_active:
                        existing.is_active = True
                        existing.description = description or existing.description
                        added += 1
                    else:
                        skipped += 1
                    continue
                
                # Determine CIDR
                cidr_notation = ip_str if "/" in ip_str else None
                
                # Add entry
                entry = IPWhitelist(
                    ip_address=ip_str.split("/")[0],
                    description=description,
                    cidr_notation=cidr_notation,
                    is_active=True,
                )
                db.add(entry)
                added += 1
            
            db.commit()
            
            # Create audit log
            client_ip = await get_client_ip(request)
            audit = AuditLog(
                action="ip_whitelist_bulk_import",
                resource_type="ip_whitelist",
                details={
                    "filename": file.filename,
                    "added": added,
                    "skipped": skipped,
                    "errors": len(errors),
                },
                ip_address=client_ip,
                severity="info",
            )
            db.add(audit)
            db.commit()
        
        return BulkImportResult(
            added=added,
            skipped=skipped,
            errors=errors,
        )
        
    except Exception as e:
        logger.error(f"Failed to import IPs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import IP addresses",
        )


@router.get("/my-ip")
async def get_my_ip(request: Request):
    """
    Get the current client's IP address.
    
    Useful for users to know their IP for whitelisting.
    No authentication required.
    
    Args:
        request: FastAPI request
        
    Returns:
        Client IP address
    """
    client_ip = await get_client_ip(request)
    return {"ip_address": client_ip}
