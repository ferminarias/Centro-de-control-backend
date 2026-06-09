from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.prode.auth import get_current_prode_user
from app.prode.models import ProdeUser
from app.prode import events

router = APIRouter(tags=["Prode - Events"])


@router.get(
    "/events",
    summary="SSE stream — fixture y tabla en tiempo real",
    description=(
        "Authenticated Server-Sent Events stream. "
        "Emits `fixture_updated` when a match state/score changes, "
        "`tabla_updated` when points are recalculated. "
        "Keepalive comment sent every 20 s."
    ),
)
async def prode_events(
    request: Request,
    _: ProdeUser = Depends(get_current_prode_user),
):
    async def stream():
        async for chunk in events.subscribe():
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
