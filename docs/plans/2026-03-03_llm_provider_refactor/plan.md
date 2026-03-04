---
name: llm-provider-refactor
overview: Refactor `backend/ml_tooling/llm/providers/` to remove Groq/Gemini entirely (code + config), and DRY up the remaining providers (OpenAI/Anthropic/OpenRouter) using mixins for API-key initialization, strict JSON-schema structured output formatting, `supports_model`, and shared completion-kwargs construction.
todos:
  - id: remove-groq-gemini
    content: Delete `groq_provider.py`/`gemini_provider.py`, remove registry wiring, remove `models.yaml` sections, remove env-var loader keys, and scrub backend docs/examples referencing Groq/Gemini.
    status: completed
  - id: add-provider-mixins
    content: Add `backend/ml_tooling/llm/providers/provider_mixins.py` (state + env-api-key + supports_model + strict-json-schema + standard kwargs builder mixins).
    status: completed
  - id: refactor-remaining-providers
    content: Refactor `openai_provider.py`, `anthropic_provider.py`, `openrouter_provider.py` to inherit mixins and remove duplicated code (init/api_key/supports_model/structured output/kwargs).
    status: completed
  - id: verification
    content: Run `uv run pytest` and `uv run ruff check .`, plus import + `/models` smoke checks; ensure providers list is only openai/anthropic/openrouter and model catalog still works.
    status: completed
isProject: false
---

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Overview

We’ll simplify the LLM provider layer by (a) deleting Groq and Gemini support end-to-end (provider classes, registry wiring, model config entries, env-var plumbing, and docs), and (b) refactoring the remaining providers (OpenAI/Anthropic/OpenRouter) to share duplicated logic via mixins. This reduces maintenance surface area (especially the structured-output schema patching) while keeping provider-specific behavior explicit and easy to extend.

## Happy Flow

1. A request reaches `LLMService.structured_completion()` in `backend/ml_tooling/llm/llm_service.py`, selecting a public `model_id` (default from `ModelConfigRegistry.get_default_model()` in `backend/ml_tooling/llm/config/model_registry.py`).
2. `LLMService._get_provider_for_model()` uses `LLMProviderRegistry.get_provider(model_id)` from `backend/ml_tooling/llm/providers/registry.py` to find the provider instance whose `supports_model(model_id)` is true.
3. `ModelConfigRegistry.get_model_config(model_id)` loads `backend/ml_tooling/llm/config/models.yaml` and produces `model_config_dict = {"kwargs": ..., "litellm_route": ...}`.
4. If a `response_model` is provided, `provider.format_structured_output(...)` returns an OpenAI-style `response_format` dict using strict JSON schema (shared via mixin).
5. `provider.prepare_completion_kwargs(...)` merges config kwargs + user kwargs and resolves `litellm_route` (shared via mixin), returning a dict for `litellm.completion(**kwargs)`.
6. `LLMService` injects `api_key=provider.api_key` and executes the request.

## Plan

### 1) Remove Groq + Gemini support (code + config + docs)

- Delete provider modules:
  - `backend/ml_tooling/llm/providers/groq_provider.py`
  - `backend/ml_tooling/llm/providers/gemini_provider.py`
- Update provider registry bootstrapping:
  - `backend/ml_tooling/llm/providers/registry.py`
    - Remove imports of `GroqProvider` and `GeminiProvider`
    - Remove `LLMProviderRegistry.register(GroqProvider)` and `...register(GeminiProvider)`
- Remove model configuration blocks:
  - `backend/ml_tooling/llm/config/models.yaml`
    - Remove the entire `models.gemini:` block (including `safety_settings`)
    - Remove the entire `models.groq:` block (including `response_format`)
- Remove env-var plumbing for deleted providers:
  - `backend/lib/load_env_vars.py`
    - Remove `GOOGLE_AI_STUDIO_KEY` and `GROQ_API_KEY` from `_env_var_types`
    - Remove reads into `_env_vars[...]` for those keys
