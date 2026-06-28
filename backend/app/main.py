import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

from app.api.routes import audit, auth, candidates, feedback, search
from app.config import settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

app = FastAPI(
    title="AI Recruiter Ranking Engine",
    description="Multi-signal ML-ranked candidate shortlisting system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 2),
    )
    response.headers["X-Response-Time-Ms"] = str(round(duration_ms, 2))
    return response

app.include_router(search.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(candidates.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
