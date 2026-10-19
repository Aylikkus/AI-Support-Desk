"""Operator queue business logic."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.operator_request import OperatorRequest
from app.models.ticket import Ticket
from app.schemas.operator import OperatorAnswer, OperatorRequestDetail, OperatorRequestStatus, OperatorRequestOut
from app.schemas.ticket import TicketOut, TicketStatus
from app.services.graph import resume_support_graph


class OperatorRequestError(Exception):
    """Base class for operator queue errors."""


class RequestNotPendingError(OperatorRequestError):
    pass


class GraphResumeError(OperatorRequestError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def list_requests(
    db: Session,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[OperatorRequest]:
    stmt = select(OperatorRequest).order_by(OperatorRequest.id.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(OperatorRequest.status == status)
    return db.scalars(stmt).all()


def get_request(db: Session, request_id: int) -> OperatorRequest | None:
    return db.get(OperatorRequest, request_id)


def get_request_detail(db: Session, request_id: int) -> OperatorRequestDetail | None:
    request = get_request(db, request_id)
    if request is None:
        return None
    return _to_detail(db, request)


def answer_request(db: Session, request_id: int, body: OperatorAnswer) -> OperatorRequestDetail | None:
    """Store the operator's answer, resume the paused graph and finish the ticket.

    Returns None when the request does not exist; raises RequestNotPendingError
    when the request was already answered/cancelled. On a graph/LLM failure the
    LangGraph thread stays paused, the ticket is marked failed and the request
    stays pending, so the operator can simply try again (GraphResumeError).
    """
    request = get_request(db, request_id)
    if request is None:
        return None
    if request.status != OperatorRequestStatus.pending.value:
        raise RequestNotPendingError(f"запрос уже обработан (status={request.status})")

    ticket = db.get(Ticket, request.ticket_id)
    try:
        analysis = resume_support_graph(request.thread_id, body.answer)
    except Exception as exc:
        ticket.status = TicketStatus.failed.value
        ticket.error = f"{type(exc).__name__}: {exc}"
        db.commit()
        raise GraphResumeError(f"{type(exc).__name__}: {exc}") from exc

    ticket.status = TicketStatus.processed.value
    ticket.category = analysis.category
    ticket.priority = analysis.priority
    ticket.summary = analysis.summary
    ticket.reply_draft = analysis.reply_draft
    ticket.error = None
    request.answer = body.answer
    request.status = OperatorRequestStatus.answered.value
    request.answered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    db.refresh(request)
    return _to_detail(db, request)


def _to_detail(db: Session, request: OperatorRequest) -> OperatorRequestDetail:
    ticket = db.get(Ticket, request.ticket_id)
    base = OperatorRequestOut.model_validate(request).model_dump()
    return OperatorRequestDetail(**base, ticket=TicketOut.model_validate(ticket))
