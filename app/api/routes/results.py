from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.user import Result, User, TestSession, StudentProfile

# Results Router
router = APIRouter()

@router.get("/{result_id}")
async def get_result(result_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.query(Result).filter(Result.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    if result.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return result

@router.get("/my/all")
async def get_my_results(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = db.query(Result).filter(Result.user_id == current_user.id).all()
    return results
