---
name: simplify-llm-provider-inheritance
overview: Refactor the LLM provider layer to replace the current multi-mixin inheritance stack with a single shared base provider class, while making OpenAI the only provider that supports strict JSON-schema structured outputs (and failing fast when structured outputs are requested for other providers).
todos:
  - id: assets-folder
    content: Create plan asset folder `docs/plans/2026-03-04_simplify_llm_provider_inheritance_843217/` (no UI screenshots).
    status: pending
  - id: base-provider
    content: Add `backend/ml_tooling/llm/providers/provider_base.py` implementing common init/api_key/supports_model/prepare_completion_kwargs; default `format_structured_output` returns None.
    status: pending
  - id: openai-structured-helper
    content: Add `backend/ml_tooling/llm/providers/openai_structured_output.py` with `format_openai_strict_json_schema()` helper (lift strict schema patching logic from current mixin).
    status: pending
  - id: update-providers
    content: Refactor `openai_provider.py`, `anthropic_provider.py`, `openrouter_provider.py` to inherit from `BaseLLMProvider`; only OpenAI overrides `format_structured_output`.
    status: pending
  - id: service-failfast
    content: Update `backend/ml_tooling/llm/llm_service.py` to raise when structured output requested but provider returns None.
    status: pending
  - id: remove-mixins
    content: Remove or slim `backend/ml_tooling/llm/providers/provider_mixins.py`; ensure no remaining imports/usages.
    status: pending
  - id: tests
    content: Add `backend/tests/test_llm_provider_refactor.py` covering OpenAI strict schema output, non-OpenAI unsupported structured outputs, and LLMService fail-fast behavior.
    status: pending
isProject: false
---

# Simplify LLM provider inheritance (Option A)

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Assets

- Plan assets: `docs/plans/2026-03-04_simplify_llm_provider_inheritance_843217/`
  - No UI screenshots expected (backend-only refactor)

## Overview

Today each provider class is composed from several mixins (`EnvApiKeyMixin`, `SupportsModelMixin`, `StrictSchemaCompletionMixin`) plus `LLMProviderProtocol`, which increases indirection and makes behavior hard to see at a glance. We’ll replace that with a single shared base class that implements the common behavior (API key state, initialization, model support, kwargs preparation), and we’ll scope strict JSON-schema structured output formatting to OpenAI only. For non-OpenAI providers, structured outputs will be explicitly unsupported (fail fast) rather than silently attempting to parse arbitrary text as JSON.

## Current shape (what we’re simplifying)

Providers currently look like:

```11:16:/Users/mark/Documents/work/mirrorview/backend/ml_tooling/llm/providers/openai_provider.py
class OpenAIProvider(
    EnvApiKeyMixin,
    StrictSchemaCompletionMixin,
    SupportsModelMixin,
    LLMProviderProtocol,
):
```

And the “behavior” is spread across mixins:

```22:108:/Users/mark/Documents/work/mirrorview/backend/ml_tooling/llm/providers/provider_mixins.py
class EnvApiKeyMixin(ProviderStateMixin):
    ...

class SupportsModelMixin:
    ...

class StrictJsonSchemaMixin:
    ...

class StandardCompletionKwargsMixin:
    ...
```

## Happy Flow

1. `LLMService.structured_completion()` in `[backend/ml_tooling/llm/llm_service.py](backend/ml_tooling/llm/llm_service.py)` selects a provider via `LLMProviderRegistry.get_provider(model)` in `[backend/ml_tooling/llm/providers/registry.py](backend/ml_tooling/llm/providers/registry.py)`.
2. Provider is lazily initialized (`provider.initialize()`), which sets `_api_key` and `_initialized` (currently done via `EnvApiKeyMixin`).
3. `_prepare_completion_kwargs()` asks the provider to format structured output (`provider.format_structured_output(response_model, model_config_dict)`).
  - **New behavior**: only `OpenAIProvider` returns an OpenAI strict JSON-schema `response_format`. Other providers return `None`.
  - If `response_format` is requested but the provider returns `None`, `LLMService` raises a clear exception before making a LiteLLM request.
4. Provider builds completion kwargs (model routing + kwargs merge) and `LLMService` injects `api_key=provider.api_key` per request (avoids global LiteLLM key).

## Implementation plan

### 1) Introduce a single shared base provider class

- Add a concrete/abstract base class (suggested new file): `[backend/ml_tooling/llm/providers/provider_base.py](backend/ml_tooling/llm/providers/provider_base.py)`
  - `BaseLLMProvider(LLMProviderProtocol, ABC)`
  - Implements:
    - `__init__` initializes `_initialized: bool = False`, `_api_key: str | None = None`
    - `initialize(api_key: str | None = None)`
      - if `api_key is None`: load via `settings().require_api_key(self.API_KEY_ENV_VAR)`
      - idempotent: only set `_api_key` once
    - `api_key` property: raises if not initialized
    - `supports_model(model_name: str) -> bool`: default membership check
    - `prepare_completion_kwargs(...) -> dict[str, Any]`: default merge of `model_config['kwargs']` and user kwargs, plus model routing via `model_config.get('litellm_route', model)`
    - `format_structured_output(...) -> dict[str, Any] | None`: **default returns `None`** (structured output unsupported unless provider overrides)
  - Providers will now be “one inheritance edge”: `class OpenAIProvider(BaseLLMProvider)` etc.

Proposed shape (sketch):

