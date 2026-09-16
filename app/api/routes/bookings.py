from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_optional, get_current_admin
from app.models.user import User
from app.models.bookings import (
    Counselor, CareerCounselingBooking, StudentGuidanceBooking, FreeCounselingBooking,
    ServiceTypeEnum, BookingStatusEnum,
)
from app.schemas.schemas import (
    CareerCounselingBookingCreate, StudentGuidanceBookingCreate, FreeCounselingBookingCreate,
    BookingResponse, BookingStatusUpdate, CounselorCreate, CounselorResponse,
)

router = APIRouter()

# Maps each booking model to the service type used for counselor matching,
# so one assignment helper works for all three tables.
_ACTIVE_STATUSES = (BookingStatusEnum.PENDING, BookingStatusEnum.ASSIGNED, BookingStatusEnum.CONFIRMED)


def _auto_assign_counselor(db: Session, service_type: ServiceTypeEnum, booking_model) -> Optional[Counselor]:
    """
    Pick the active counselor qualified for `service_type` with the fewest
    currently-active bookings (across ALL their booking types, not just this
    one), so load balances across a counselor's whole day rather than per-form.
    Returns None if no qualified counselor is available (booking stays PENDING
    for manual admin assignment).
    """
    candidates = db.query(Counselor).filter(Counselor.is_active == True).all()
    qualified = [c for c in candidates if service_type.value in (c.specialties or [])]
    if not qualified:
        return None

    def active_load(counselor: Counselor) -> int:
        return (
            db.query(CareerCounselingBooking).filter(
                CareerCounselingBooking.counselor_id == counselor.id,
                CareerCounselingBooking.status.in_(_ACTIVE_STATUSES),
            ).count()
            + db.query(StudentGuidanceBooking).filter(
                StudentGuidanceBooking.counselor_id == counselor.id,
                StudentGuidanceBooking.status.in_(_ACTIVE_STATUSES),
            ).count()
            + db.query(FreeCounselingBooking).filter(
                FreeCounselingBooking.counselor_id == counselor.id,
                FreeCounselingBooking.status.in_(_ACTIVE_STATUSES),
            ).count()
        )

    qualified.sort(key=active_load)
    best = qualified[0]
    if active_load(best) >= best.max_daily_bookings:
        return None  # everyone qualified is already at capacity — leave for manual assignment
    return best


# ── Career Counseling ────────────────────────────────────────────────────────
@router.post("/career-counseling", response_model=BookingResponse)
async def request_career_counseling(
    data: CareerCounselingBookingCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    booking = CareerCounselingBooking(user_id=current_user.id if current_user else None, **data.dict())
    db.add(booking)
    db.flush()  # assign an id before we look at load-balancing across bookings
    counselor = _auto_assign_counselor(db, ServiceTypeEnum.CAREER_COUNSELING, CareerCounselingBooking)
    if counselor:
        booking.counselor_id = counselor.id
        booking.status = BookingStatusEnum.ASSIGNED
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/career-counseling/my", response_model=List[BookingResponse])
async def my_career_counseling_bookings(
    current_user: User = Depends(get_current_user_optional), db: Session = Depends(get_db)
):
    if not current_user:
        return []
    return db.query(CareerCounselingBooking).filter(CareerCounselingBooking.user_id == current_user.id).all()


# ── Student Guidance ─────────────────────────────────────────────────────────
@router.post("/student-guidance", response_model=BookingResponse)
async def request_student_guidance(
    data: StudentGuidanceBookingCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    booking = StudentGuidanceBooking(user_id=current_user.id if current_user else None, **data.dict())
    db.add(booking)
    db.flush()
    counselor = _auto_assign_counselor(db, ServiceTypeEnum.STUDENT_GUIDANCE, StudentGuidanceBooking)
    if counselor:
        booking.counselor_id = counselor.id
        booking.status = BookingStatusEnum.ASSIGNED
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/student-guidance/my", response_model=List[BookingResponse])
async def my_student_guidance_bookings(
    current_user: User = Depends(get_current_user_optional), db: Session = Depends(get_db)
):
    if not current_user:
        return []
    return db.query(StudentGuidanceBooking).filter(StudentGuidanceBooking.user_id == current_user.id).all()


# ── Free Expert Counseling ───────────────────────────────────────────────────
@router.post("/free-counseling", response_model=BookingResponse)
async def request_free_counseling(
    data: FreeCounselingBookingCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    booking = FreeCounselingBooking(user_id=current_user.id if current_user else None, **data.dict())
    db.add(booking)
    db.flush()
    counselor = _auto_assign_counselor(db, ServiceTypeEnum.FREE_COUNSELING, FreeCounselingBooking)
    if counselor:
        booking.counselor_id = counselor.id
        booking.status = BookingStatusEnum.ASSIGNED
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/free-counseling/my", response_model=List[BookingResponse])
async def my_free_counseling_bookings(
    current_user: User = Depends(get_current_user_optional), db: Session = Depends(get_db)
):
    if not current_user:
        return []
    return db.query(FreeCounselingBooking).filter(FreeCounselingBooking.user_id == current_user.id).all()


# ── Admin: Counselors ─────────────────────────────────────────────────────────
@router.get("/admin/counselors", response_model=List[CounselorResponse])
async def list_counselors(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Counselor).all()


@router.post("/admin/counselors", response_model=CounselorResponse)
async def create_counselor(
    data: CounselorCreate, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    counselor = Counselor(
        full_name=data.full_name, email=data.email, phone=data.phone, bio=data.bio,
        specialties=[s.value for s in data.specialties], max_daily_bookings=data.max_daily_bookings,
    )
    db.add(counselor)
    db.commit()
    db.refresh(counselor)
    return counselor


@router.patch("/admin/counselors/{counselor_id}/toggle", response_model=CounselorResponse)
async def toggle_counselor_active(
    counselor_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    counselor = db.query(Counselor).filter(Counselor.id == counselor_id).first()
    if not counselor:
        raise HTTPException(status_code=404, detail="Counselor not found")
    counselor.is_active = not counselor.is_active
    db.commit()
    db.refresh(counselor)
    return counselor


# ── Admin: Booking management (list + status/assignment updates) ────────────
_BOOKING_MODELS = {
    "career-counseling": CareerCounselingBooking,
    "student-guidance": StudentGuidanceBooking,
    "free-counseling": FreeCounselingBooking,
}


@router.get("/admin/{service}", response_model=List[BookingResponse])
async def admin_list_bookings(
    service: str, status_filter: Optional[BookingStatusEnum] = None,
    current_user: User = Depends(get_current_admin), db: Session = Depends(get_db),
):
    model = _BOOKING_MODELS.get(service)
    if not model:
        raise HTTPException(status_code=404, detail="Unknown service type")
    query = db.query(model)
    if status_filter:
        query = query.filter(model.status == status_filter)
    return query.order_by(model.created_at.desc()).all()


@router.patch("/admin/{service}/{booking_id}", response_model=BookingResponse)
async def admin_update_booking(
    service: str, booking_id: int, data: BookingStatusUpdate,
    current_user: User = Depends(get_current_admin), db: Session = Depends(get_db),
):
    model = _BOOKING_MODELS.get(service)
    if not model:
        raise HTTPException(status_code=404, detail="Unknown service type")
    booking = db.query(model).filter(model.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = data.status
    if data.admin_notes is not None:
        booking.admin_notes = data.admin_notes
    if data.counselor_id is not None:
        booking.counselor_id = data.counselor_id
    db.commit()
    db.refresh(booking)
    return booking
