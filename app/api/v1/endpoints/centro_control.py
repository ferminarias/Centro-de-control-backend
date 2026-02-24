import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.lead import Lead
from app.models.tipificacion_externa import TipificacionExterna
from app.schemas.tipificacion_externa import (
    RetryMatchResponse,
    TipificacionExternaIngestResponse,
    TipificacionExternaListResponse,
    TipificacionExternaPayload,
    TipificacionExternaResponse,
)

logger = logging.getLogger(__name__)

# --- Router público (webhook ingest, auth por api_key en URL) ---
public_router = APIRouter()

# --- Router admin (requiere admin key) ---
admin_router = APIRouter()


# ──────────────────────────────────────────────
# WEBHOOK PÚBLICO — POST /ingest/{api_key}/tipificacion-externa
# ──────────────────────────────────────────────
@public_router.post(
    "/ingest/{account_api_key}/tipificacion-externa",
    response_model=TipificacionExternaIngestResponse,
    summary="Recibir tipificación externa (Neotel)",
    description="Webhook público para recibir tipificaciones externas. Auth por api_key en URL.",
)
def ingest_tipificacion_externa(
    account_api_key: str,
    payload: TipificacionExternaPayload,
    db: Session = Depends(get_db),
) -> TipificacionExternaIngestResponse:
    # 1. Validar cuenta por api_key
    account = (
        db.query(Account)
        .filter(Account.api_key == account_api_key, Account.activo.is_(True))
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or inactive",
        )

    logger.info(
        "Tipificación externa recibida para cuenta '%s' (%s) — email=%s",
        account.nombre, account.id, payload.EMLMAIL,
    )

    # 2. Buscar lead por email en datos JSONB
    lead = (
        db.query(Lead)
        .filter(
            Lead.cuenta_id == account.id,
            Lead.datos["email"].astext == payload.EMLMAIL,
        )
        .first()
    )

    # 3. Crear TipificacionExterna
    tipificacion = TipificacionExterna(
        cuenta_id=account.id,
        lead_id=lead.id if lead else None,
        email=payload.EMLMAIL,
        id_neotel=payload.USUARIO,
        id_subresolucion=payload.IdSubresolucion,
        raw_payload=payload.model_dump(),
        matched=lead is not None,
    )
    db.add(tipificacion)

    # 4. Si hay lead, actualizar ultima_tipificacion
    if lead:
        lead.ultima_tipificacion = {
            "id_neotel": payload.USUARIO,
            "id_subresolucion": payload.IdSubresolucion,
            "email": payload.EMLMAIL,
            "fecha": datetime.now(timezone.utc).isoformat(),
            "tipificacion_externa_id": str(tipificacion.id),
        }
        logger.info("Lead %s matcheado con tipificación externa", lead.id)
    else:
        logger.info("No se encontró lead con email %s — guardada como pendiente", payload.EMLMAIL)

    db.commit()
    db.refresh(tipificacion)

    return TipificacionExternaIngestResponse(
        success=True,
        tipificacion_id=tipificacion.id,
        matched=tipificacion.matched,
        lead_id=tipificacion.lead_id,
    )


