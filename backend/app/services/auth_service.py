from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest


def normalize_email(email: str) -> str:
    """Normalize an email address for consistent storage and lookup."""
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Fetch a user by normalized email address."""
    normalized = normalize_email(email)
    stmt = select(User).where(User.email == normalized)
    return db.scalar(stmt)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Fetch a user by primary key ID."""
    stmt = select(User).where(User.id == user_id)
    return db.scalar(stmt)


def register_user(db: Session, payload: UserRegisterRequest) -> User:
    """Register a new user after checking for duplicate email addresses."""
    normalized_email = normalize_email(payload.email)
    existing_user = get_user_by_email(db, normalized_email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        full_name=payload.full_name,
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: UserLoginRequest) -> str:
    """Authenticate user credentials and return a signed JWT access token."""
    user = get_user_by_email(db, payload.email)
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return create_access_token(subject=user.id)
