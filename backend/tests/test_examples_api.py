from fastapi.testclient import TestClient

from app.examples import load_examples
from app.main import app


def test_examples_suggestions_default_count():
    catalog = load_examples()
    with TestClient(app) as client:
        response = client.get("/examples/suggestions")
    assert response.status_code == 200
    payload = response.json()
    examples = payload.get("examples") or []
    assert len(examples) == min(3, len(catalog))
    ids = {example["id"] for example in examples}
    assert len(ids) == len(examples)


def test_examples_random_returns_valid_entry():
    with TestClient(app) as client:
        response = client.get("/examples/random")
    assert response.status_code == 200
    payload = response.json()
    assert "id" in payload and payload["id"]
    assert "title" in payload and payload["title"]
    assert "input_text" in payload and payload["input_text"]


def test_examples_random_respects_exclusion():
    catalog = load_examples()
    excluded_id = catalog[0].id
    with TestClient(app) as client:
        response = client.get(f"/examples/random?exclude_id={excluded_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] != excluded_id or len(catalog) == 1
