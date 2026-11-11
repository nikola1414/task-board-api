import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import cache
from app.db import engine
from app.routers import auth, projects, tasks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("app")

app = FastAPI(
    title="Task Board API",
    version="1.0.0",
    description="Projects, tasks, comments and an activity log, with role-based access.",
)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)

_VALID_REQUEST_ID = re.compile(r"^[\w-]{1,64}$")


def error_response(
    request: Request, status_code: int, message: Any, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    """Every error has the same shape: {"error": {"status", "message"}, "request_id"}."""
    return JSONResponse(
        {
            "error": {"status": status_code, "message": message},
            "request_id": getattr(request.state, "request_id", None),
        },
        status_code=status_code,
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return error_response(request, exc.status_code, exc.detail, exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()
    ]
    return error_response(request, 422, details)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    incoming = request.headers.get("X-Request-ID", "")
    request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled error request_id=%s", request_id)
        response = error_response(request, 500, "Internal server error")
    response.headers["X-Request-ID"] = request_id
    log.info(
        "%s %s -> %d %.1fms request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
        request_id,
    )
    return response


@app.get("/health", tags=["health"])
def health() -> JSONResponse:
    """Liveness + dependency check: 200 if Postgres and Redis both answer, else 503."""
    checks: dict[str, str] = {}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "unavailable"
    try:
        cache.client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if healthy else "degraded", **checks}, status_code=200 if healthy else 503
    )