- Remove/adjust documentation and examples that reference the deleted providers:
  - `backend/README.md` remove `GOOGLE_AI_STUDIO_KEY` / `GROQ_API_KEY` from the “Provider credentials” snippet
  - Update example strings mentioning `gemini`/`groq` in:
    - `backend/ml_tooling/llm/providers/base.py`
    - `backend/ml_tooling/llm/llm_service.py`
    - `backend/ml_tooling/llm/config/model_registry.py`

### 2) Introduce shared mixins for the remaining providers

Create a small mixin module used only by OpenAI/Anthropic/OpenRouter:

- Add `backend/ml_tooling/llm/providers/provider_mixins.py` (or `backend/ml_tooling/llm/providers/mixins.py`) containing:
  - `ProviderStateMixin`: owns `_initialized: bool` + `_api_key: str|None` and a cooperative `__init__`.
  - `EnvApiKeyMixin`: implements `initialize(api_key: str|None)` + `api_key` property; requires a class attribute like `API_KEY_ENV_VAR: str`.
  - `SupportsModelMixin`: implements `supports_model(self, model_name: str) -> bool` as `model_name in self.supported_models`.
  - `StrictJsonSchemaMixin`: implements `format_structured_output(...)` and internal `deepcopy + recursive additionalProperties=False` patching once.
  - `StandardCompletionKwargsMixin`: implements `prepare_completion_kwargs(...)`:
    - `merged_kwargs = {**model_config.get("kwargs", {}), **kwargs}`
    - `model_route = model_config.get("litellm_route", model)`
    - include `messages` and optional `response_format`.

### 3) Refactor OpenAI/Anthropic/OpenRouter providers to be metadata-only

- Update these files to inherit mixins + `LLMProviderProtocol`:
  - `backend/ml_tooling/llm/providers/openai_provider.py`
  - `backend/ml_tooling/llm/providers/anthropic_provider.py`
  - `backend/ml_tooling/llm/providers/openrouter_provider.py`
- Remove duplicated methods that mixins cover:
  - delete per-provider `__init__` (use `ProviderStateMixin.__init__`)
  - delete duplicated `initialize`, `api_key`, `supports_model`, `format_structured_output`, `_patch_recursive`, and the common `prepare_completion_kwargs` (unless a provider truly diverges later)
- Keep only provider-specific metadata:
  - `provider_name`
  - `supported_models`
  - `API_KEY_ENV_VAR` (and any other minimal constants needed by mixins)

### 4) Tighten registry and runtime expectations

- Ensure `LLMProviderRegistry.get_provider()` behavior remains unchanged after provider removals.
- Optionally (small hygiene): register providers via a local tuple in `backend/ml_tooling/llm/providers/registry.py` to keep the file declarative.

## Manual Verification

- **Unit tests**:
  - `cd backend && uv run pytest`
  - Expected: exit code 0, tests including `backend/tests/test_generate_response.py::test_models_endpoint_returns_default_and_options` pass.
- **Lint**:
  - `cd backend && uv run ruff check .`
  - Expected: “All checks passed!” (or no new violations).
- **Import smoke tests** (fast failure for deleted providers):
  - `cd backend && uv run python -c "from ml_tooling.llm.providers.registry import LLMProviderRegistry; print(sorted(LLMProviderRegistry.list_providers()))"`
  - Expected output includes `['anthropic', 'openai', 'openrouter']` and does **not** include `gemini`/`groq`.
- **API sanity check**:
  - Start server: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
  - In another terminal: `curl -s http://localhost:8000/models | python -m json.tool`
  - Expected: `default_model_id` is `gpt-5-nano`; returned models include only those marked `available: true` in `backend/ml_tooling/llm/config/models.yaml`.

## Alternative approaches

- **Concrete base class** (rejected): would be slightly simpler than mixins, but introduces a “one true inheritance chain” and tends to accrete unrelated provider behaviors over time.
- **Helpers-only** (rejected): reduces duplication, but tends to keep provider files noisy (call sites still repeat the same patterns) and doesn’t leverage ABC satisfaction the way mixins do.
- **Mixins (chosen)**: keeps providers declarative while maintaining explicit composition and low coupling; easy to add/override a single behavior without reworking a base class.

