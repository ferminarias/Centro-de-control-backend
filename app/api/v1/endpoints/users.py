import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_admin_key)])


def _user_to_dict(user: User, role_nombre: str | None = None) -> dict:
    return {
        "id": user.id,
        "cuenta_id": user.cuenta_id,
        "nombre": user.nombre,
        "apellido": user.apellido,
        "email": user.email,
        "username": user.username,
        "role_id": user.role_id,
        "role_nombre": role_nombre,
        "activo": user.activo,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.post(
    "/accounts/{account_id}/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
)
def create_user(
    account_id: uuid.UUID,
    body: UserCreate,
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check email uniqueness within account
    existing = db.query(User).filter(
        User.cuenta_id == account_id, User.email == body.email
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists in this account")

    # Check username uniqueness within account
    existing_user = db.query(User).filter(
        User.cuenta_id == account_id, User.username == body.username
    ).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="A user with this username already exists in this account")

    # Validate role if provided
    role_nombre = None
    if body.role_id:
        role = db.query(Role).filter(
            Role.id == body.role_id, Role.cuenta_id == account_id
        ).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found in this account")
        role_nombre = role.nombre

    user = User(
        cuenta_id=account_id,
        nombre=body.nombre,
        apellido=body.apellido,
        email=body.email,
        username=body.username,
        password_hash=hash_password(body.password),
        role_id=body.role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("User '%s' created for account %s", user.username, account_id)
    return _user_to_dict(user, role_nombre)


@router.get(
    "/accounts/{account_id}/users",
    response_model=UserListResponse,
    summary="List users for an account",
)
def list_users(
    account_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    query = db.query(User).filter(User.cuenta_id == account_id)
    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Fetch role names
    role_ids = {u.role_id for u in users if u.role_id}
    role_names: dict[uuid.UUID, str] = {}
    if role_ids:
        roles = db.query(Role.id, Role.nombre).filter(Role.id.in_(role_ids)).all()
        role_names = {r.id: r.nombre for r in roles}

    items = [
        _user_to_dict(u, role_names.get(u.role_id) if u.role_id else None)
        for u in users
    ]

    return {"items": items, "total": total}


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user details",
)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_nombre = None
    if user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if role:
            role_nombre = role.nombre

    return _user_to_dict(user, role_nombre)


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.nombre is not None:
        user.nombre = body.nombre
    if body.apellido is not None:
        user.apellido = body.apellido
    if body.email is not None:
        # Check uniqueness
        existing = db.query(User).filter(
            User.cuenta_id == user.cuenta_id, User.email == body.email, User.id != user_id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use in this account")
        user.email = body.email
    if body.username is not None:
        existing = db.query(User).filter(
            User.cuenta_id == user.cuenta_id, User.username == body.username, User.id != user_id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Username already in use in this account")
        user.username = body.username
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.role_id is not None:
        role = db.query(Role).filter(
            Role.id == body.role_id, Role.cuenta_id == user.cuenta_id
        ).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found in this account")
        user.role_id = body.role_id
    if body.activo is not None:
        user.activo = body.activo

    db.commit()
    db.refresh(user)

    role_nombre = None
    if user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if role:
            role_nombre = role.nombre

    return _user_to_dict(user, role_nombre)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    logger.info("User '%s' deleted", user.username)
