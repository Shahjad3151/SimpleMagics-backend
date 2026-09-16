from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

security = HTTPBearer()

# We use the `bcrypt` library directly instead of passlib. passlib has been
# unmaintained since 2020 and breaks on bcrypt>=4.1 (it reads an internal
# `bcrypt.__about__.__version__` attribute that no longer exists), which is
# exactly why this file used to pin bcrypt==4.0.1 — but that old version has
# no prebuilt wheel for newer Python releases on Windows, forcing a from-source
# build most machines can't do without a C compiler installed. Talking to
# bcrypt directly sidesteps both problems.

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, AttributeError):
        return False

def get_password_hash(password: str) -> str:
    # bcrypt silently ignores bytes beyond 72 — our schema already rejects
    # passwords longer than that at the API layer, so this is just a safety net.
    hashed = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt())
    return hashed.decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    from app.models.user import User
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user

async def get_current_admin(current_user=Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def get_current_user_optional(
    request_credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
):
    """Like get_current_user, but returns None instead of raising when no/invalid token is present.
    Used for lead-gen endpoints (booking forms) that guests may submit without an account."""
    from app.models.user import User
    if not request_credentials:
        return None
    payload = decode_token(request_credentials.credentials)
    if not payload:
        return None
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    return user
