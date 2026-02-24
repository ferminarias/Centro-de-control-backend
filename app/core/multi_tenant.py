"""
Multi-tenant security utilities.
Ensures resources can only be accessed by their owning account.
"""
import uuid
from typing import Type, TypeVar

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User

T = TypeVar("T")


class TenantAccessError(Exception):
    """Raised when a user tries to access a resource from another tenant."""
    pass


def verify_tenant_access(
    db: Session,
    model: Type[T],
    resource_id: uuid.UUID,
    user: User,
    tenant_field: str = "cuenta_id"
) -> T:
    """
    Verify that a resource belongs to the user's account.
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        resource_id: ID of the resource to access
        user: Current authenticated user
        tenant_field: Name of the tenant field (default: cuenta_id)
    
    Returns:
        The resource if access is granted
    
    Raises:
        HTTPException: 404 if not found or doesn't belong to tenant
    """
    resource = db.query(model).filter(
        model.id == resource_id,
        getattr(model, tenant_field) == user.cuenta_id
    ).first()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found or access denied"
        )
    
    return resource


def verify_tenant_access_by_user(
    db: Session,
    model: Type[T],
    resource_id: uuid.UUID,
    user: User,
    user_field: str = "user_id"
) -> T:
    """
    Verify that a resource belongs to the user directly (for user-owned resources).
    """
    resource = db.query(model).filter(
        model.id == resource_id,
        getattr(model, user_field) == user.id
    ).first()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found or access denied"
        )
    
    return resource


def require_admin_or_owner(
    user: User,
    resource_owner_id: uuid.UUID,
    admin_permission: str = "*"
) -> bool:
    """
    Check if user is admin or owner of the resource.
    
    Args:
        user: Current user
        resource_owner_id: ID of the resource owner
        admin_permission: Permission that grants admin access
    
    Returns:
        True if access granted
    
    Raises:
        HTTPException: 403 if not authorized
    """
    if user.id == resource_owner_id:
        return True
    
    if admin_permission in (user.permisos or []):
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this resource"
    )


class TenantContext:
    """Helper class for tenant-scoped queries."""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
    
    def query(self, model: Type[T]) -> "TenantQuery[T]":
        """Start a tenant-scoped query."""
        return TenantQuery(self.db, model, self.user.cuenta_id)


class TenantQuery:
    """Query builder that automatically filters by tenant."""
    
    def __init__(self, db: Session, model: Type[T], cuenta_id: uuid.UUID):
        self.db = db
        self.model = model
        self.cuenta_id = cuenta_id
        self._query = db.query(model).filter(
            getattr(model, "cuenta_id") == cuenta_id
        )
    
    def filter(self, *criterion):
        """Add additional filters."""
        self._query = self._query.filter(*criterion)
        return self
    
    def first(self) -> T | None:
        """Get first result."""
        return self._query.first()
    
    def all(self) -> list[T]:
        """Get all results."""
        return self._query.all()
    
    def count(self) -> int:
        """Count results."""
        return self._query.count()
    
    def order_by(self, *criterion):
        """Order results."""
        self._query = self._query.order_by(*criterion)
        return self
    
    def offset(self, offset: int):
        """Add offset."""
        self._query = self._query.offset(offset)
        return self
    
    def limit(self, limit: int):
        """Add limit."""
        self._query = self._query.limit(limit)
        return self


def get_tenant_context(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> TenantContext:
    """Dependency to get tenant context."""
    return TenantContext(db, user)
