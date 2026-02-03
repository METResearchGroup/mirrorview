import importlib
import logging
from datetime import datetime, timezone
from uuid import uuid4


def _reload_app_with_env(monkeypatch, cors_origins: str | None = None):
    if cors_origins is None:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ORIGINS", cors_origins)

    # `app` is created at import time, so reload to apply env changes.
    import app.main as main

    importlib.reload(main)
    return main


def test_feedback_edit_ok(monkeypatch, caplog):
    main = _reload_app_with_env(monkeypatch, cors_origins="http://localhost:3000")

    submission_id = str(uuid4())
    payload = {
        "submission": {
            "id": submission_id,
            "created_at": "2026-02-03T00:00:00.000Z",
            "input_text": "hello",
        },
        "edited_text": "my preferred version",
        "edited_at": datetime.now(timezone.utc).isoformat(),
    }

    from fastapi.testclient import TestClient

    caplog.set_level(logging.INFO)
    client = TestClient(main.app)
    res = client.post("/feedback/edit", json=payload)

    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert submission_id in caplog.text
    assert "edit_feedback" in caplog.text


def test_feedback_edit_empty_text_422(monkeypatch):
    main = _reload_app_with_env(monkeypatch, cors_origins="http://localhost:3000")

    payload = {
        "submission": {
            "id": str(uuid4()),
            "created_at": "2026-02-03T00:00:00.000Z",
            "input_text": "hello",
        },
        "edited_text": "",
        "edited_at": datetime.now(timezone.utc).isoformat(),
    }

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    res = client.post("/feedback/edit", json=payload)

    assert res.status_code == 422


def test_feedback_edit_missing_submission_422(monkeypatch):
    main = _reload_app_with_env(monkeypatch, cors_origins="http://localhost:3000")

    payload = {
        "edited_text": "my preferred version",
        "edited_at": datetime.now(timezone.utc).isoformat(),
    }

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    res = client.post("/feedback/edit", json=payload)

    assert res.status_code == 422

