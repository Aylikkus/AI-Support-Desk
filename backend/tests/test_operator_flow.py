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


def test_escalation_creates_queue_item(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _escalation_run())

    resp = client.post("/api/tickets", json=PAYLOAD)
    body = resp.json()
    assert resp.status_code == 201
    assert body["status"] == "pending_operator"
    assert body["category"] == "payment"
    assert body["priority"] == "high"

    queue = client.get("/api/operator/requests", params={"status": "pending"}).json()
    assert len(queue) == 1
    assert queue[0]["question"] == "Какой заказ имеется в виду?"
    assert queue[0]["ticket_id"] == body["id"]

    detail = client.get(f"/api/operator/requests/{queue[0]['id']}").json()
    assert detail["ticket"]["message"] == PAYLOAD["message"]


def test_answer_resumes_graph_and_finishes_ticket(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _escalation_run())
    body = client.post("/api/tickets", json=PAYLOAD).json()
    request_id = client.get("/api/operator/requests").json()[0]["id"]

    monkeypatch.setattr(
        operator_service,
        "resume_support_graph",
        lambda thread_id, answer: Analysis(
            category="payment",
            priority="high",
            summary="Заказ пропал",
            reply_draft=f"Здравствуйте! По вашему вопросу ({answer}).",
        ),
    )

    resp = client.post(f"/api/operator/requests/{request_id}/answer", json={"answer": "Заказ №123"})
    detail = resp.json()
    assert resp.status_code == 200
    assert detail["status"] == "answered"
    assert detail["answer"] == "Заказ №123"
    assert detail["answered_at"] is not None
    assert detail["ticket"]["status"] == "processed"
    assert "Заказ №123" in detail["ticket"]["reply_draft"]

    ticket = client.get(f"/api/tickets/{body['id']}").json()
    assert ticket["status"] == "processed"
    assert ticket["summary"] == "Заказ пропал"

    assert client.get("/api/operator/requests", params={"status": "pending"}).json() == []


def test_answer_twice_conflicts(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _escalation_run())
    client.post("/api/tickets", json=PAYLOAD)
    request_id = client.get("/api/operator/requests").json()[0]["id"]

    monkeypatch.setattr(
        operator_service,
        "resume_support_graph",
        lambda thread_id, answer: Analysis(
            category="payment", priority="high", summary="s", reply_draft="r"
        ),
    )
    assert client.post(f"/api/operator/requests/{request_id}/answer", json={"answer": "ок"}).status_code == 200
    assert client.post(f"/api/operator/requests/{request_id}/answer", json={"answer": "ещё"}).status_code == 409


def test_resume_failure_keeps_request_pending(client, monkeypatch):
    monkeypatch.setattr(tickets_service, "run_support_graph", lambda name, msg: _escalation_run())
    ticket = client.post("/api/tickets", json=PAYLOAD).json()
    request_id = client.get("/api/operator/requests").json()[0]["id"]

    def boom(thread_id, answer):
        raise RuntimeError("llm down")

    monkeypatch.setattr(operator_service, "resume_support_graph", boom)
    resp = client.post(f"/api/operator/requests/{request_id}/answer", json={"answer": "Заказ №123"})
    assert resp.status_code == 502

    still_pending = client.get("/api/operator/requests", params={"status": "pending"}).json()
    assert len(still_pending) == 1
    assert client.get(f"/api/tickets/{ticket['id']}").json()["status"] == "failed"


def test_operator_request_not_found(client):
    assert client.get("/api/operator/requests/999").status_code == 404
    assert client.post("/api/operator/requests/999/answer", json={"answer": "ок"}).status_code == 404
