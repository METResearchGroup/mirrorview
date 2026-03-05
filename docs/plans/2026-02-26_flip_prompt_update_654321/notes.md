# Flip Prompt Update (2026-02-26)

## Overview

Align the `FLIP_PROMPT` string with the requested social psychology instructions so every flip response mirrors the opposite U.S. political stance while preserving tone, intensity, and target directionality.

## Changes

- Replaced the old prompt text in `backend/prompts.py` with the new block that explicitly describes the researcher use case, opposite-stance mirroring, figure/group targeting, and emotional register rules.
- Confirmed `backend/app/api/routers/generate.py` still imports `FLIP_PROMPT` and does not contain hard-coded references to the previous wording.

## Verification

- `cd backend && python - <<'PY'\nfrom prompts import FLIP_PROMPT\nprint(FLIP_PROMPT)\nPY` (printed prompt text matches the new researcher instructions).
