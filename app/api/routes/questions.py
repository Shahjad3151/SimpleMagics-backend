from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.user import Question, Result, User, TestSession, StudentProfile
from app.schemas.schemas import QuestionCreate, QuestionResponse, ResultResponse, AdminStats

# Questions Router
router = APIRouter()

@router.get("/", response_model=List[QuestionResponse])
async def get_questions(
    category: Optional[str] = None,
    domain: Optional[str] = None,
    technology: Optional[str] = None,
    is_profile: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    query = db.query(Question)
    if category: query = query.filter(Question.category == category)
    if domain: query = query.filter(Question.domain == domain)
    if technology: query = query.filter(Question.technology == technology)
    if is_profile is not None: query = query.filter(Question.is_profile_question == is_profile)
    return query.offset(skip).limit(limit).all()

@router.post("/", response_model=QuestionResponse)
async def create_question(q: QuestionCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    question = Question(**q.dict())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question

@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(question_id: int, q: QuestionCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    for key, val in q.dict().items():
        setattr(question, key, val)
    db.commit()
    db.refresh(question)
    return question

@router.delete("/{question_id}")
async def delete_question(question_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(question)
    db.commit()
    return {"message": "Question deleted"}
