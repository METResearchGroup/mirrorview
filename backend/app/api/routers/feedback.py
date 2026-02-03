from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.di.providers import get_feedback_service
from app.schemas import AckResponse, EditFeedbackRequest, ThumbFeedbackRequest
from app.services.feedback_service import FeedbackService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback")


@router.post("/thumb", response_model=AckResponse)
async def submit_thumb_feedback(
    req: ThumbFeedbackRequest,
    svc: FeedbackService = Depends(get_feedback_service),
) -> AckResponse:
    try:
        logger.info(
            "thumb_feedback submission_id=%s vote=%s voted_at=%s",
            req.submission.id,
            req.vote,
            req.voted_at.isoformat(),
        )
        await svc.submit_thumb(req=req)
        return AckResponse(ok=True)
    except Exception:
        logger.exception("Failed to record thumb feedback")
        raise HTTPException(
            status_code=500,
            detail="Failed to record your feedback. Please try again.",
        )


@router.post("/edit", response_model=AckResponse)
async def submit_edit_feedback(
    req: EditFeedbackRequest,
    svc: FeedbackService = Depends(get_feedback_service),
) -> AckResponse:
    try:
        logger.info(
            "edit_feedback submission_id=%s edited_at=%s edited_text_len=%s",
            req.submission.id,
            req.edited_at.isoformat(),
            len(req.edited_text),
        )
        await svc.submit_edit(req=req)
        return AckResponse(ok=True)
    except Exception:
        logger.exception("Failed to record edit feedback")
        raise HTTPException(
            status_code=500,
            detail="Failed to record your feedback. Please try again.",
        )

