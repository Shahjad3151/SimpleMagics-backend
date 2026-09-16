from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class CategoryEnum(str, enum.Enum):
    IT = "IT"
    NON_IT = "Non-IT"
    MANAGEMENT = "Management"
    FINANCE = "Finance"
    HR = "HR"
    CREATIVE = "Creative"
    ENGINEERING = "Engineering"
    HEALTHCARE = "Healthcare"
    LAW = "Law"
    GOVERNMENT = "Government"
    EDUCATION = "Education"

class DomainEnum(str, enum.Enum):
    FRONTEND = "Frontend Developer"
    BACKEND = "Backend Developer"
    FULLSTACK = "Full Stack Developer"
    DATA_SCIENCE = "Data Science"
    AI_ML = "AI/ML Engineer"
    DEVOPS = "DevOps/Cloud"
    CYBERSECURITY = "Cybersecurity"
    MOBILE = "Mobile Developer"
    BUSINESS_ANALYST = "Business Analyst"
    PRODUCT_MANAGER = "Product Manager"
    HR_GENERALIST = "HR Generalist"
    TALENT_ACQUISITION = "Talent Acquisition"
    DIGITAL_MARKETING = "Digital Marketing"
    CONTENT_CREATOR = "Content Creator"
    UI_UX = "UI/UX Designer"
    CA_FINANCE = "CA/Finance"
    ENTREPRENEUR = "Entrepreneur"
    MANUFACTURING = "Manufacturing Engineer"
    SALES = "Sales & BD"
    SOCIAL_MEDIA = "Social Media"

class TechnologyEnum(str, enum.Enum):
    C = "C"
    CPP = "C++"
    DOTNET = ".NET"
    JAVA = "Java"
    PYTHON = "Python"
    REACT = "React"
    NODEJS = "Node.js"
    ANGULAR = "Angular"
    VUE = "Vue.js"
    GO = "Go"
    RUST = "Rust"
    KOTLIN = "Kotlin"
    SWIFT = "Swift"
    SQL = "SQL"
    GENERAL = "General"

class QuestionTypeEnum(str, enum.Enum):
    MCQ = "MCQ"
    MULTI_SELECT = "multi_select"
    CODING = "coding"
    DESCRIPTIVE = "descriptive"
    APTITUDE = "aptitude"
    SCENARIO = "scenario"

class DifficultyEnum(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"

class EligibilityStatusEnum(str, enum.Enum):
    EXCEPTIONAL = "exceptional"
    ELIGIBLE = "eligible"
    MODERATELY_ELIGIBLE = "moderately_eligible"
    NEEDS_IMPROVEMENT = "needs_improvement"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    profile = relationship("StudentProfile", back_populates="user", uselist=False)
    test_sessions = relationship("TestSession", back_populates="user")

class StudentProfile(Base):
    __tablename__ = "student_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    full_name = Column(String, nullable=False)
    mobile_number = Column(String)
    education = Column(String)
    graduation_year = Column(Integer)
    college_name = Column(String)
    current_status = Column(String)
    age = Column(Integer, nullable=True)
    preferred_domain = Column(String)
    preferred_technology = Column(String)
    personality_type = Column(String, nullable=True)
    interest_area = Column(String, nullable=True)
    biggest_challenge = Column(String, nullable=True)
    strength_keyword = Column(String, nullable=True)
    category_fit = Column(SAEnum(CategoryEnum), nullable=True)
    assigned_domain = Column(SAEnum(DomainEnum), nullable=True)
    assigned_technology = Column(SAEnum(TechnologyEnum), nullable=True)
    profile_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="profile")

class Question(Base):
    __tablename__ = "question_bank"
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(SAEnum(QuestionTypeEnum), nullable=False)
    category = Column(SAEnum(CategoryEnum), nullable=True)
    domain = Column(SAEnum(DomainEnum), nullable=True)
    technology = Column(SAEnum(TechnologyEnum), nullable=True)
    difficulty = Column(SAEnum(DifficultyEnum), default=DifficultyEnum.MEDIUM)
    options = Column(JSON, nullable=True)
    correct_answer = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)
    marks = Column(Integer, default=1)
    is_profile_question = Column(Boolean, default=False)
    # Interest/style questions have no "right" answer — they exist purely to route
    # a person toward a career category based on which option they pick. They are
    # excluded from scoring entirely (see tests.py). option_tags holds one
    # CategoryEnum value per option, in the same order as `options`.
    is_interest_signal = Column(Boolean, default=False)
    option_tags = Column(JSON, nullable=True)
    section_tag = Column(String, nullable=True)
    coding_template = Column(Text, nullable=True)
    test_cases = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(SAEnum(CategoryEnum), nullable=True)
    domain = Column(SAEnum(DomainEnum), nullable=True)
    technology = Column(SAEnum(TechnologyEnum), nullable=True)
    total_questions = Column(Integer, default=30)
    duration_minutes = Column(Integer, default=45)
    passing_score = Column(Float, default=60.0)
    is_active = Column(Boolean, default=True)
    is_profile_assessment = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TestSession(Base):
    __tablename__ = "test_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=True)
    session_type = Column(String)
    status = Column(String, default="pending")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
    questions_data = Column(JSON, nullable=True)
    user = relationship("User", back_populates="test_sessions")
    submissions = relationship("Submission", back_populates="test_session")
    result = relationship("Result", back_populates="test_session", uselist=False)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id"))
    question_id = Column(Integer, ForeignKey("question_bank.id"))
    user_answer = Column(JSON, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    marks_obtained = Column(Float, default=0)
    time_spent_seconds = Column(Integer, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    test_session = relationship("TestSession", back_populates="submissions")
    question = relationship("Question")

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id"), unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_score = Column(Float, default=0)
    max_score = Column(Float, default=0)
    percentage = Column(Float, default=0)
    category_fit = Column(SAEnum(CategoryEnum), nullable=True)
    domain_fit = Column(SAEnum(DomainEnum), nullable=True)
    technology_fit = Column(SAEnum(TechnologyEnum), nullable=True)
    eligibility_status = Column(SAEnum(EligibilityStatusEnum), nullable=True)
    section_scores = Column(JSON, nullable=True)
    strengths = Column(JSON, nullable=True)
    weaknesses = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    learning_path = Column(JSON, nullable=True)
    career_paths = Column(JSON, nullable=True)
    cognitive_profile = Column(JSON, nullable=True)
    # Transparency: for profile_fit results, how many interest-signal answers
    # pointed toward each category — shown on the results page so the
    # recommendation doesn't feel like a black box.
    category_signal_breakdown = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    test_session = relationship("TestSession", back_populates="result")
