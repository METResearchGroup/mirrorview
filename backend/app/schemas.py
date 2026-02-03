from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SubmissionContext(BaseModel):
    id: UUID = Field(..., description="Client-generated UUID correlating feedback calls.")
    created_at: datetime = Field(..., description="ISO-8601 UTC timestamp of submission creation.")
    input_text: str = Field(..., min_length=1, description="Original user text at flip time.")


class AckResponse(BaseModel):
    ok: bool = Field(True, description="Simple acknowledgement response.")


class ThumbFeedbackRequest(BaseModel):
    submission: SubmissionContext = Field(..., description="Submission metadata generated client-side.")
    vote: str = Field(..., pattern="^(up|down)$", description="Thumbs up ('up') or thumbs down ('down').")
    voted_at: datetime = Field(..., description="ISO-8601 UTC timestamp of when feedback was given.")


class EditFeedbackRequest(BaseModel):
    submission: SubmissionContext = Field(..., description="Submission metadata generated client-side.")
    edited_text: str = Field(..., min_length=1, description="User's preferred version of the flipped text.")
    edited_at: datetime = Field(..., description="ISO-8601 UTC timestamp of when edit was submitted.")


class GenerateResponseRequest(BaseModel):
    text: str = Field(..., min_length=1, description="A social media post to flip.")
    submission: SubmissionContext | None = Field(
        default=None,
        description="Optional submission metadata generated client-side at flip time.",
    )


class FlipResponse(BaseModel):
    flipped_text: str = Field(..., description="The rewritten post with opposite political stance.")
    explanation: str = Field(
        ...,
        description="Specific features considered when flipping (tone, framing, issues, rhetoric, etc.).",
    )

