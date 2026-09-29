import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import tickets as tickets_api
from app.db.session import Base, get_db
from app.main import app
from app.models import ticket  # noqa: F401
from app.schemas.ticket import Analysis
from app.services.llm import LLMError

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def client():
    Base.metadata.create_all(engine)

    def override():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


PAYLOAD = {"customer_name": "Ivan", "customer_email": "ivan@example.com", "message": "Charged but no order!"}


def test_create_ticket_processed(client, monkeypatch):
    monkeypatch.setattr(
        tickets_api,
        "analyze_ticket",
        lambda name, msg: Analysis(category="payment", priority="high", summary="Charged w/o order", reply_draft="Hi!"),
    )
    resp = client.post("/api/tickets", json=PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "processed"
    assert body["category"] == "payment"
    assert body["priority"] == "high"
    assert client.get(f"/api/tickets/{body['id']}").json()["reply_draft"] == "Hi!"


def test_llm_failure_keeps_ticket(client, monkeypatch):
    def boom(name, msg):
        raise LLMError("down")

    monkeypatch.setattr(tickets_api, "analyze_ticket", boom)
    resp = client.post("/api/tickets", json=PAYLOAD)
    assert resp.status_code == 201
    assert resp.json()["status"] == "failed"
    assert len(client.get("/api/tickets", params={"status": "failed"}).json()) == 1


def test_validation(client):
    resp = client.post("/api/tickets", json={**PAYLOAD, "customer_email": "nope"})
    assert resp.status_code == 422


def test_not_found(client):
    assert client.get("/api/tickets/999").status_code == 404
