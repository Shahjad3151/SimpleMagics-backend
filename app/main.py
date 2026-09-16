from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.limiter import limiter
from app.api.routes import auth, students, assessments, questions, tests, results, admin, bookings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SimpleMagics API",
    description="Career Counseling, Assessments, and Guidance Platform",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(students.router, prefix="/api/students", tags=["Students"])
app.include_router(assessments.router, prefix="/api/assessments", tags=["Assessments"])
app.include_router(questions.router, prefix="/api/questions", tags=["Questions"])
app.include_router(tests.router, prefix="/api/tests", tags=["Tests"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "SimpleMagics API", "version": "2.0.0"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred. Please try again."})
