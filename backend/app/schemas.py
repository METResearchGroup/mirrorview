from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SubmissionContext(BaseModel):
    id: UUID = Field(..., description="Client-generated UUID correlating feedback calls.")
    created_at: datetime = Field(..., description="ISO-8601 UTC timestamp of submission creation.")
    input_text: str = Field(..., min_length=1, description="Original user text at flip time.")


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

