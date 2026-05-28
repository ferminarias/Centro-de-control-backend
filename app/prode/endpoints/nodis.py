from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.prode.auth import get_current_prode_user
from app.prode.models import ProdePartido, ProdeUser

router = APIRouter(tags=["Nodis IA"])

SYSTEM_PROMPT = """\
Sos Nodis, el asistente de IA del prode del Mundial FIFA 2026 de Grupo Nods.

Tu rol:
- Ayudás a los participantes a tomar mejores decisiones en sus predicciones de pronostico
- Analizás partidos y dás recomendaciones de resultados con confianza y razonamiento
- Sos conciso, directo y usás lenguaje informal en español rioplatense
- Solo hablás de fútbol, el Mundial 2026 y el prode — no de otros temas

Cuando recomendás un partido usá siempre este formato:
🎯 Mi recomendación: [Equipo A] X-Y [Equipo B]
📊 Confianza: [Baja / Media / Media-Alta / Alta]
💡 [2-3 oraciones de análisis concreto: forma reciente, estadísticas, contexto del grupo/fase]

Si el usuario pregunta algo general sobre el Mundial respondé con datos reales y útiles.
No digas que sos un modelo de lenguaje ni menciones a OpenAI. Sos Nodis, punto."""


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class NodisRequest(BaseModel):
    message: str
    partido_id: Optional[int] = None
    history: list[ChatMessage] = []


class NodisResponse(BaseModel):
    reply: str


@router.post("/nodis/chat", response_model=NodisResponse)
def nodis_chat(
    req: NodisRequest,
    current_user: ProdeUser = Depends(get_current_prode_user),
    db: Session = Depends(get_db),
) -> NodisResponse:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Nodis no está disponible (falta OPENAI_API_KEY).")

    # Build match context block if a partido_id was provided
    context_block = ""
    if req.partido_id:
        partido = db.query(ProdePartido).filter(ProdePartido.id == req.partido_id).first()
        if partido and partido.equipo_local and partido.equipo_visitante:
            local = partido.equipo_local.nombre
            visitante = partido.equipo_visitante.nombre
            fecha = partido.fecha.strftime("%d/%m/%Y %H:%M UTC")
            fase = partido.fase
            grupo = f" — Grupo {partido.grupo}" if partido.grupo else ""
            context_block = (
                f"\n\nContexto del partido consultado:\n"
                f"  {local} vs {visitante}\n"
                f"  Fecha: {fecha}\n"
                f"  Fase: {fase}{grupo}"
            )

    system = SYSTEM_PROMPT + context_block

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
    return NodisResponse(reply=reply)
