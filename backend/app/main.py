import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import FlipResponse, GenerateResponseRequest
from ml_tooling.llm.exceptions import LLMAuthError, LLMInvalidRequestError, LLMTransientError
from ml_tooling.llm.llm_service import get_llm_service
from prompts import FLIP_PROMPT

logger = logging.getLogger(__name__)


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
