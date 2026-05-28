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

# Singleton client — evita crear una instancia por request
_client: Optional[OpenAI] = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client

# Prompt compacto (~70 tokens vs ~250 anteriores)
SYSTEM_PROMPT = (
    "Sos Nodis, oráculo de IA del prode Mundial 2026 de Grupo Nods. "
    "Español rioplatense, solo fútbol.\n"
    "Para análisis de partido respondé EXACTAMENTE:\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "🏆 [FAVORITO] gana\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "🎯 Pronóstico: [Local] GL-GV [Visitante]\n"
    "⚡ Confianza: [Alta/Media-Alta/Media/Baja]\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "📌 [1 oración ≤20 palabras]\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "Usá las probabilidades del contexto para la confianza. "
    "Otras consultas: máximo 2 líneas."
)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class NodisRequest(BaseModel):
    message: str
    partido_id: Optional[int] = None
    history: list[ChatMessage] = []


class NodisResponse(BaseModel):
    reply: str
    probabilities: Optional[dict] = None


@router.post("/nodis/chat", response_model=NodisResponse)
def nodis_chat(
    req: NodisRequest,
    current_user: ProdeUser = Depends(get_current_prode_user),
    db: Session = Depends(get_db),
) -> NodisResponse:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Nodis no está disponible (falta OPENAI_API_KEY).")

    # ── 1. Contexto del partido (1 línea compacta) ──────────────────────────────
    context_block = ""
    prob_data: Optional[dict] = None

    if req.partido_id:
        partido = db.query(ProdePartido).filter(ProdePartido.id == req.partido_id).first()
        if partido and partido.equipo_local and partido.equipo_visitante:
            local = partido.equipo_local.nombre
            visitante = partido.equipo_visitante.nombre
            grupo = f" Grupo {partido.grupo}" if partido.grupo else ""
            context_block = f"\nPartido: {local} vs {visitante} | {partido.fase}{grupo}"

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
                    context_block += (
                        f"\nStats: {local} {pct['home_win']} | "
                        f"Empate {pct['draw']} | {visitante} {pct['away_win']}"
                    )

    system = SYSTEM_PROMPT + context_block

    # ── 2. Call OpenAI — historial recortado a 4 msgs (2 intercambios) ─────────
    messages: list[dict] = [{"role": "system", "content": system}]
    for msg in req.history[-4:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    completion = _get_client().chat.completions.create(
        model="gpt-4.1-nano",
        messages=messages,  # type: ignore[arg-type]
        max_tokens=200,
        temperature=0.5,
    )

    reply = completion.choices[0].message.content or "No pude generar una respuesta."
    return NodisResponse(reply=reply, probabilities=prob_data)
