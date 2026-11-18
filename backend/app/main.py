"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import check_database_connection
from app.routers import admin, ai, auth, content, documents, healthcare_workers, patients, records, users
from app.services.storage_service import get_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_storage()  # ensure private storage directory exists
    if check_database_connection():
        logger.info("Database connection OK")
    else:
        logger.warning("Database is not reachable — check DATABASE_URL")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Milestone 1 — Patient & Healthcare Information Management System for the AI-Driven "
        "Healthcare Assistance Platform. Use **Authorize** with the access_token from `/auth/login`."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition", "Retry-After"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    # Return field-level messages without echoing submitted values (may contain sensitive data).
    errors = [
        {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"].removeprefix("Value error, ")}
        for err in exc.errors()
    ]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": "Validation failed", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


@app.get("/health", tags=["Health"])
def health():
    db_ok = check_database_connection()
    return {"status": "ok" if db_ok else "degraded", "database": "connected" if db_ok else "unavailable"}


for r in (auth.router, users.router, patients.router, healthcare_workers.router,
          documents.router, records.router, content.router, admin.router, ai.router):
    app.include_router(r, prefix=settings.API_V1_PREFIX)
