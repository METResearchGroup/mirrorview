from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

_LIMIT_UNIT_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
}


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int


class InMemoryRateLimitStore:
    """Process-local fixed-window counters.

    This implementation is intentionally simple for single-instance deployment.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[tuple[str, str, int, int], int] = {}

    def hit(self, *, key: str, scope: str, rule: RateLimitRule, now: float) -> tuple[bool, int]:
        window_start = int(now // rule.window_seconds) * rule.window_seconds
        bucket = (key, scope, rule.window_seconds, window_start)
        with self._lock:
            count = self._counts.get(bucket, 0)
            if count >= rule.limit:
                retry_after = (window_start + rule.window_seconds) - int(now)
                return False, max(retry_after, 1)
            self._counts[bucket] = count + 1
            self._cleanup_if_needed(now=now)
        return True, 0

    def _cleanup_if_needed(self, *, now: float) -> None:
        if len(self._counts) < 10_000:
            return
        now_i = int(now)
        stale = [
            bucket
            for bucket in self._counts
            if bucket[3] + bucket[2] <= now_i
        ]
        for bucket in stale:
            self._counts.pop(bucket, None)


class EndpointRateLimiter:
    def __init__(self, policy: dict[str, tuple[RateLimitRule, ...]]) -> None:
        self._policy = policy
        self._store = InMemoryRateLimitStore()

    def check(self, *, scope: str, client_key: str) -> tuple[bool, int]:
        rules = self._policy.get(scope)
        if not rules:
            return True, 0

        now = time.time()
        retry_after_values: list[int] = []
        for rule in rules:
            allowed, retry_after = self._store.hit(key=client_key, scope=scope, rule=rule, now=now)
            if not allowed:
                retry_after_values.append(retry_after)
        if retry_after_values:
            return False, max(retry_after_values)
        return True, 0


def build_rate_limit_policy() -> dict[str, tuple[RateLimitRule, ...]]:
    return {
        "generate_response": _parse_rules(
            os.getenv("RATE_LIMIT_GENERATE", "5/minute,30/hour")
        ),
        "feedback_thumb": _parse_rules(
            os.getenv("RATE_LIMIT_FEEDBACK_THUMB", "30/minute,300/hour")
        ),
        "feedback_edit": _parse_rules(
            os.getenv("RATE_LIMIT_FEEDBACK_EDIT", "15/minute,120/hour")
        ),
    }


def get_request_body_limit_bytes() -> int:
    raw = os.getenv("MAX_REQUEST_BODY_BYTES", "65536")
    try:
        parsed = int(raw)
    except ValueError:
        logger.warning("Invalid MAX_REQUEST_BODY_BYTES=%s; defaulting to 65536", raw)
        return 65536
    return max(parsed, 1024)


def trust_proxy_headers_enabled() -> bool:
    return _env_bool("TRUST_PROXY_HEADERS", default=False)


def use_csp_report_only() -> bool:
    return _env_bool("CSP_REPORT_ONLY", default=True)


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_rules(raw_rules: str) -> tuple[RateLimitRule, ...]:
    rules: list[RateLimitRule] = []
    for token in [t.strip() for t in raw_rules.split(",") if t.strip()]:
        try:
            limit_part, unit_part = token.split("/", 1)
            limit = int(limit_part.strip())
            unit = unit_part.strip().lower().rstrip("s")
            window_seconds = _LIMIT_UNIT_SECONDS[unit]
        except (ValueError, KeyError) as exc:
            raise ValueError(
                f"Invalid rate limit token '{token}'. Expected format like '10/minute'."
            ) from exc
        if limit <= 0:
            raise ValueError(f"Rate limit must be > 0 for token '{token}'")
        rules.append(RateLimitRule(limit=limit, window_seconds=window_seconds))
    if not rules:
        raise ValueError("At least one rate limit rule is required.")
    return tuple(rules)


def resolve_rate_limit_scope(path: str) -> str | None:
    if path == "/generate_response":
        return "generate_response"
    if path == "/feedback/thumb":
        return "feedback_thumb"
    if path == "/feedback/edit":
        return "feedback_edit"
    return None


def extract_client_ip(request: Request, *, trust_proxy_headers: bool) -> str:
    if trust_proxy_headers:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # We trust the edge proxy to sanitize this header.
            parts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
            if parts:
                return parts[0]
        real_ip = request.headers.get("x-real-ip")
        if real_ip and real_ip.strip():
            return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def error_payload(
    *,
    code: str,
    message: str,
    request_id: str | None,
    details: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if request_id:
        payload["error"]["request_id"] = request_id
    if details is not None:
        payload["error"]["details"] = details
    return payload


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return uuid4().hex


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str | None,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code=code, message=message, request_id=request_id, details=details),
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = get_request_id(request)
    status_code = exc.status_code
    if status_code >= 500:
        return error_response(
            status_code=status_code,
            code="internal_error",
            message="Internal server error.",
            request_id=request_id,
        )

    detail = exc.detail if isinstance(exc.detail, str) and exc.detail.strip() else "Request failed."
    return error_response(
        status_code=status_code,
        code="request_error",
        message=detail,
        request_id=request_id,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        status_code=422,
        code="validation_error",
        message="Invalid request payload.",
        request_id=get_request_id(request),
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception request_id=%s path=%s", get_request_id(request), request.url.path)
    return error_response(
        status_code=500,
        code="internal_error",
        message="Internal server error.",
        request_id=get_request_id(request),
    )
