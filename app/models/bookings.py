from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ServiceTypeEnum(str, enum.Enum):
    CAREER_COUNSELING = "career_counseling"
    STUDENT_GUIDANCE = "student_guidance"
    FREE_COUNSELING = "free_counseling"


class BookingStatusEnum(str, enum.Enum):
    PENDING = "pending"        # just submitted, not yet assigned
    ASSIGNED = "assigned"      # counselor auto/manually assigned
    CONFIRMED = "confirmed"    # counselor confirmed a time with the person
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Counselor(Base):
    """
    A staff member who can be assigned to bookings. `specialties` lists which
    of the ServiceTypeEnum values this counselor handles, so auto-assignment
    only considers counselors qualified for that service.
    """
    __tablename__ = "counselors"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    specialties = Column(JSON, nullable=False, default=list)  # e.g. ["career_counseling", "free_counseling"]
    max_daily_bookings = Column(Integer, default=8)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    career_counseling_bookings = relationship("CareerCounselingBooking", back_populates="counselor")
    student_guidance_bookings = relationship("StudentGuidanceBooking", back_populates="counselor")
    free_counseling_bookings = relationship("FreeCounselingBooking", back_populates="counselor")


class CareerCounselingBooking(Base):
    __tablename__ = "career_counseling_bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable: guests can request too
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    current_situation = Column(String, nullable=True)  # student / fresher / working professional / career-break / homemaker
    goal_description = Column(Text, nullable=True)
    preferred_date = Column(String, nullable=True)
    preferred_time_slot = Column(String, nullable=True)

    counselor_id = Column(Integer, ForeignKey("counselors.id"), nullable=True)
    status = Column(SAEnum(BookingStatusEnum), default=BookingStatusEnum.PENDING)
    admin_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    counselor = relationship("Counselor", back_populates="career_counseling_bookings")


class StudentGuidanceBooking(Base):
    __tablename__ = "student_guidance_bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    education_level = Column(String, nullable=True)  # 10th / 12th / UG / PG / dropout
    stream = Column(String, nullable=True)
    guidance_topic = Column(Text, nullable=True)

    counselor_id = Column(Integer, ForeignKey("counselors.id"), nullable=True)
    status = Column(SAEnum(BookingStatusEnum), default=BookingStatusEnum.PENDING)
    admin_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    counselor = relationship("Counselor", back_populates="student_guidance_bookings")


class FreeCounselingBooking(Base):
    __tablename__ = "free_counseling_bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    result_id = Column(Integer, ForeignKey("results.id"), nullable=True)  # ties session to a completed assessment result, if any
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    preferred_mode = Column(String, nullable=True)  # call / video / chat
    message = Column(Text, nullable=True)

    counselor_id = Column(Integer, ForeignKey("counselors.id"), nullable=True)
    status = Column(SAEnum(BookingStatusEnum), default=BookingStatusEnum.PENDING)
    admin_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    counselor = relationship("Counselor", back_populates="free_counseling_bookings")
