import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import llm

client = TestClient(app)


def _mock(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        llm.httpx, "post", lambda url, **kw: httpx.Client(transport=transport).post(url, **kw)
    )


def _chat(content: str):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_check_ok(monkeypatch):
    good = json.dumps({"category": "Payment", "priority": "HIGH", "summary": "s", "reply_draft": "r"})
    _mock(monkeypatch, lambda req: _chat(good))
    resp = client.get("/api/llm/check")
    body = resp.json()
    assert resp.status_code == 200
    assert body["ok"] is True
    assert body["parsed"]["category"] == "payment"
    assert body["content"] == good


def test_check_non_json_content_is_returned(monkeypatch):
    _mock(monkeypatch, lambda req: _chat("Sorry, I can't help with that."))
    resp = client.get("/api/llm/check")
    body = resp.json()
    assert resp.status_code == 502
    assert body["ok"] is False
    assert body["content"] == "Sorry, I can't help with that."
    assert "LLMError" in body["error"]


def test_check_http_error_returns_raw_body(monkeypatch):
    _mock(monkeypatch, lambda req: httpx.Response(401, text='{"error": "bad key"}'))
    resp = client.get("/api/llm/check")
    body = resp.json()
    assert resp.status_code == 502
    assert body["http_status"] == 401
    assert "bad key" in body["raw_response"]


def test_check_connection_error(monkeypatch):
    def boom(req):
        raise httpx.ConnectError("refused")

    _mock(monkeypatch, boom)
    body = client.get("/api/llm/check").json()
    assert body["ok"] is False
    assert "ConnectError" in body["error"]
    assert body["http_status"] is None
