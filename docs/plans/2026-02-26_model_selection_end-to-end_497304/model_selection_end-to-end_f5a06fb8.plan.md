---
name: model_selection_end-to-end
overview: Capture the verification steps that ensure the model selection work functions end-to-end by checking backend symmetry (catalog, validation, persistence) alongside the frontend dropdown flow, and archive the resulting artifacts in docs/plans/2026-02-26_model_selection_end-to-end_497304/.
todos:
  - id: capture-before-screenshot
    content: Use the browser tool to capture the current app screen showing the Model dropdown happy path and save the image in docs/plans/2026-02-26_model_selection_end-to-end_497304/images/before/.
    status: completed
  - id: validate-backend-flow
    content: Run backend verification steps (tests, API smoke requests, health check) described above to ensure catalog, validation, and execution behave before touching the UI.
    status: completed
  - id: validate-frontend-flow
    content: Perform frontend verification steps (lint/build, dev server, dropdown selection, flip + feedback flows, error handling) with NEXT_PUBLIC_API_URL pointing to the local backend.
    status: completed
  - id: capture-after-screenshot
    content: After the verification work, use the browser tool to capture the updated happy-path UI state and store the image in docs/plans/2026-02-26_model_selection_end-to-end_497304/images/after/.
    status: completed
isProject: false
---

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Overview

Outline the verification plan for the model selection feature so we can prove the backend catalog and validation, the generation service persistence, and the frontend dropdown all cooperate as intended; store every asset under docs/plans/2026-02-26_model_selection_end-to-end_497304/.

## Happy Flow

1. `flip-prototype/app/page.tsx` on load calls `GET /models` from `[backend/app/api/routers/generate.py](backend/app/api/routers/generate.py)` and renders the dropdown populated with `model_id`/`display_name` entries, defaulting to the registry-provided `gpt-5-nano`.
2. Selecting a model makes the submission payload include `submission.model_id`, which arrives at `[backend/app/services/generation_service.py](backend/app/services/generation_service.py)` and calls `model_registry.resolve_litellm_route()` before invoking `structured_completion(..., model=resolved_route)` so the provider receives the right route metadata and both submission and generation records persist the chosen `model_id`.
3. The same backend exposes `GET /models` implemented in `[backend/app/api/routers/generate.py](backend/app/api/routers/generate.py)`, runs through `[backend/ml_tooling/llm/config/model_registry.py](backend/ml_tooling/llm/config/model_registry.py)` to list available models, and rejects unknown/unavailable model IDs with 4xx responses, ensuring runtime safety for the UI flows.
4. A success flip request returns `flipped_text`/`explanation` plus a backend log entry showing the resolved `litellm_route`, closing the loop on frontend selection → backend execution → persisted metadata.

## Manual Verification

- From `backend/` run `uv run pytest` (or `uv run pytest -k "not persistence_integration"` if Docker dependencies fail) and confirm every test suite (registry, generate_response, generation_service, persistence) passes without failures.
- Start the backend with `cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` and manually exercise:
  - `GET http://localhost:8000/models` returns 200 with `default_model_id`, a non-empty `models` array, and each entry containing `model_id`, `display_name`, and `provider`.
  - `POST http://localhost:8000/generate_response` with a valid `submission.model_id` from `/models` returns 200 with `flipped_text` and `explanation` and logs the matching model ID.
  - `POST` with `model_id` of a missing entry returns 400 plus a message mentioning the unknown ID, and with `model_id` of a disabled entry returns 400 describing unavailability.
  - `GET http://localhost:8000/health` returns `{"status":"ok"}`.
- From `flip-prototype/` run `npm run lint` and `npm run build` to ensure frontend compiles.
- With `NEXT_PUBLIC_API_URL=http://localhost:8000`, start the frontend (`npm run dev`) and in the browser:
  - Confirm the **Model** dropdown loads options matching `/models` with `gpt-5-nano` preselected and is disabled until catalog loads.
  - Choose a different model, enter sample text, click **Flip**, and verify the flipped output/ explanation renders while the network request includes the selected `model_id` and backend logs match.
  - Trigger the feedback flow to confirm submissions carry the `model_id` in their payloads.
  - Stop the backend to confirm the UI surfaces a clean error message instead of crashing.

## Alternative Approaches

- Using only automated tests (pytest + jest) saves time but misses integration regressions between UI dropdown and backend validation; the chosen manual backend + frontend smoke path ensures the entire request lifecycle and persistence hooks are verified.

