from app.schemas.ticket import Analysis
from app.services import operator as operator_service
from app.services import tickets as tickets_service
from app.services.graph import Escalation, GraphRunResult

PAYLOAD = {
    "customer_name": "Ivan",
    "customer_email": "ivan@example.com",
    "message": "My order vanished and nobody replies!",
}


def _escalation_run() -> GraphRunResult:
    return GraphRunResult(
        thread_id="ticket-test",
        analysis=None,
        escalation=Escalation(
            question="Какой заказ имеется в виду?",
            category="payment",
            priority="high",
        ),
    )


def _ok_run() -> GraphRunResult:
    return GraphRunResult(
        thread_id="ticket-test",
        analysis=Analysis(
            category="payment", priority="high", summary="s", reply_draft="r"
        ),
        escalation=None,
    )


def test_sender_tracks_escalated_ticket_until_final_answer(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _escalation_run())
    created = client.post("/api/tickets", json=PAYLOAD).json()
    token = created["access_token"]
    assert created["status"] == "pending_operator"
    assert token

    resp = client.get(f"/api/tickets/{created['id']}/status", params={"token": token})
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_operator"

    monkeypatch.setattr(
        operator_service,
        "resume_support_graph",
        lambda thread_id, answer: Analysis(
            category="payment",
            priority="high",
            summary="Заказ пропал",
            reply_draft="Финальный ответ оператора через LangGraph",
        ),
    )
    request_id = client.get("/api/operator/requests").json()[0]["id"]
    assert client.post(
        f"/api/operator/requests/{request_id}/answer", json={"answer": "Заказ №123"}
    ).status_code == 200

    resp = client.get(f"/api/tickets/{created['id']}/status", params={"token": token})
    body = resp.json()
    assert resp.status_code == 200
    assert body["status"] == "processed"
    assert body["reply_draft"] == "Финальный ответ оператора через LangGraph"


def test_wrong_token_forbidden(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _escalation_run())
    created = client.post("/api/tickets", json=PAYLOAD).json()

    resp = client.get(
        f"/api/tickets/{created['id']}/status", params={"token": "0" * 32}
    )
    assert resp.status_code == 403


def test_non_escalated_ticket_not_trackable(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _ok_run())
    created = client.post("/api/tickets", json=PAYLOAD).json()
    assert created["status"] == "processed"
    assert created["access_token"] is None

    resp = client.get(
        f"/api/tickets/{created['id']}/status", params={"token": "anything"}
    )
    assert resp.status_code == 404


def test_status_unknown_ticket_not_found(client):
    resp = client.get("/api/tickets/999/status", params={"token": "x"})
    assert resp.status_code == 404


def test_status_requires_token(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _escalation_run())
    created = client.post("/api/tickets", json=PAYLOAD).json()
    assert (
        client.get(f"/api/tickets/{created['id']}/status").status_code == 422
    )


def test_token_is_stable_across_reanalyze(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _escalation_run())
    created = client.post("/api/tickets", json=PAYLOAD).json()
    first_token = created["access_token"]

    body = client.post(f"/api/tickets/{created['id']}/reanalyze").json()
    assert body["status"] == "pending_operator"

    ticket = client.get(f"/api/tickets/{created['id']}").json()
    assert ticket["status"] == "pending_operator"
    assert (
        client.get(
            f"/api/tickets/{created['id']}/status", params={"token": first_token}
        ).status_code
        == 200
    )
