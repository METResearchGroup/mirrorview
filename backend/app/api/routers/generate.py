from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.di.providers import get_generation_service
from app.schemas import FlipResponse, GenerateResponseRequest
from app.services.generation_service import GenerationService
from ml_tooling.llm.exceptions import LLMAuthError, LLMInvalidRequestError, LLMTransientError
from prompts import FLIP_PROMPT


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate_response", response_model=FlipResponse)
async def generate_response(
    req: GenerateResponseRequest,
    svc: GenerationService = Depends(get_generation_service),
) -> FlipResponse:
    submission_id = str(req.submission.id)
    text_len = len(req.text) if isinstance(req.text, str) else None
    logger.info(
        "generate_response request submission_id=%s text_len=%s",
        submission_id,
        text_len,
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": FLIP_PROMPT},
        {"role": "user", "content": req.text},
    ]

    try:
        return await svc.generate(req=req, messages=messages)
    except (LLMAuthError,) as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except (LLMInvalidRequestError,) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (LLMTransientError,) as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unhandled error: {type(e).__name__}: {e}") from e

