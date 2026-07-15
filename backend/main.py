"""Personalized Networking Assistant — FastAPI backend service.

Run with:  uvicorn backend.main:app --reload --port 8000
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import generate, verify, history

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Personalized Networking Assistant API",
    description=(
        "Generates smart, tailored conversation starters for networking events "
        "using DistilBERT (theme extraction) and GPT-2 (text generation), with "
        "Wikipedia-backed fact verification and a feedback-driven history log."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router)
app.include_router(verify.router)
app.include_router(history.router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "service": "Personalized Networking Assistant API",
        "docs": "/docs",
        "endpoints": ["/api/v1/generate", "/api/v1/verify", "/api/v1/history", "/api/v1/feedback"],
    }


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