# ──────────────────────────────────────────────
# SSE FEED — GET /accounts/{cuenta_id}/centro-control/feed
# ──────────────────────────────────────────────
@admin_router.get(
    "/accounts/{cuenta_id}/centro-control/feed",
    summary="SSE feed de tipificaciones externas en tiempo real",
    description="Server-Sent Events stream. Envía las últimas 50 al conectar y luego nuevas cada 2s.",
)
def centro_control_feed(
    cuenta_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: str | None = Depends(verify_admin_key),
):
    # Verificar que la cuenta existe
    account = db.query(Account).filter(Account.id == cuenta_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    def event_generator():
        import time

        from app.core.database import SessionLocal

        session = SessionLocal()
        try:
            # Batch inicial: últimas 50 tipificaciones
            initial = (
                session.query(TipificacionExterna)
                .filter(TipificacionExterna.cuenta_id == cuenta_id)
                .order_by(TipificacionExterna.created_at.desc())
                .limit(50)
                .all()
            )
            initial_data = [
                TipificacionExternaResponse.model_validate(t).model_dump(mode="json")
                for t in reversed(initial)
            ]
            yield f"event: init\ndata: {json.dumps(initial_data)}\n\n"

            # Determinar el timestamp más reciente
            if initial:
                last_ts = max(t.created_at for t in initial)
            else:
                last_ts = datetime.now(timezone.utc)

            # Loop de polling cada 2 segundos
            while True:
                time.sleep(2)
                try:
                    nuevas = (
                        session.query(TipificacionExterna)
                        .filter(
                            TipificacionExterna.cuenta_id == cuenta_id,
                            TipificacionExterna.created_at > last_ts,
                        )
                        .order_by(TipificacionExterna.created_at.asc())
                        .all()
                    )

                    for tip in nuevas:
                        data = TipificacionExternaResponse.model_validate(tip).model_dump(mode="json")
                        yield f"event: nueva_tipificacion\ndata: {json.dumps(data)}\n\n"
                        last_ts = tip.created_at

                    # Heartbeat para mantener la conexión viva
                    if not nuevas:
                        yield ": heartbeat\n\n"

                except Exception:
                    session.rollback()
                    yield ": heartbeat\n\n"

        except GeneratorExit:
            pass
        finally:
            session.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────────────────────────────────
# LISTA PAGINADA — GET /accounts/{cuenta_id}/centro-control
# ──────────────────────────────────────────────
@admin_router.get(
    "/accounts/{cuenta_id}/centro-control",
    response_model=TipificacionExternaListResponse,
    summary="Lista paginada de tipificaciones externas",
)
def listar_tipificaciones_externas(
    cuenta_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    matched: bool | None = Query(None, description="Filtrar por matched (true/false)"),
    db: Session = Depends(get_db),
    _admin: str | None = Depends(verify_admin_key),
) -> TipificacionExternaListResponse:
    account = db.query(Account).filter(Account.id == cuenta_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    query = db.query(TipificacionExterna).filter(TipificacionExterna.cuenta_id == cuenta_id)

    if matched is not None:
        query = query.filter(TipificacionExterna.matched == matched)

    total = query.count()
    items = (
        query
        .order_by(TipificacionExterna.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TipificacionExternaListResponse(
        items=[TipificacionExternaResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────
# PENDIENTES — GET /accounts/{cuenta_id}/centro-control/pendientes
# ──────────────────────────────────────────────
@admin_router.get(
    "/accounts/{cuenta_id}/centro-control/pendientes",
    response_model=TipificacionExternaListResponse,
    summary="Tipificaciones externas sin match (pendientes)",
)
def listar_pendientes(
    cuenta_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: str | None = Depends(verify_admin_key),
) -> TipificacionExternaListResponse:
    account = db.query(Account).filter(Account.id == cuenta_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    query = (
        db.query(TipificacionExterna)
        .filter(
            TipificacionExterna.cuenta_id == cuenta_id,
            TipificacionExterna.matched.is_(False),
        )
    )

    total = query.count()
    items = (
        query
        .order_by(TipificacionExterna.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TipificacionExternaListResponse(
        items=[TipificacionExternaResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────
# RETRY MATCH — POST /accounts/{cuenta_id}/centro-control/retry-match
# ──────────────────────────────────────────────
@admin_router.post(
    "/accounts/{cuenta_id}/centro-control/retry-match",
    response_model=RetryMatchResponse,
    summary="Reintentar match de tipificaciones pendientes",
    description="Reintenta asociar tipificaciones sin lead a leads actuales por email.",
)
def retry_match(
    cuenta_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: str | None = Depends(verify_admin_key),
) -> RetryMatchResponse:
    account = db.query(Account).filter(Account.id == cuenta_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    pendientes = (
        db.query(TipificacionExterna)
        .filter(
            TipificacionExterna.cuenta_id == cuenta_id,
            TipificacionExterna.matched.is_(False),
        )
        .all()
    )

    total_pendientes = len(pendientes)
    matched_count = 0

    for tip in pendientes:
        lead = (
            db.query(Lead)
            .filter(
                Lead.cuenta_id == cuenta_id,
                Lead.datos["email"].astext == tip.email,
            )
            .first()
        )
        if lead:
            tip.lead_id = lead.id
            tip.matched = True
            matched_count += 1

            # Actualizar ultima_tipificacion del lead con la más reciente
            ultima = (
                db.query(TipificacionExterna)
                .filter(
                    TipificacionExterna.lead_id == lead.id,
                )
                .order_by(TipificacionExterna.created_at.desc())
                .first()
            )
            # La que estamos matcheando ahora o la existente más reciente
            mas_reciente = tip if (not ultima or tip.created_at >= ultima.created_at) else ultima
            lead.ultima_tipificacion = {
                "id_neotel": mas_reciente.id_neotel,
                "id_subresolucion": mas_reciente.id_subresolucion,
                "email": mas_reciente.email,
                "fecha": mas_reciente.created_at.isoformat(),
                "tipificacion_externa_id": str(mas_reciente.id),
            }

    db.commit()

    logger.info(
        "Retry-match para cuenta %s: %d/%d matcheados",
        cuenta_id, matched_count, total_pendientes,
    )

    return RetryMatchResponse(
        total_pendientes=total_pendientes,
        matched=matched_count,
        still_pending=total_pendientes - matched_count,
    )


# ──────────────────────────────────────────────
# HISTORIAL DE UN LEAD — GET /leads/{lead_id}/tipificaciones-externas
# ──────────────────────────────────────────────
@admin_router.get(
    "/leads/{lead_id}/tipificaciones-externas",
    response_model=list[TipificacionExternaResponse],
    summary="Historial de tipificaciones externas de un lead",
)
def historial_tipificaciones_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: str | None = Depends(verify_admin_key),
) -> list[TipificacionExternaResponse]:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    tipificaciones = (
        db.query(TipificacionExterna)
        .filter(TipificacionExterna.lead_id == lead_id)
        .order_by(TipificacionExterna.created_at.desc())
        .all()
    )

    return [TipificacionExternaResponse.model_validate(t) for t in tipificaciones]
