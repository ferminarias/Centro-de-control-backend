import io
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.lead import Lead
from app.models.lead_base import LeadBase
from app.models.lote import Lote
from app.schemas.lead import BulkUpdateResponse, LeadListResponse, LeadResponse

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_admin_key)])


def _lead_to_dict(lead: Lead, base_nombre: str | None = None, lote_nombre: str | None = None) -> dict:
    return {
        "id": lead.id,
        "id_lead": lead.id_lead,
        "cuenta_id": lead.cuenta_id,
        "record_id": lead.record_id,
        "lead_base_id": lead.lead_base_id,
        "base_nombre": base_nombre,
        "lote_id": lead.lote_id,
        "lote_nombre": lote_nombre,
        "datos": lead.datos,
        "created_at": lead.created_at,
    }


@router.get(
    "/accounts/{account_id}/leads",
    response_model=LeadListResponse,
    summary="List leads for an account",
)
def list_leads(
    account_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    query = db.query(Lead).filter(Lead.cuenta_id == account_id)
    total = query.count()
    leads = (
        query.order_by(Lead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Fetch base names
    base_ids = {l.lead_base_id for l in leads if l.lead_base_id}
    base_names: dict[uuid.UUID, str] = {}
    if base_ids:
        bases = db.query(LeadBase.id, LeadBase.nombre).filter(LeadBase.id.in_(base_ids)).all()
        base_names = {b.id: b.nombre for b in bases}

    # Fetch lote names
    lote_ids = {l.lote_id for l in leads if l.lote_id}
    lote_names: dict[uuid.UUID, str] = {}
    if lote_ids:
        lotes = db.query(Lote.id, Lote.nombre).filter(Lote.id.in_(lote_ids)).all()
        lote_names = {lo.id: lo.nombre for lo in lotes}

    items = [
        _lead_to_dict(
            lead,
            base_names.get(lead.lead_base_id) if lead.lead_base_id else None,
            lote_names.get(lead.lote_id) if lead.lote_id else None,
        )
        for lead in leads
    ]

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/leads/{lead_id}",
    response_model=LeadResponse,
    summary="Get lead details",
)
def get_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    base_nombre = None
    if lead.lead_base_id:
        base = db.query(LeadBase.nombre).filter(LeadBase.id == lead.lead_base_id).first()
        if base:
            base_nombre = base.nombre

    lote_nombre = None
    if lead.lote_id:
        lote = db.query(Lote.nombre).filter(Lote.id == lead.lote_id).first()
        if lote:
            lote_nombre = lote.nombre

    return _lead_to_dict(lead, base_nombre, lote_nombre)


# ---------------------------------------------------------------------------
# Bulk update template download
# ---------------------------------------------------------------------------
@router.get(
    "/accounts/{account_id}/leads/update-template",
    summary="Download Excel template for bulk lead update",
)
def download_update_template(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    from app.models.field import CustomField

    fields = (
        db.query(CustomField.nombre_campo)
        .filter(CustomField.cuenta_id == account_id)
        .order_by(CustomField.created_at)
        .all()
    )
    field_names = [f[0] for f in fields]

    wb = Workbook()
    ws = wb.active
    ws.title = "Actualizar Leads"
    ws.append(["id_lead"] + field_names)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"actualizar_leads_{account.nombre}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Bulk update via Excel
# ---------------------------------------------------------------------------
@router.post(
    "/accounts/{account_id}/leads/bulk-update",
    response_model=BulkUpdateResponse,
    summary="Bulk update leads from Excel file",
)
def bulk_update_leads(
    account_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        content = file.file.read()
        wb = load_workbook(filename=io.BytesIO(content), read_only=True)
        ws = wb.active
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Excel file")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="Excel must have a header row and at least one data row")

    header = [str(c).strip() if c is not None else "" for c in rows[0]]

    # First column MUST be id_lead
    if not header or header[0].lower() != "id_lead":
        raise HTTPException(
            status_code=400,
            detail="First column must be 'id_lead'",
        )

    update_columns = header[1:]
    if not update_columns:
        raise HTTPException(status_code=400, detail="No data columns to update (only id_lead found)")

    updated = 0
    not_found_ids: list[int] = []
    errors: list[str] = []

    for row_idx, row in enumerate(rows[1:], start=2):
        raw_id = row[0] if row else None
        if raw_id is None or str(raw_id).strip() == "":
            continue

        try:
            lead_id_val = int(raw_id)
        except (ValueError, TypeError):
            errors.append(f"Row {row_idx}: invalid id_lead '{raw_id}'")
            continue

        lead = db.query(Lead).filter(
            Lead.cuenta_id == account_id,
            Lead.id_lead == lead_id_val,
        ).first()

        if not lead:
            not_found_ids.append(lead_id_val)
            continue

        # Build update dict from non-empty cells
        new_datos = dict(lead.datos)
        changed = False
        for col_idx, col_name in enumerate(update_columns):
            if not col_name:
                continue
            cell_val = row[col_idx + 1] if col_idx + 1 < len(row) else None
            if cell_val is not None and str(cell_val).strip() != "":
                new_datos[col_name] = cell_val
                changed = True

        if changed:
            lead.datos = new_datos
            # Also update the record
            if lead.record:
                lead.record.datos = new_datos
            updated += 1

    db.commit()

    logger.info(
        "Bulk update for account %s: %d updated, %d not found",
        account_id, updated, len(not_found_ids),
    )

    return {
        "updated": updated,
        "not_found_ids": not_found_ids,
        "errors": errors,
    }
