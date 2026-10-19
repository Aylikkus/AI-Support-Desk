from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.db.session import get_db
from app.schemas.ticket import Category, Priority, TicketCreate, TicketCreated, TicketOut, TicketStatus
from app.services import tickets as tickets_service

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.post("", response_model=TicketCreated, status_code=201)
async def create_ticket(body: TicketCreate, db: Session = Depends(get_db)) -> TicketCreated:
    return await run_in_threadpool(tickets_service.create_ticket, db, body)


@router.get("", response_model=list[TicketOut])
async def list_tickets(
    category: Category | None = None,
    priority: Priority | None = None,
    status: TicketStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[TicketOut]:
    return await run_in_threadpool(
        tickets_service.list_tickets, db, category, priority, status, limit, offset
    )


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> TicketOut:
    ticket = await run_in_threadpool(tickets_service.get_ticket, db, ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.post("/{ticket_id}/reanalyze", response_model=TicketOut)
async def reanalyze_ticket(ticket_id: int, db: Session = Depends(get_db)) -> TicketOut:
    ticket = await run_in_threadpool(tickets_service.get_ticket, db, ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    return await run_in_threadpool(tickets_service.reanalyze_ticket, db, ticket)


@router.get("/{ticket_id}/status", response_model=TicketOut)
async def get_ticket_status(
    ticket_id: int,
    token: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> TicketOut:
    """Status of an escalated ticket for its sender only (secret token from the create response)."""
    try:
        ticket = await run_in_threadpool(tickets_service.get_ticket_status, db, ticket_id, token)
    except tickets_service.InvalidStatusTokenError as exc:
        raise HTTPException(403, "Invalid access token") from exc
    if ticket is None:
        raise HTTPException(404, "Ticket not found or not trackable")
    return ticket
