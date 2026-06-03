"""Vesper backend — FastAPI layer wrapping the existing BoredBot scripts.

Routes are SYNC on purpose: FastAPI runs sync routes in a worker thread, so the
blocking `llm.call` (subprocess to the claude CLI, up to 120s) never blocks the
event loop."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import bridge
from .routes import chat, finance, heartbeat, memory, note, status


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Read SOUL.md once so the first chat request isn't slowed by disk I/O.
    bridge._soul()
    yield


app = FastAPI(title="Vesper API", lifespan=_lifespan)
app.include_router(status.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(finance.router, prefix="/api")
app.include_router(note.router, prefix="/api")
app.include_router(heartbeat.router, prefix="/api")
