"""REST routes for previewing, filing, listing, and verifying eTIMS invoices."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.etims import (
    CreateInvoiceRequest,
    InvoiceListItem,
    InvoiceResponse,
    VerifyInvoiceResponse,
)
from app.schemas.tax import TaxBreakdown
from app.services.oscu_engine import (
    apply_whatsapp_dispatch,
    get_invoice,
    issue_invoice,
    list_invoices,
    qr_png_bytes,
    to_response,
    verify_control_code,
)
from app.services.tax_engine import TaxValidationError, calculate_invoice

router = APIRouter()


def _http_tax_error(exc: TaxValidationError) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"ok": False, "code": exc.code, "message": exc.message},
    )


@router.post("/preview", response_model=TaxBreakdown)
def preview_invoice(payload: CreateInvoiceRequest):
    from app.api.v1.stats import record_telemetry_event
    try:
        res = calculate_invoice(payload.items, claimed_grand_total=payload.claimed_grand_total)
        record_telemetry_event("TAX_ENGINE", f"VAT Preview: Total KES {res.grand_total:,.2f} | VAT KES {res.total_vat_amount:,.2f}", "success")
        return res
    except TaxValidationError as exc:
        record_telemetry_event("TAX_ENGINE", f"Tax validation error: {exc.message}", "error")
        raise _http_tax_error(exc) from exc


@router.post("", response_model=InvoiceResponse)
def create_invoice(payload: CreateInvoiceRequest, db: Session = Depends(get_db)):
    from app.api.v1.stats import record_telemetry_event
    try:
        inv = issue_invoice(db, payload)
        record_telemetry_event("OSCU_SIGNER", f"eTIMS Invoice #{inv.invoice_number} signed with Control Code {inv.oscu_control_code}", "success")
        record_telemetry_event("DISPATCH", f"WhatsApp QR Code sent to {inv.whatsapp_destination or '+254712345678'}", "success")
        return inv
    except TaxValidationError as exc:
        record_telemetry_event("OSCU_SIGNER", f"Invoice creation failed: {exc.message}", "error")
        raise _http_tax_error(exc) from exc


@router.get("", response_model=list[InvoiceListItem])
def get_invoices(db: Session = Depends(get_db)):
    invoices = list_invoices(db)
    return [
        InvoiceListItem(
            invoice_number=row.invoice_number,
            buyer_name=row.buyer_name,
            grand_total=row.grand_total,
            oscu_control_code=row.oscu_control_code,
            sms_status=row.sms_status,
            whatsapp_status=row.whatsapp_status,
            issued_at=row.issued_at,
        )
        for row in invoices
    ]


@router.get("/verify/{control_code}", response_model=VerifyInvoiceResponse)
def verify_invoice(control_code: str, db: Session = Depends(get_db)):
    invoice, valid, message = verify_control_code(db, control_code)
    return VerifyInvoiceResponse(
        valid=valid,
        message=message,
        invoice=to_response(invoice, valid=valid) if invoice else None,
    )


@router.get("/{invoice_number}/qr.png")
def get_invoice_qr(invoice_number: str, db: Session = Depends(get_db)):
    invoice = get_invoice(db, invoice_number)
    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail={"ok": False, "code": "NOT_FOUND", "message": "Invoice not found."},
        )
    return Response(
        content=qr_png_bytes(invoice),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/{invoice_number}/whatsapp", response_model=InvoiceResponse)
def resend_whatsapp(invoice_number: str, db: Session = Depends(get_db)):
    invoice = get_invoice(db, invoice_number)
    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail={"ok": False, "code": "NOT_FOUND", "message": "Invoice not found."},
        )
    apply_whatsapp_dispatch(invoice)
    db.commit()
    db.refresh(invoice)
    return to_response(invoice)


@router.get("/{invoice_number}", response_model=InvoiceResponse)
def get_invoice_by_number(invoice_number: str, db: Session = Depends(get_db)):
    invoice = get_invoice(db, invoice_number)
    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail={"ok": False, "code": "NOT_FOUND", "message": "Invoice not found."},
        )
    return to_response(invoice)
