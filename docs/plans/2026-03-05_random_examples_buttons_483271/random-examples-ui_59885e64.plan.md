---
name: random-examples-ui
overview: Add a curated, backend-served random examples feature that surfaces 3 suggestion buttons plus a “Get a random example” button above the input textarea in the Next.js prototype. Clicking any button populates the textarea with example text that the user can edit before submitting the existing flip flow.
todos:
  - id: before-screenshots
    content: Capture baseline UI screenshots (4-button strip absent) and save to `docs/plans/2026-03-05_random_examples_buttons_483271/images/before/` (run happy flow on current UI).
    status: completed
  - id: plan-assets-folder
    content: Create plan asset folder `docs/plans/2026-03-05_random_examples_buttons_483271/` with `images/before/` and `images/after/` subfolders.
    status: completed
  - id: backend-catalog-and-schemas
    content: Add curated examples catalog (repo file) + Pydantic schemas in `backend/app/schemas.py` for examples responses.
    status: completed
  - id: backend-examples-router
    content: Implement `GET /examples/suggestions` and `GET /examples/random` in new `backend/app/api/routers/examples.py`, wire into `backend/app/api/routers/__init__.py` and `backend/app/main.py`.
    status: completed
  - id: backend-rate-limits
    content: Extend rate-limit policy and scope mapping in `backend/app/security.py` for examples endpoints.
    status: completed
  - id: backend-tests
    content: Add `backend/tests/test_examples_api.py` to validate suggestions/random endpoints and uniqueness/exclude behavior.
    status: completed
  - id: frontend-examples-buttons
    content: Update `flip-prototype/app/page.tsx` to fetch 3 suggestions on mount and render 4 buttons above textarea; clicking populates `inputText` and resets downstream state; sampler fetches `/examples/random` (excluding current suggestion ids).
    status: completed
  - id: verify-and-lint
    content: Run `cd backend && uv run pytest` and `cd flip-prototype && npm run lint`; manually click through UI happy flow locally.
    status: completed
  - id: after-screenshots
    content: Capture updated UI screenshots (4-button strip present and working) and save to `docs/plans/2026-03-05_random_examples_buttons_483271/images/after/` (same happy flow as before).
    status: completed
isProject: false
---

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview

We’ll add a small curated “examples” API to the FastAPI backend and a matching UI strip in the `flip-prototype` app. The backend will serve (a) a batch of 3 unique random suggestions and (b) a single random example for a sampler button. The frontend will render 4 buttons above the textarea; clicking any button fills `inputText` (editable) and resets downstream generation/feedback state to avoid stale output.

## Happy Flow

1. User opens the prototype page in `[flip-prototype/app/page.tsx](flip-prototype/app/page.tsx)`.
2. On mount, the page already calls `GET /models`; we’ll additionally call `GET /examples/suggestions?count=3` using the same `NEXT_PUBLIC_API_URL` base URL logic.
3. The UI renders an “Examples” strip above the textarea with 4 buttons:
  - 3 suggestion buttons labeled with each example’s `title` (from `/examples/suggestions`).
  - 1 sampler button (“Get a random example”).
4. User clicks one of the 3 suggestion buttons → frontend sets `inputText` to that example’s `input_text` and clears `flippedText`, `explanation`, `feedback`, `customVersion`, and `submission` state in `[flip-prototype/app/page.tsx](flip-prototype/app/page.tsx)`.
5. User optionally edits the populated textarea.
6. User clicks **Flip** → existing `handleFlip()` submits `POST /generate_response` to `[backend/app/api/routers/generate.py](backend/app/api/routers/generate.py)` with the edited text.
7. User clicks “Get a random example” → frontend calls `GET /examples/random` (optionally excluding currently displayed suggestion IDs) and populates/resets state the same way.

## Implementation details

### Backend API

- **New curated catalog**
  - Add a curated examples catalog file, e.g. `[backend/app/examples/catalog.json](backend/app/examples/catalog.json)` (or `.yaml`).
  - Add a small loader helper, e.g. `[backend/app/examples/loader.py](backend/app/examples/loader.py)`, that loads and validates the catalog once (module-level cache).
  - Ensure `input_text` is \le 4000 chars to match `[backend/app/schemas.py](backend/app/schemas.py)` `GenerateResponseRequest.text`.
- **New schemas** in `[backend/app/schemas.py](backend/app/schemas.py)`
  - `ExampleResponse` with fields: `id: str`, `title: str`, `input_text: str`, optional `tags: list[str] = []`.
  - `ExampleSuggestionsResponse` with `examples: list[ExampleResponse]`.
