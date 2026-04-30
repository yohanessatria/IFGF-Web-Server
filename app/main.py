from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.models import user, church  # noqa: ensure models are registered
from app.routers import auth, members, attendance, icare, ministries, dashboard, activity_types, activity_sessions, users, roles

# Create all tables (run once; use Alembic for production migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="IFGF Taipei Zhongli – Church Management API",
    version="1.0.0",
    description="Backend API for managing church members, attendance, iCare groups, and ministries.",
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(members.router)
app.include_router(attendance.router)
app.include_router(icare.router)
app.include_router(ministries.router)
app.include_router(dashboard.router)
app.include_router(activity_types.router)
app.include_router(activity_sessions.router)
app.include_router(users.router)
app.include_router(roles.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "IFGF Taipei Zhongli API"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
