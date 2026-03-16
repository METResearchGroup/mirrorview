from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import FlipResponse


def test_flip_response_rejects_blank_flipped_text() -> None:
    with pytest.raises(ValidationError, match="flipped_text must not be empty or whitespace-only"):
        FlipResponse(flipped_text="   ", explanation="reason")
