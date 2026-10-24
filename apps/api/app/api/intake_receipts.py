from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.identity import Principal
from app.db import get_db
from app.schemas.ingestion import AIProviderName
from app.schemas.intake_receipts import ReceiptCreate, ReceiptRead
from app.services.documents import get_object_storage
from app.services.intake_receipts import (
    deliver_document_item,
    deliver_url_receipt,
    find_receipt_by_occurrence,
    get_receipt_delivery,
    serialize_receipt,
)
from app.services.object_storage import ObjectStorage

router = APIRouter(prefix="/intake/receipts", tags=["intake-receipts"])


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise RuntimeError("Authenticated principal is unavailable")
    return principal


@router.post("", response_model=ReceiptRead, status_code=202)
def create_receipt(
    data: ReceiptCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> ReceiptRead:
    principal = _principal(request)
    delivery = deliver_url_receipt(db, data, principal)
    result = serialize_receipt(db, delivery, principal)
    if "queued" not in delivery.dispositions.values():
        response.status_code = 200
    return result


@router.post("/{receipt_id}/documents", response_model=ReceiptRead, status_code=202)
async def create_document_item(
    receipt_id: str,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    external_item_ref: str = Form(..., min_length=1, max_length=500),
    provider: AIProviderName | None = Form(default=None),
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> ReceiptRead:
    principal = _principal(request)
    delivery = await deliver_document_item(
        db,
        receipt_id,
        file,
        external_item_ref,
        storage,
        provider_name=provider,
        principal=principal,
    )
    result = serialize_receipt(db, delivery, principal)
    if "queued" not in delivery.dispositions.values():
        response.status_code = 200
    return result


@router.get("", response_model=ReceiptRead)
def receipt_by_occurrence(
    occurrence_ref: str,
    request: Request,
    db: Session = Depends(get_db),
) -> ReceiptRead:
    """Find a receipt by the calling system's own reference, within its own namespace."""

    principal = _principal(request)
    return serialize_receipt(
        db, find_receipt_by_occurrence(db, occurrence_ref, principal), principal
    )


@router.get("/{receipt_id}", response_model=ReceiptRead)
def receipt(
    receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> ReceiptRead:
    principal = _principal(request)
    return serialize_receipt(db, get_receipt_delivery(db, receipt_id, principal), principal)
