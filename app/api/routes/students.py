from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, StudentProfile
from app.schemas.schemas import StudentProfileCreate, StudentProfileResponse

router = APIRouter()

@router.post("/profile", response_model=StudentProfileResponse)
async def create_profile(
    profile_data: StudentProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if existing:
        for key, value in profile_data.dict().items():
            setattr(existing, key, value)
        existing.profile_completed = True
        db.commit()
        db.refresh(existing)
        return existing
    profile = StudentProfile(user_id=current_user.id, profile_completed=True, **profile_data.dict())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/profile", response_model=StudentProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.get("/dashboard")
async def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.user import TestSession, Result
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    sessions = db.query(TestSession).filter(TestSession.user_id == current_user.id).all()
    results = db.query(Result).filter(Result.user_id == current_user.id).all()
    return {
        "profile": profile,
        "total_tests": len(sessions),
        "completed_tests": len([s for s in sessions if s.status == "completed"]),
        "latest_result": results[-1] if results else None,
    }
