from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.di.providers import get_generation_service
from app.schemas import FlipResponse, GenerateResponseRequest, ModelCatalogResponse, ModelOption
from app.services.generation_service import GenerationService
from ml_tooling.llm.config.model_registry import ModelConfigRegistry
from ml_tooling.llm.exceptions import LLMAuthError, LLMInvalidRequestError, LLMTransientError
from prompts import FLIP_PROMPT


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/models", response_model=ModelCatalogResponse)
def list_models() -> ModelCatalogResponse:
    return ModelCatalogResponse(
        default_model_id=ModelConfigRegistry.get_default_model(),
        models=[
            ModelOption(
                model_id=model["model_id"],
                display_name=model["display_name"],
                provider=model["provider"],
            )
            for model in ModelConfigRegistry.list_available_models()
        ],
    )


@router.post("/generate_response", response_model=FlipResponse)
async def generate_response(
    req: GenerateResponseRequest,
    svc: GenerationService = Depends(get_generation_service),
) -> FlipResponse:
    submission_id = str(req.submission.id)
    model_id = req.submission.model_id
    text_len = len(req.text) if isinstance(req.text, str) else None
    logger.info(
        "generate_response request submission_id=%s model_id=%s text_len=%s",
        submission_id,
        model_id,
        text_len,
    )

    if not ModelConfigRegistry.model_exists(model_id):
        raise HTTPException(status_code=400, detail=f"Unknown model_id: {model_id}")
    if not ModelConfigRegistry.is_model_available(model_id):
        raise HTTPException(status_code=400, detail=f"Model is not available: {model_id}")

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
        logger.exception("Unhandled generate_response failure submission_id=%s", submission_id)
        raise HTTPException(status_code=500, detail="Internal server error.") from e