```python
# backend/ml_tooling/llm/providers/provider_base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel

from lib.load_env_vars import settings
from ml_tooling.llm.providers.base import LLMProviderProtocol


class BaseLLMProvider(LLMProviderProtocol, ABC):
    API_KEY_ENV_VAR: ClassVar[str]

    def __init__(self) -> None:
        self._initialized = False
        self._api_key: str | None = None

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            raise RuntimeError(
                f"{self.__class__.__name__} has not been initialized with an API key. "
                "Call initialize() before making LiteLLM requests."
            )
        return self._api_key

    def initialize(self, api_key: str | None = None) -> None:
        if api_key is None:
            api_key = settings().require_api_key(self.API_KEY_ENV_VAR)
        if not self._initialized:
            self._api_key = api_key
            self._initialized = True

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.supported_models

    def format_structured_output(
        self, response_model: type[BaseModel], model_config: dict[str, Any]
    ) -> dict[str, Any] | None:
        return None

    def prepare_completion_kwargs(
        self,
        model: str,
        messages: list[dict],
        response_format: dict[str, Any] | None,
        model_config: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self._initialized:
            self.initialize()

        merged_kwargs = {**model_config.get("kwargs", {}), **kwargs}
        out: dict[str, Any] = {
            "model": model_config.get("litellm_route", model),
            "messages": messages,
            **merged_kwargs,
        }
        if response_format is not None:
            out["response_format"] = response_format
        return out
```

### 2) Make strict JSON schema formatting OpenAI-only

- Convert `StrictJsonSchemaMixin` into a **standalone helper** module, so it’s not part of provider inheritance:
  - New file: `[backend/ml_tooling/llm/providers/openai_structured_output.py](backend/ml_tooling/llm/providers/openai_structured_output.py)`
  - Export: `format_openai_strict_json_schema(response_model: type[BaseModel]) -> dict[str, Any]`
  - Implementation can be lifted directly from `StrictJsonSchemaMixin.format_structured_output()` and its `_patch_recursive` logic.

### 3) Update providers to use the base class

- Update:
  - `[backend/ml_tooling/llm/providers/openai_provider.py](backend/ml_tooling/llm/providers/openai_provider.py)`
  - `[backend/ml_tooling/llm/providers/anthropic_provider.py](backend/ml_tooling/llm/providers/anthropic_provider.py)`
  - `[backend/ml_tooling/llm/providers/openrouter_provider.py](backend/ml_tooling/llm/providers/openrouter_provider.py)`

Desired end-state:

- `OpenAIProvider(BaseLLMProvider)` overrides `format_structured_output()` to call `format_openai_strict_json_schema()`.
- `AnthropicProvider(BaseLLMProvider)` and `OpenRouterProvider(BaseLLMProvider)` rely on base default (`None`).

### 4) Make `LLMService` fail fast when structured output isn’t supported

- Update `[backend/ml_tooling/llm/llm_service.py](backend/ml_tooling/llm/llm_service.py)` in `_prepare_completion_kwargs()`:
  - After calling `provider.format_structured_output(...)`:
    - If `response_format is not None` and `response_format_dict is None`: raise `ValueError` (or a project-specific exception, if you prefer) explaining structured outputs aren’t supported for that `provider.provider_name` / `model`.

This aligns with the contract documented in `LLMProviderProtocol.format_structured_output()` (may return `None` when unsupported).

### 5) Remove or slim down `provider_mixins.py`

- Update `[backend/ml_tooling/llm/providers/provider_mixins.py](backend/ml_tooling/llm/providers/provider_mixins.py)`:
  - Either delete it (preferred) or leave only small helper(s) if anything remains referenced.
  - Ensure no providers import mixins anymore.

### 6) Tests (focused + hermetic)

Add a new unit test file, e.g. `[backend/tests/test_llm_provider_refactor.py](backend/tests/test_llm_provider_refactor.py)`:

- **OpenAI structured output**: `OpenAIProvider.format_structured_output()` returns dict with `{"type": "json_schema", ... "strict": True}` and schema includes `additionalProperties: false` on objects.
- **Non-OpenAI structured output unsupported**: `AnthropicProvider.format_structured_output(...) is None` and `OpenRouterProvider... is None`.
- **Service fail-fast**: calling `LLMService._prepare_completion_kwargs(..., response_format=SomeModel, provider=AnthropicProvider())` raises with a clear error message.
  - Use `provider.initialize(api_key="test")` to avoid env dependence.

## Manual Verification

- From `backend/` sync + run tests:
  - `uv sync`
  - `uv run pytest` (expect: all tests pass)
- Quick import smoke-check:
  - `uv run python -c "from ml_tooling.llm.providers.registry import LLMProviderRegistry; print(LLMProviderRegistry.list_providers())"` (expect: `['openai','anthropic','openrouter']` in some order)
- Structured output support:
  - `uv run python -c "from ml_tooling.llm.llm_service import LLMService; from pydantic import BaseModel;\nclass X(BaseModel): a:int\nsvc=LLMService();\n# should raise (if default model set to non-openai) only when selecting non-openai explicitly"`
    - (We’ll keep this as a developer sanity check; unit tests are the real gate.)

## Alternative approaches

- **Keep mixins but reduce count**: collapse to 1–2 mixins (e.g., `EnvApiKeyMixin` + `CompletionKwargsMixin`).
  - Pros: minimal churn.
  - Cons: still multi-inheritance, behavior remains distributed.
- **Composition over inheritance**: providers hold `ApiKeySource`, `StructuredOutputFormatter`, `KwargsBuilder` objects.
  - Pros: very explicit dependencies and easy provider-by-provider variation.
  - Cons: more boilerplate in a small codebase; arguably overkill now.

We chose **Option A (single base class)** because it keeps provider definitions tiny, eliminates MRO/mixin indirection, and matches how the system is already used (providers are simple singletons with small overridable seams).