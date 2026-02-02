from pydantic import BaseModel, Field


class GenerateResponseRequest(BaseModel):
    text: str = Field(..., min_length=1, description="A social media post to flip.")


class FlipResponse(BaseModel):
    flipped_text: str = Field(..., description="The rewritten post with opposite political stance.")
    explanation: str = Field(
        ...,
        description="Specific features considered when flipping (tone, framing, issues, rhetoric, etc.).",
    )

