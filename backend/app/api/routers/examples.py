from __future__ import annotations

import random

from fastapi import APIRouter, HTTPException, Query

from app.examples import load_examples
from app.schemas import ExampleResponse, ExampleSuggestionsResponse

router = APIRouter()


@router.get("/examples/suggestions", response_model=ExampleSuggestionsResponse)
def get_example_suggestions(
    count: int = Query(
        3,
        ge=1,
        le=10,
        description="Number of unique suggestions to return from the catalog.",
    ),
) -> ExampleSuggestionsResponse:
    catalog = load_examples()
    if not catalog:
        return ExampleSuggestionsResponse(examples=[])

    k = min(count, len(catalog))
    suggestions = random.sample(catalog, k)
    return ExampleSuggestionsResponse(examples=suggestions)


@router.get("/examples/random", response_model=ExampleResponse)
def get_random_example(
    exclude_id: list[str] | None = Query(
        None,
        description="Optional example IDs to avoid when sampling a single entry.",
    ),
) -> ExampleResponse:
    catalog = load_examples()
    if not catalog:
        raise HTTPException(status_code=500, detail="Examples catalog is empty.")

    exclusion = set(exclude_id or [])
    filtered_catalog = [example for example in catalog if example.id not in exclusion]
    candidates = filtered_catalog or list(catalog)
    return random.choice(candidates)
