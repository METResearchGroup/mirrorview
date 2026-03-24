from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import jwt
from fastapi import HTTPException, Request

from lib.load_env_vars import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthenticatedUser:
    sub: str
    role: str | None
    email: str | None
    raw_claims: dict[str, Any]


def _expected_issuer(supabase_url: str) -> str:
    return f"{supabase_url.rstrip('/')}/auth/v1"


def _get_bearer_token(request: Request) -> str:
    header = request.headers.get("authorization")
    if not header:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid Authorization header.")
    return token.strip()


def _require_auth_config() -> tuple[str, str, str]:
    supabase_url = (settings().supabase_url or "").strip()
    jwt_secret = (settings().supabase_jwt_secret or "").strip()
    aud = (settings().supabase_jwt_audience or "").strip()
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL must be set when auth is required.")
    if not jwt_secret:
        raise RuntimeError("SUPABASE_JWT_SECRET must be set when auth is required.")
    if not aud:
        raise RuntimeError("SUPABASE_JWT_AUDIENCE must be set when auth is required.")
    return supabase_url, jwt_secret, aud


def _validate_and_decode(token: str) -> dict[str, Any]:
    supabase_url, jwt_secret, aud = _require_auth_config()

    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token.") from exc

    alg = header.get("alg")
    if alg != "HS256":
        raise HTTPException(status_code=401, detail="Unsupported token algorithm.")

    issuer = _expected_issuer(supabase_url)
    try:
        claims = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience=aud,
            issuer=issuer,
            options={
                "require": ["exp", "iat", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token.") from exc

    return claims


def _claims_to_user(claims: dict[str, Any]) -> AuthenticatedUser:
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise HTTPException(status_code=401, detail="Invalid token.")

    raw_role = claims.get("role")
    role = raw_role if isinstance(raw_role, str) else None
    raw_email = claims.get("email")
    email = raw_email if isinstance(raw_email, str) else None
    return AuthenticatedUser(sub=sub, role=role, email=email, raw_claims=claims)


def require_authenticated_user(request: Request) -> AuthenticatedUser:
    if not settings().auth_required:
        # Tests can opt-out of auth enforcement with AUTH_REQUIRED=false.
        return AuthenticatedUser(sub="anonymous", role=None, email=None, raw_claims={})

    token = _get_bearer_token(request)
    claims = _validate_and_decode(token)
    user = _claims_to_user(claims)

    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        # Debug-only; do not log the token.
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        logger.debug("auth_ok sub=%s exp=%s", user.sub, exp_dt.isoformat())
    else:
        logger.debug("auth_ok sub=%s exp=unknown", user.sub)

    return user


def maybe_authenticated_user(request: Request) -> AuthenticatedUser | None:
    """Best-effort authentication for endpoints that allow anonymous access."""
    if not settings().auth_required:
        return None
    try:
        token = _get_bearer_token(request)
    except HTTPException as exc:
        logger.debug(
            "auth_optional_failed stage=bearer_token path=%s user_agent=%s detail=%s",
            request.url.path,
            request.headers.get("user-agent"),
            exc.detail,
        )
        return None
    try:
        claims = _validate_and_decode(token)
        return _claims_to_user(claims)
    except HTTPException as exc:
        logger.debug(
            "auth_optional_failed stage=validate_decode path=%s user_agent=%s detail=%s",
            request.url.path,
            request.headers.get("user-agent"),
            exc.detail,
        )
        return None


def debug_auth_config() -> str:
    """Return redacted auth config for debugging misconfiguration."""
    supabase_url = (settings().supabase_url or "").strip()
    aud = (settings().supabase_jwt_audience or "").strip()
    return json.dumps(
        {
            "supabase_url_set": bool(supabase_url),
            "audience_set": bool(aud),
            "issuer": _expected_issuer(supabase_url) if supabase_url else None,
        },
        sort_keys=True,
    )
