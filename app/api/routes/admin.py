from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User, StudentProfile, TestSession, Result

router = APIRouter()

@router.get("/stats")
async def get_admin_stats(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    total_students = db.query(User).filter(User.is_admin == False).count()
    completed = db.query(TestSession).filter(TestSession.status == "completed").count()
    pending = db.query(TestSession).filter(TestSession.status.in_(["pending", "in_progress"])).count()
    
    category_dist = {}
    cats = db.query(StudentProfile.category_fit, func.count(StudentProfile.id)).group_by(StudentProfile.category_fit).all()
    for cat, cnt in cats:
        if cat:
            category_dist[cat.value] = cnt

    avg_score_result = db.query(func.avg(Result.percentage)).scalar()
    avg_score = round(avg_score_result or 0, 1)

    eligibility_dist = {}
    elig = db.query(Result.eligibility_status, func.count(Result.id)).group_by(Result.eligibility_status).all()
    for e, cnt in elig:
        if e:
            eligibility_dist[e.value] = cnt

    return {
        "total_students": total_students,
        "total_tests_completed": completed,
        "total_tests_pending": pending,
        "category_distribution": category_dist,
        "eligibility_distribution": eligibility_dist,
        "avg_score": avg_score
    }

@router.get("/students")
async def get_all_students(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    students = db.query(User).filter(User.is_admin == False).all()
    result = []
    for s in students:
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == s.id).first()
        latest_result = db.query(Result).filter(Result.user_id == s.id).order_by(Result.created_at.desc()).first()
        result.append({
            "id": s.id,
            "email": s.email,
            "created_at": s.created_at,
            "profile": profile,
            "latest_result": latest_result
        })
    return result

@router.get("/students/{student_id}/report")
async def get_student_report(student_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    user = db.query(User).filter(User.id == student_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student not found")
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == student_id).first()
    sessions = db.query(TestSession).filter(TestSession.user_id == student_id).all()
    results = db.query(Result).filter(Result.user_id == student_id).all()
    return {"user": user, "profile": profile, "sessions": sessions, "results": results}
