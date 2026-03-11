from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

Binary01 = Annotated[int, Field(ge=0, le=1)]


class Stage1CriteriaLabel(BaseModel):
    """Six binary criteria for reward-model Stage 1 filtering."""

    political_us: Binary01
    opinion_not_news: Binary01
    complete: Binary01
    self_contained: Binary01
    target_topic: Binary01
    clear_political_stance: Binary01
