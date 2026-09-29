from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ticket import Ticket
from app.schemas.ticket import Category, Priority, TicketCreate, TicketOut
from app.services.llm import LLMError, analyze_ticket

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _run_analysis(ticket: Ticket, db: Session) -> None:
    try:
        result = analyze_ticket(ticket.customer_name, ticket.message)
    except LLMError as exc:
        ticket.status = "failed"
        ticket.error = str(exc)
    else:
        ticket.category = result.category
        ticket.priority = result.priority
        ticket.summary = result.summary
        ticket.reply_draft = result.reply_draft
        ticket.status = "processed"
        ticket.error = None
    db.commit()
    db.refresh(ticket)


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(body: TicketCreate, db: Session = Depends(get_db)):
    ticket = Ticket(**body.model_dump())
    db.add(ticket)
    db.commit()
    _run_analysis(ticket, db)
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(
    category: Category | None = None,
    priority: Priority | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Ticket).order_by(Ticket.id.desc()).limit(limit).offset(offset)
    if category:
        stmt = stmt.where(Ticket.category == category)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)
    if status:
        stmt = stmt.where(Ticket.status == status)
    return db.scalars(stmt).all()


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.post("/{ticket_id}/reanalyze", response_model=TicketOut)
def reanalyze_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    _run_analysis(ticket, db)
    return ticket
