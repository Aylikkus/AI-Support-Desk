import json

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.main import app
from app.services import llm as llm_module

client = TestClient(app)


def _mock(monkeypatch, messages):
    fake = GenericFakeChatModel(messages=iter(messages))
    monkeypatch.setattr(llm_module, "get_chat_model", lambda *args, **kwargs: fake)


def test_check_ok(monkeypatch):
    good = json.dumps(
        {"category": "Payment", "priority": "HIGH", "summary": "s", "reply_draft": "r"}
    )
    _mock(monkeypatch, [AIMessage(content=good)])
    resp = client.get("/api/llm/check")
    body = resp.json()
    assert resp.status_code == 200
    assert body["ok"] is True
    assert body["parsed"]["category"] == "payment"
    assert body["content"] == good


def test_check_non_json_content_is_returned(monkeypatch):
    _mock(monkeypatch, [AIMessage(content="Sorry, I can't help with that.")])
    resp = client.get("/api/llm/check")
    body = resp.json()
    assert resp.status_code == 502
    assert body["ok"] is False
    assert body["content"] == "Sorry, I can't help with that."
    assert "LLMError" in body["error"]


def test_check_provider_error(monkeypatch):
    class Boom:
        def bind(self, **kwargs):
            return self

        def invoke(self, messages, **kwargs):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(llm_module, "get_chat_model", lambda *args, **kwargs: Boom())
    body = client.get("/api/llm/check").json()
    assert body["ok"] is False
    assert "RuntimeError" in body["error"]
    assert body["content"] is None
