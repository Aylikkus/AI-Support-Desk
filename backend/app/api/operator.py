from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.db.session import get_db
from app.schemas.operator import (
    OperatorAnswer,
    OperatorRequestDetail,
    OperatorRequestOut,
    OperatorRequestStatus,
)
from app.services import operator as operator_service

router = APIRouter(prefix="/api/operator", tags=["operator"])


@router.get("/requests", response_model=list[OperatorRequestOut])
async def list_requests(
    status: OperatorRequestStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[OperatorRequestOut]:
    return await run_in_threadpool(
        operator_service.list_requests, db, status, limit, offset
    )


@router.get("/requests/{request_id}", response_model=OperatorRequestDetail)
async def get_request(request_id: int, db: Session = Depends(get_db)) -> OperatorRequestDetail:
    detail = await run_in_threadpool(operator_service.get_request_detail, db, request_id)
    if detail is None:
        raise HTTPException(404, "Operator request not found")
    return detail


@router.post("/requests/{request_id}/answer", response_model=OperatorRequestDetail)
async def answer_request(
    request_id: int,
    body: OperatorAnswer,
    db: Session = Depends(get_db),
) -> OperatorRequestDetail:
    try:
        detail = await run_in_threadpool(
            operator_service.answer_request, db, request_id, body
        )
    except operator_service.RequestNotPendingError as exc:
        raise HTTPException(409, str(exc)) from exc
    except operator_service.GraphResumeError as exc:
        raise HTTPException(502, f"Не удалось завершить обработку: {exc.message}") from exc
    if detail is None:
        raise HTTPException(404, "Operator request not found")
    return detail
