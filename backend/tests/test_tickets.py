from app.schemas.ticket import Analysis
from app.services import tickets as tickets_service
from app.services.graph import Escalation, GraphRunResult, SupportGraphError

PAYLOAD = {
    "customer_name": "Ivan",
    "customer_email": "ivan@example.com",
    "message": "Charged but no order!",
}


def _ok_run() -> GraphRunResult:
    return GraphRunResult(
        thread_id="ticket-test",
        analysis=Analysis(
            category="payment", priority="high", summary="Charged w/o order", reply_draft="Hi!"
        ),
        escalation=None,
    )


def test_create_ticket_processed(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _ok_run())
    resp = client.post("/api/tickets", json=PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "processed"
    assert body["category"] == "payment"
    assert body["priority"] == "high"
    assert client.get(f"/api/tickets/{body['id']}").json()["reply_draft"] == "Hi!"


def test_graph_failure_keeps_ticket(client, monkeypatch):
    def boom(name, msg):
        raise SupportGraphError("down")

    monkeypatch.setattr(tickets_service, "run_support_graph", boom)
    resp = client.post("/api/tickets", json=PAYLOAD)
    assert resp.status_code == 201
    assert resp.json()["status"] == "failed"
    assert len(client.get("/api/tickets", params={"status": "failed"}).json()) == 1


def test_create_ticket_escalates(client, monkeypatch):
    run = GraphRunResult(
        thread_id="ticket-test",
        analysis=None,
        escalation=Escalation(question="Уточните номер заказа", category="payment", priority="high"),
    )
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: run)

    body = client.post("/api/tickets", json=PAYLOAD).json()
    assert body["status"] == "pending_operator"
    assert body["category"] == "payment"
    assert body["reply_draft"] is None


def test_reanalyze_cancels_pending_request(client, monkeypatch):
    run = GraphRunResult(
        thread_id="ticket-test",
        analysis=None,
        escalation=Escalation(question="Уточните номер заказа", category="payment", priority="high"),
    )
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: run)
    ticket = client.post("/api/tickets", json=PAYLOAD).json()
    request_id = client.get("/api/operator/requests").json()[0]["id"]

    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _ok_run())
    body = client.post(f"/api/tickets/{ticket['id']}/reanalyze").json()
    assert body["status"] == "processed"

    queue = client.get("/api/operator/requests").json()
    assert queue[0]["status"] == "cancelled"
    assert client.get("/api/operator/requests", params={"status": "pending"}).json() == []
    assert client.post(f"/api/operator/requests/{request_id}/answer", json={"answer": "x"}).status_code == 409


def test_validation(client):
    resp = client.post("/api/tickets", json={**PAYLOAD, "customer_email": "nope"})
    assert resp.status_code == 422


def test_not_found(client):
    assert client.get("/api/tickets/999").status_code == 404
