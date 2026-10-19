"""Ticket business logic; routers stay thin and never touch the DB themselves."""

import secrets

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.operator_request import OperatorRequest
from app.models.ticket import Ticket
from app.schemas.operator import OperatorRequestStatus
from app.schemas.ticket import Category, Priority, TicketCreate, TicketStatus
from app.services.graph import GraphRunResult, run_support_graph


def create_ticket(db: Session, body: TicketCreate) -> Ticket:
    ticket = Ticket(**body.model_dump())
    db.add(ticket)
    db.commit()
    _run_graph_and_update(db, ticket)
    return ticket


def reanalyze_ticket(db: Session, ticket: Ticket) -> Ticket:
    _cancel_pending_requests(db, ticket.id)
    _run_graph_and_update(db, ticket)
    return ticket


def list_tickets(
    db: Session,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Ticket]:
    stmt = select(Ticket).order_by(Ticket.id.desc()).limit(limit).offset(offset)
    if category:
        stmt = stmt.where(Ticket.category == category)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)
    if status:
        stmt = stmt.where(Ticket.status == status)
    return db.scalars(stmt).all()


def get_ticket(db: Session, ticket_id: int) -> Ticket | None:
    return db.get(Ticket, ticket_id)


class InvalidStatusTokenError(Exception):
    """Raised when the provided access token does not match the ticket."""


def get_ticket_status(db: Session, ticket_id: int, token: str) -> Ticket | None:
    """Ticket status for the sender only.

    Only escalated tickets get an access token, so status tracking exists solely
    for tickets redirected to an operator. Returns None for unknown or
    non-escalated tickets; raises InvalidStatusTokenError on a wrong token.
    """
    ticket = get_ticket(db, ticket_id)
    if ticket is None or ticket.access_token is None:
        return None
    if not secrets.compare_digest(ticket.access_token, token):
        raise InvalidStatusTokenError("invalid access token")
    return ticket


def _run_graph_and_update(db: Session, ticket: Ticket) -> None:
    try:
        run = run_support_graph(ticket.customer_name, ticket.message)
    except Exception as exc:  # graph/LLM/provider failures keep the ticket with the error text
        ticket.status = TicketStatus.failed.value
        ticket.error = f"{type(exc).__name__}: {exc}"
    else:
        ticket.error = None
        if run.escalation is not None:
            ticket.status = TicketStatus.pending_operator.value
            ticket.category = _safe_enum(run.escalation.category, Category)
            ticket.priority = _safe_enum(run.escalation.priority, Priority)
            if ticket.access_token is None:
                # Secret capability token for the sender's status link; issued once per ticket.
                ticket.access_token = secrets.token_hex(16)
            db.add(
                OperatorRequest(
                    ticket_id=ticket.id,
                    thread_id=run.thread_id,
                    question=run.escalation.question,
                    status=OperatorRequestStatus.pending.value,
                )
            )
        elif run.analysis is not None:
            ticket.status = TicketStatus.processed.value
            ticket.category = run.analysis.category
            ticket.priority = run.analysis.priority
            ticket.summary = run.analysis.summary
            ticket.reply_draft = run.analysis.reply_draft
    db.commit()
    db.refresh(ticket)


def _safe_enum(value: str | None, enum_cls: type) -> str | None:
    if value is None:
        return None
    try:
        return enum_cls(value).value
    except ValueError:
        return None


def _cancel_pending_requests(db: Session, ticket_id: int) -> None:
    db.execute(
        update(OperatorRequest)
        .where(
            OperatorRequest.ticket_id == ticket_id,
            OperatorRequest.status == OperatorRequestStatus.pending.value,
        )
        .values(status=OperatorRequestStatus.cancelled.value)
    )
    db.commit()
