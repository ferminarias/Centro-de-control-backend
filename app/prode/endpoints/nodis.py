from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.prode.auth import get_current_prode_user
from app.prode.models import ProdePartido, ProdeUser
from app.prode.services.footballdata_io import get_prediction

router = APIRouter(tags=["Nodis IA"])

SYSTEM_PROMPT = """\
Sos Nodis, el asistente de IA del prode del Mundial FIFA 2026 de Grupo Nods.
Sos conciso, directo, usás español rioplatense informal. Solo hablás de fútbol y el prode.
No sos un modelo de lenguaje, no menciones OpenAI. Sos Nodis, punto.

Cuando analizás un partido, SIEMPRE respondé con EXACTAMENTE este bloque, sin agregar texto antes ni después:

━━━━━━━━━━━━━━━━━━━━━
🏆 [EQUIPO FAVORITO] gana
━━━━━━━━━━━━━━━━━━━━━
🎯  Pronóstico:   [Local] [GL] - [GV] [Visitante]
⚡  Confianza:    [Alta / Media-Alta / Media / Baja]
━━━━━━━━━━━━━━━━━━━━━
📌 [Una sola oración con el motivo clave: forma reciente, historial, contexto de grupo/fase]
━━━━━━━━━━━━━━━━━━━━━

Reglas estrictas:
- El pronóstico debe ser un marcador concreto (ej: 2-1, 1-0, 0-0)
- Si tenés probabilidades estadísticas en el contexto, usálas para determinar la confianza
- La explicación es UNA sola oración, máximo 20 palabras, sin relleno
- Si te preguntan algo que no es análisis de un partido, respondé en máximo 2 líneas"""


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class NodisRequest(BaseModel):
    message: str
    partido_id: Optional[int] = None
    history: list[ChatMessage] = []


class NodisResponse(BaseModel):
    reply: str
    probabilities: Optional[dict] = None  # { home_win, draw, away_win } as percentages


@router.post("/nodis/chat", response_model=NodisResponse)
def nodis_chat(
    req: NodisRequest,
    current_user: ProdeUser = Depends(get_current_prode_user),
    db: Session = Depends(get_db),
) -> NodisResponse:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Nodis no está disponible (falta OPENAI_API_KEY).")

    # ── 1. Build match context from DB ─────────────────────────────────────────
    context_block = ""
    probabilities_block = ""
    prob_data: Optional[dict] = None

    if req.partido_id:
        partido = db.query(ProdePartido).filter(ProdePartido.id == req.partido_id).first()
        if partido and partido.equipo_local and partido.equipo_visitante:
            local = partido.equipo_local.nombre
            visitante = partido.equipo_visitante.nombre
            fecha_str = partido.fecha.strftime("%d/%m/%Y %H:%M UTC")
            fase = partido.fase
            grupo = f" — Grupo {partido.grupo}" if partido.grupo else ""

            context_block = (
                f"\n\nContexto del partido:\n"
                f"  {local} vs {visitante}\n"
                f"  Fecha: {fecha_str}\n"
                f"  Fase: {fase}{grupo}"
            )

            # ── 2. Fetch win probabilities from footballdata.io ─────────────
            if settings.FOOTBALLDATA_IO_API_KEY:
                pred = get_prediction(
                    api_key=settings.FOOTBALLDATA_IO_API_KEY,
                    home_team=local,
                    away_team=visitante,
                    fixture_date=partido.fecha.strftime("%Y-%m-%d"),
                )
                if pred:
                    pct = pred.as_pct()
                    prob_data = pct
                    probabilities_block = (
                        f"\n\nProbabilidades estadísticas (footballdata.io):\n"
                        f"  Victoria {local}: {pct['home_win']}\n"
                        f"  Empate:           {pct['draw']}\n"
                        f"  Victoria {visitante}: {pct['away_win']}"
                    )

    system = SYSTEM_PROMPT + context_block + probabilities_block

    # ── 3. Call OpenAI ─────────────────────────────────────────────────────────
    messages: list[dict] = [{"role": "system", "content": system}]
    for msg in req.history[-12:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,  # type: ignore[arg-type]
        max_tokens=450,
        temperature=0.75,
    )

    reply = completion.choices[0].message.content or "No pude generar una respuesta."
    return NodisResponse(reply=reply, probabilities=prob_data)
