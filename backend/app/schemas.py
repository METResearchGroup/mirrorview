from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SubmissionContext(BaseModel):
    id: UUID = Field(..., description="Client-generated UUID correlating feedback calls.")
    created_at: datetime = Field(..., description="ISO-8601 UTC timestamp of submission creation.")
    input_text: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Original user text at flip time.",
    )
    model_id: str = Field(
        default="gpt-5-nano",
        min_length=1,
        max_length=128,
        description="Public model identifier selected at generation time.",
    )


class AckResponse(BaseModel):
    ok: bool = Field(True, description="Simple acknowledgement response.")


class ThumbFeedbackRequest(BaseModel):
    submission: SubmissionContext = Field(..., description="Submission metadata generated client-side.")
    vote: str = Field(..., pattern="^(up|down)$", description="Thumbs up ('up') or thumbs down ('down').")
    voted_at: datetime = Field(..., description="ISO-8601 UTC timestamp of when feedback was given.")


class EditFeedbackRequest(BaseModel):
    submission: SubmissionContext = Field(..., description="Submission metadata generated client-side.")
    edited_text: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User's preferred version of the flipped text.",
    )
    edited_at: datetime = Field(..., description="ISO-8601 UTC timestamp of when edit was submitted.")


class GenerateResponseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000, description="A social media post to flip.")
    submission: SubmissionContext = Field(
        ...,
        description="Submission metadata generated client-side at flip time.",
    )


class FlipResponse(BaseModel):
    flipped_text: str = Field(..., description="The rewritten post with opposite political stance.")
    explanation: str = Field(
        ...,
        description="Specific features considered when flipping (tone, framing, issues, rhetoric, etc.).",
    )


class ModelOption(BaseModel):
    model_id: str = Field(..., description="Public model identifier.")
    display_name: str = Field(..., description="Model display name for UI.")
    provider: str = Field(..., description="Provider family for this model.")


class ModelCatalogResponse(BaseModel):
    default_model_id: str = Field(..., description="Default model identifier used by the backend.")
    models: list[ModelOption] = Field(..., description="Available models for user selection.")

