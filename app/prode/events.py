"""
Thread-safe SSE broadcaster for prode real-time updates.

APScheduler runs sync in a background thread; this module bridges that thread
to async SSE subscribers via call_soon_threadsafe.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None
_queues: list[asyncio.Queue[str]] = []


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called once from the FastAPI lifespan after the event loop is running."""
    global _loop
    _loop = loop
    logger.info("SSE broadcaster ready (%d existing subscribers)", len(_queues))


def broadcast(event: str, data: dict | None = None) -> None:
    """
    Push an event to all connected SSE clients.
    Safe to call from any thread (APScheduler, sync services, etc.).
    """
    if not _loop or not _queues:
        return
    payload = json.dumps({"event": event, **(data or {})})
    for q in list(_queues):
        try:
            _loop.call_soon_threadsafe(q.put_nowait, payload)
        except Exception as exc:
            logger.debug("SSE broadcast error: %s", exc)


async def subscribe() -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted strings.
    Sends a keepalive comment every 20 s to prevent proxy timeouts.
    """
    q: asyncio.Queue[str] = asyncio.Queue()
    _queues.append(q)
    logger.debug("SSE client connected (total: %d)", len(_queues))
    try:
        yield 'data: {"event":"connected"}\n\n'
        while True:
            try:
                payload = await asyncio.wait_for(q.get(), timeout=20.0)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        try:
            _queues.remove(q)
        except ValueError:
            pass
        logger.debug("SSE client disconnected (total: %d)", len(_queues))
