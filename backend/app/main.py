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
    except AttributeError:
        payload = req.dict()  # Pydantic v1
    submission_id = None
    try:
        submission = payload.get("submission") if isinstance(payload, dict) else None
        submission_id = submission.get("id") if isinstance(submission, dict) else None
    except Exception:
        submission_id = None

    logger.info("generate_response request submission_id=%s payload=%s", submission_id, payload)

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
