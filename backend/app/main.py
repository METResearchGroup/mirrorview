import logging
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routers import feedback_router, generate_router
from app.db.session import dispose_engine, init_engine, is_persistence_enabled
from app.security import (
    EndpointRateLimiter,
    build_rate_limit_policy,
    error_response,
    extract_client_ip,
    http_exception_handler,
    resolve_rate_limit_scope,
    trust_proxy_headers_enabled,
    unhandled_exception_handler,
    use_csp_report_only,
    validation_exception_handler,
    get_request_body_limit_bytes,
)
from lib.load_env_vars import EnvVarsContainer

logger = logging.getLogger(__name__)


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    run_mode = os.getenv("RUN_MODE", "test")
    if run_mode != "prod" and "http://localhost:3000" not in origins:
        origins.append("http://localhost:3000")
    return origins


@asynccontextmanager
async def lifespan(_: FastAPI):
    if is_persistence_enabled():
        database_url = EnvVarsContainer.get_env_var("DATABASE_URL", required=True)
        init_engine(database_url)
    try:
        yield
    finally:
        await dispose_engine()


app = FastAPI(title="MirrorView Backend", version="0.2.0", lifespan=lifespan)
rate_limiter = EndpointRateLimiter(policy=build_rate_limit_policy())
body_limit_bytes = get_request_body_limit_bytes()
trust_proxy_headers = trust_proxy_headers_enabled()
csp_report_only = use_csp_report_only()

allow_origins = _parse_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


def _apply_response_security_headers(response: Response, *, request_id: str) -> None:
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    csp_value = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    if csp_report_only:
        response.headers["Content-Security-Policy-Report-Only"] = csp_value
    else:
        response.headers["Content-Security-Policy"] = csp_value


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    request_id = uuid4().hex
    request.state.request_id = request_id
    started = time.monotonic()
    path = request.url.path
    client_ip = extract_client_ip(request, trust_proxy_headers=trust_proxy_headers)

    content_length = request.headers.get("content-length")
    if request.method in {"POST", "PUT", "PATCH"} and content_length:
        try:
            if int(content_length) > body_limit_bytes:
                response = error_response(
                    status_code=413,
                    code="payload_too_large",
                    message="Request body too large.",
                    request_id=request_id,
                )
                _apply_response_security_headers(response, request_id=request_id)
                return response
        except ValueError:
            logger.warning("Invalid content-length header request_id=%s value=%s", request_id, content_length)

    scope = resolve_rate_limit_scope(path)
    if scope and request.method != "OPTIONS":
        try:
            allowed, retry_after = rate_limiter.check(scope=scope, client_key=client_ip)
        except Exception:
            logger.exception(
                "rate_limiter_check_failed request_id=%s path=%s client_ip=%s",
                request_id,
                path,
                client_ip,
            )
            response = error_response(
                status_code=503,
                code="rate_limiter_unavailable",
                message="Request could not be evaluated for rate limiting.",
                request_id=request_id,
            )
            _apply_response_security_headers(response, request_id=request_id)
            return response
        if not allowed:
            logger.warning(
                "rate_limited request_id=%s path=%s client_ip=%s retry_after=%s",
                request_id,
                path,
                client_ip,
                retry_after,
            )
            response = error_response(
                status_code=429,
                code="rate_limited",
                message="Too many requests.",
                request_id=request_id,
                headers={"Retry-After": str(retry_after)},
            )
            _apply_response_security_headers(response, request_id=request_id)
            return response

    response = await call_next(request)
    _apply_response_security_headers(response, request_id=request_id)
    duration_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "request_complete request_id=%s method=%s path=%s status_code=%s duration_ms=%s client_ip=%s",
        request_id,
        request.method,
        path,
        response.status_code,
        duration_ms,
        client_ip,
    )
    return response


app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

app.include_router(generate_router)
app.include_router(feedback_router)
