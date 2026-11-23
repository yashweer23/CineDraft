import logging
import asyncio
from contextlib import suppress
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pydantic_settings import SettingsError
from starlette.exceptions import HTTPException

from app.catalog import router as catalog_router
from app.talent.api import router as talent_router
from app.collaboration.api import router as collaboration_router
from app.drafting.api import router as drafting_router
from app.drafting.errors import DraftProblem
from app.simulation.api import router as simulation_router
from app.config import Settings
from app.accounts.api import router as accounts_router
from app.challenges.api import router as challenges_router
from app.whatif.api import router as whatif_router
from app.analytics.api import router as analytics_router
from app.database import Database
from app.rooms.api import router as rooms_router
from app.rooms.worker import sweep
from app.schemas import ErrorEnvelope, LiveHealth, ReadyHealth

logger = logging.getLogger("cinedraft")


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    """Factory makes dependency injection explicit for tests and Uvicorn."""
    if settings is None:
        try:
            settings = Settings()
        except ValidationError as error:
            issues = "; ".join(
                f"{'.'.join(map(str, item['loc']))}: {item['msg']}"
                for item in error.errors(include_input=False, include_context=False)
            )
            raise RuntimeError(
                "Invalid CineDraft configuration. Run 'node scripts/setup-env.cjs' "
                f"from the project root and review backend/.env. {issues}"
            ) from None
        except SettingsError:
            raise RuntimeError(
                'Invalid backend/.env encoding. CORS_ORIGINS must be a JSON array of explicit origins. '
                "Review backend/.env.example; no credentials are printed."
            ) from None
    db = database if database is not None else Database(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task = asyncio.create_task(sweep(db.engine)) if hasattr(db, "engine") else None
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            db.close()

    app = FastAPI(
        title="CineDraft API", version="0.15.0",
        description="Phase 15: cooperative live draft rooms with server-owned turns and persistent deadlines, plus solo drafts, challenges and release simulation.",
        docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.database = db
    app.state.room_origins = set(settings.cors_origins)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins,
        allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"],
        expose_headers=["X-Request-ID"],
    )

    def failure(request: Request, status: int, code: str, message: str, headers=None):
        return JSONResponse(
            status_code=status,
            content={"error": {"code": code, "message": message},
                     "request_id": request.state.request_id},
            headers=headers,
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception:
            logger.error("Unhandled request failure, request_id=%s", request.state.request_id)
            response = failure(request, 500, "internal_error", "The API could not complete this request.")
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith(("/api/v1/sessions", "/api/v1/drafts", "/api/v1/accounts", "/api/v1/challenges", "/api/v1/rooms")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(DraftProblem)
    async def draft_error(request: Request, error: DraftProblem):
        detail = {"code": error.code, "message": error.message}
        if error.current_revision is not None:
            detail["current_revision"] = error.current_revision
        return JSONResponse(status_code=error.status,
            content={"error": detail, "request_id": request.state.request_id},
            headers={"WWW-Authenticate": "Bearer"} if error.status == 401 else None)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        return failure(request, error.status_code, f"http_{error.status_code}",
                       str(error.detail), error.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError):
        return failure(request, 422, "validation_error", "Request fields do not match the API contract.")

    @app.get("/api/health", response_model=LiveHealth, tags=["Health"])
    def live() -> LiveHealth:
        """Liveness: API is running; this does not imply the database is ready."""
        return LiveHealth()

    @app.get("/api/health/ready", response_model=ReadyHealth, tags=["Health"],
             responses={503: {"model": ErrorEnvelope, "description": "Database unavailable"}})
    def ready(request: Request):
        if not db.ping():
            return failure(request, 503, "database_unavailable",
                           "PostgreSQL is unavailable. Check that it is running and backend settings match.")
        return ReadyHealth()

    app.include_router(catalog_router)
    app.include_router(talent_router)
    app.include_router(collaboration_router)
    app.include_router(drafting_router)
    app.include_router(simulation_router)
    app.include_router(accounts_router)
    app.include_router(challenges_router)
    app.include_router(whatif_router)
    app.include_router(analytics_router)
    app.include_router(rooms_router)
    return app
