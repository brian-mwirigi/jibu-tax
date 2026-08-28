"""
Ledger enqueue API.

POST returns immediately after placing a Celery job so the ElevenLabs webhook
does not wait on PostgreSQL.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_db
from app.models.ledger import LedgerEntry
from app.schemas.filing import LedgerEnqueueRequest, LedgerEnqueueResponse, LedgerEntryResponse
from app.workers.ledger_tasks import enqueue_ledger_write

router = APIRouter()


@router.post("/enqueue", response_model=LedgerEnqueueResponse, status_code=202)
def enqueue_ledger_entry(body: LedgerEnqueueRequest) -> LedgerEnqueueResponse:
    task_id = enqueue_ledger_write(body.model_dump(mode="json"))
    return LedgerEnqueueResponse(
        accepted=True,
        celery_task_id=task_id,
        invoice_number=body.invoice_number,
        message="Ledger write queued; the voice call is not blocked on Postgres.",
    )


@router.get("", response_model=List[LedgerEntryResponse])
def list_ledger_entries(db: Session = Depends(get_db)) -> list[LedgerEntry]:
    return list(db.exec(select(LedgerEntry).order_by(LedgerEntry.sequence.desc())).all())
