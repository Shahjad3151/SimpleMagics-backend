from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.models.user import CategoryEnum, DomainEnum, TechnologyEnum, QuestionTypeEnum, DifficultyEnum, EligibilityStatusEnum

# Auth Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one number")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False
    user_id: int
    profile_completed: bool = False

class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

# Student Profile Schemas
class StudentProfileCreate(BaseModel):
    full_name: str
    mobile_number: str
    education: str
    graduation_year: int
    college_name: str
    current_status: str
    preferred_domain: Optional[str] = None
    preferred_technology: Optional[str] = None

class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    mobile_number: Optional[str]
    education: Optional[str]
    graduation_year: Optional[int]
    college_name: Optional[str]
    current_status: Optional[str]
    preferred_domain: Optional[str]
    preferred_technology: Optional[str]
    category_fit: Optional[CategoryEnum]
    assigned_domain: Optional[DomainEnum]
    assigned_technology: Optional[TechnologyEnum]
    profile_completed: bool
    class Config:
        from_attributes = True

# Question Schemas
class QuestionCreate(BaseModel):
    question_text: str
    question_type: QuestionTypeEnum
    category: Optional[CategoryEnum] = None
    domain: Optional[DomainEnum] = None
    technology: Optional[TechnologyEnum] = None
    difficulty: DifficultyEnum = DifficultyEnum.MEDIUM
    options: Optional[List[str]] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    marks: int = 1
    is_profile_question: bool = False
    is_interest_signal: bool = False
    option_tags: Optional[List[str]] = None
    coding_template: Optional[str] = None
    test_cases: Optional[List[Dict]] = None

class QuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: QuestionTypeEnum
    category: Optional[CategoryEnum]
    domain: Optional[DomainEnum]
    technology: Optional[TechnologyEnum]
    difficulty: DifficultyEnum
    options: Optional[List[str]]
    marks: int
    is_profile_question: bool
    is_interest_signal: bool = False
    coding_template: Optional[str]
    test_cases: Optional[List[Dict]]
    class Config:
        from_attributes = True

# Test Session Schemas
class StartTestRequest(BaseModel):
    session_type: str  # profile_fit, technical, non_it, management
    domain: Optional[str] = None
    technology: Optional[str] = None

class SubmitAnswerRequest(BaseModel):
    question_id: int
    user_answer: Any
    time_spent_seconds: Optional[int] = None

class SubmitTestRequest(BaseModel):
    test_session_id: int
    answers: List[SubmitAnswerRequest]
    time_taken_seconds: Optional[int] = None

class TestSessionResponse(BaseModel):
    id: int
    session_type: str
    status: str
    started_at: Optional[datetime]
    questions: List[QuestionResponse] = []
    class Config:
        from_attributes = True

# Result Schemas
class ResultResponse(BaseModel):
    id: int
    test_session_id: int
    user_id: int
    total_score: float
    max_score: float
    percentage: float
    category_fit: Optional[CategoryEnum]
    domain_fit: Optional[DomainEnum]
    technology_fit: Optional[TechnologyEnum]
    eligibility_status: Optional[EligibilityStatusEnum]
    section_scores: Optional[Dict]
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    recommendations: Optional[List[str]]
    learning_path: Optional[List[str]]
    category_signal_breakdown: Optional[Dict] = None
    created_at: datetime
    class Config:
        from_attributes = True

# Admin Schemas
class AdminStats(BaseModel):
    total_students: int
    total_tests_completed: int
    total_tests_pending: int
    category_distribution: Dict[str, int]
    eligibility_distribution: Dict[str, int]
    avg_score: float

# ── Booking Schemas (Career Counseling / Student Guidance / Free Counseling) ─
from app.models.bookings import ServiceTypeEnum, BookingStatusEnum

class CounselorResponse(BaseModel):
    id: int
    full_name: str
    email: str
    bio: Optional[str]
    specialties: List[str]
    is_active: bool
    class Config:
        from_attributes = True

class CounselorCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    bio: Optional[str] = None
    specialties: List[ServiceTypeEnum]
    max_daily_bookings: int = 8

class CareerCounselingBookingCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    current_situation: Optional[str] = None
    goal_description: Optional[str] = None
    preferred_date: Optional[str] = None
    preferred_time_slot: Optional[str] = None

class StudentGuidanceBookingCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    education_level: Optional[str] = None
    stream: Optional[str] = None
    guidance_topic: Optional[str] = None

class FreeCounselingBookingCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    result_id: Optional[int] = None
    preferred_mode: Optional[str] = None
    message: Optional[str] = None

class BookingResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str]
    counselor_id: Optional[int]
    counselor: Optional[CounselorResponse] = None
    status: BookingStatusEnum
    admin_notes: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class BookingStatusUpdate(BaseModel):
    status: BookingStatusEnum
    admin_notes: Optional[str] = None
    counselor_id: Optional[int] = None
