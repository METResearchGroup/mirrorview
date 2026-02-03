import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AckResponse,
    EditFeedbackRequest,
    FlipResponse,
    GenerateResponseRequest,
    ThumbFeedbackRequest,
)
from ml_tooling.llm.exceptions import LLMAuthError, LLMInvalidRequestError, LLMTransientError
from prompts import FLIP_PROMPT

logger = logging.getLogger(__name__)


def get_llm_service():
    # Lazy import so unit tests (and feedback-only usage) don't require LLM deps.
    from ml_tooling.llm.llm_service import get_llm_service as _get_llm_service

    return _get_llm_service()


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    # Always allow local Next.js dev.
    if "http://localhost:3000" not in origins:
        origins.append("http://localhost:3000")
    return origins


app = FastAPI(title="MirrorView Backend", version="0.1.0")

allow_origins = _parse_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins if allow_origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate_response", response_model=FlipResponse)
def generate_response(req: GenerateResponseRequest) -> FlipResponse:
    # Validate + structured-log payload (correlation key for future DB storage).
    try:
        payload = req.model_dump(mode="json")  # Pydantic v2
        submission_id = payload["submission"]["id"] if req.submission is not None else None
    except Exception:
        logger.exception("Failed to serialize /generate_response request for logging")
        raise

    text_len = len(req.text) if isinstance(req.text, str) else None
    logger.info(
        "generate_response request submission_id=%s text_len=%s has_submission=%s",
        submission_id,
        text_len,
        req.submission is not None,
    )

    # LiteLLM expects messages as list[dict] with role/content.
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": FLIP_PROMPT},
        {"role": "user", "content": req.text},
    ]

    llm = get_llm_service()
    try:
        return llm.structured_completion(
            messages=messages,
            response_model=FlipResponse,
            model=None,  # Use default from models.yaml (gpt-4o-mini)
        )
    except (LLMAuthError,) as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except (LLMInvalidRequestError,) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (LLMTransientError,) as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        # Catch-all: keep response bounded but still report something actionable.
        raise HTTPException(status_code=500, detail=f"Unhandled error: {type(e).__name__}: {e}") from e


@app.post("/feedback/thumb", response_model=AckResponse)
def submit_thumb_feedback(req: ThumbFeedbackRequest) -> AckResponse:
    # Validate + structured-log payload (correlation key for future DB storage).
    try:
        payload = req.model_dump(mode="json")  # Pydantic v2
        submission_id = payload["submission"]["id"]
    except Exception:
        logger.exception("Failed to serialize /feedback/thumb request for logging")
        raise

    logger.info(
        "thumb_feedback submission_id=%s vote=%s voted_at=%s",
        submission_id,
        req.vote,
        req.voted_at.isoformat(),
    )
    return AckResponse(ok=True)


@app.post("/feedback/edit", response_model=AckResponse)
def submit_edit_feedback(req: EditFeedbackRequest) -> AckResponse:
    # Validate + structured-log payload (correlation key for future DB storage).
    try:
        payload = req.model_dump(mode="json")  # Pydantic v2
        submission_id = payload["submission"]["id"]
    except Exception:
        logger.exception("Failed to serialize /feedback/edit request for logging")
        raise

    logger.info(
        "edit_feedback submission_id=%s edited_at=%s edited_text_len=%s",
        submission_id,
        req.edited_at.isoformat(),
        len(req.edited_text),
    )
    return AckResponse(ok=True)