- **New router**
  - Create `[backend/app/api/routers/examples.py](backend/app/api/routers/examples.py)` with:
    - `GET /examples/suggestions` returning `ExampleSuggestionsResponse`.
      - Query params: `count: int = 3` (clamp to `[1, 10]` and to catalog length).
      - Select unique examples via `random.sample()`.
    - `GET /examples/random` returning `ExampleResponse`.
      - Optional query param: `exclude_id: list[str] = []` to avoid returning one of the 3 suggestions.
      - Filter catalog by excluded IDs; if exhausted, fall back to full catalog.
- **Wire router**
  - Export in `[backend/app/api/routers/__init__.py](backend/app/api/routers/__init__.py)`.
  - Include in `[backend/app/main.py](backend/app/main.py)` alongside `generate_router` and `feedback_router`.
- **Rate limiting**
  - Extend `[backend/app/security.py](backend/app/security.py)`:
    - `build_rate_limit_policy()` to include `examples_suggestions` and `examples_random` using env defaults such as `60/minute,1000/hour`.
    - `resolve_rate_limit_scope()` to map `/examples/suggestions` and `/examples/random`.
- **Backend tests**
  - Add tests in a new file like `[backend/tests/test_examples_api.py](backend/tests/test_examples_api.py)` using `fastapi.testclient.TestClient`.
  - Assertions:
    - `GET /examples/suggestions?count=3` → 200, JSON has `examples` length `<=3`, unique `id`s, each `input_text` non-empty.
    - `GET /examples/random` → 200, has required fields.
    - `GET /examples/random?exclude_id=<three suggestion ids>` still returns an example (unless catalog is smaller; handle that case in test with conditional expectations).

### Frontend UI

- **Types and fetch helpers** in `[flip-prototype/app/page.tsx](flip-prototype/app/page.tsx)`
  - Add `Example` and `ExampleSuggestionsResponse` TS types.
  - Add state:
    - `exampleSuggestions: Example[]`
    - `isLoadingSuggestions: boolean`
    - `isLoadingRandomExample: boolean`
  - Add `loadExampleSuggestions()` in the existing `useEffect` (near the model catalog fetch), guarded by `baseUrl`.
- **UI placement**
  - In the “Text to flip” card, inside `CardContent` and **above** the `<Textarea />`, render:
    - a `Label` (e.g. “Examples”)
    - a 4-button grid using existing `[flip-prototype/components/ui/button.tsx](flip-prototype/components/ui/button.tsx)`
      - Layout classes: `grid grid-cols-2 gap-2 sm:grid-cols-4`.
- **Click handlers**
  - `applyExample(example: Example)` that:
    - `setInputText(example.input_text)`
    - resets: `setFlippedText(null)`, `setExplanation(null)`, `setFeedback(null)`, `setCustomVersion("")`, `setSubmission(null)`
  - Suggestion buttons call `applyExample(suggestion)`.
  - Sampler button calls `GET /examples/random` (include `exclude_id` from current `exampleSuggestions.map(e => e.id)`), then `applyExample(returnedExample)`.

## Manual Verification

- **Backend**
  - Start backend (persistence disabled is fine):

```bash
cd backend
export RUN_MODE=local
export PERSISTENCE_ENABLED=false
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Verify endpoints respond:
  - `GET http://localhost:8000/examples/suggestions?count=3` returns JSON with `examples` array.
  - `GET http://localhost:8000/examples/random` returns a single example.
- Run backend tests:

```bash
cd backend
uv run pytest
```

- Expected: exit code 0; examples API tests pass.
- **Frontend**
  - Start frontend:

```bash
cd flip-prototype
export NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

- In browser at `http://localhost:3000`:
  - Confirm 4 example buttons appear **above** the textarea.
  - Click each of the 3 suggestion buttons → textarea populates; you can edit text.
  - Click “Get a random example” → textarea populates with a (likely different) example.
  - After clicking any example button, confirm any prior “Flipped output” section disappears (state reset).
  - Click **Flip** and confirm the normal generation flow still works.
- Lint frontend:

```bash
cd flip-prototype
npm run lint
```

- Expected: lint exits successfully.

## Alternative approaches

- **Frontend-only curated examples (Option A)**: simpler and zero backend changes, but requires redeploying the UI to update examples.
- **DB-backed random sampling (Option C)**: could surface real historical examples, but is unsafe without strong scoping/auth (risk of leaking user text). We chose **curated backend examples** to keep content controlled, updateable server-side, and compatible with persistence-disabled local development.

