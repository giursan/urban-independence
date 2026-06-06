"""FastAPI application: the companion brain's HTTP surface."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import chat, conversations, diagnostics, reports

app = FastAPI(title="Agentic Companion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(diagnostics.router)
app.include_router(reports.router)
