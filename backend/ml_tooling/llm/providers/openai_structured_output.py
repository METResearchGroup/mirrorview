"""OpenAI-specific helpers for strict JSON-schema responses."""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel


def format_openai_strict_json_schema(response_model: type[BaseModel]) -> dict[str, Any]:
    schema = response_model.model_json_schema()
    fixed_schema = _strict_schema(schema)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": response_model.__name__.lower(),
            "strict": True,
            "schema": fixed_schema,
        },
    }


def _strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    schema_copy = copy.deepcopy(schema)
    _patch_recursive(schema_copy)
    return schema_copy


def _patch_recursive(obj: Any) -> None:
    if isinstance(obj, dict):
        if obj.get("type") == "object":
            obj["additionalProperties"] = False
        for value in obj.values():
            _patch_recursive(value)
    elif isinstance(obj, list):
        for item in obj:
            _patch_recursive(item)
