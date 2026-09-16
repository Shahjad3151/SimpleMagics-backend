from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, get_current_user
from app.core.limiter import limiter
from app.models.user import User, StudentProfile
from app.schemas.schemas import UserCreate, UserLogin, Token, UserResponse

router = APIRouter()

@router.post("/register", response_model=Token)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return Token(access_token=token, user_id=user.id, is_admin=False, profile_completed=False)

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        # Same error for "no such user" and "wrong password" — don't leak
        # which one it was, that's an account-enumeration vector.
        raise HTTPException(status_code=401, detail="Invalid credentials")
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    profile_completed = profile.profile_completed if profile else False
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return Token(access_token=token, user_id=user.id, is_admin=user.is_admin, profile_completed=profile_completed)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
