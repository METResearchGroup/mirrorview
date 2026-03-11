# Pyright strict findings log

This file records the notable fixes made to reach `uv run pyright .` with `typeCheckingMode=strict` in `backend/`.

## Notable fixes
- Added strict typings across tests (fixture annotations, request payload dict typing, datetime values for Pydantic models).
- Tightened internal typing in model registry + DI boundaries to avoid `Unknown` propagation from YAML config data.
- Adjusted `UnitOfWork` abstraction so `transaction()` is a real `AsyncContextManager` and plays well with strict typing.

## Local suppressions
- `backend/ml_tooling/llm/llm_service.py` locally suppresses Pyright’s `reportUnknown*` diagnostics because it integrates with third-party libraries that do not expose complete typing information (avoids false positives while keeping the rest of the project strict).
