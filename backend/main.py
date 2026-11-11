"""
KiranaOS FastAPI Main Application
Entry point for Munim-AI KiranaOS Backend.
Adheres to PRD §2, §6, D-05, and Threat Model T-01-SC.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.routers.cfo_router import router as cfo_router
from backend.routers.cmo_router import router as cmo_router
from backend.routers.memory_router import router as memory_router
from backend.routers.voice_router import router as voice_router
from backend.services.seed_demo_data import STORE_NAME, seed_all


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.
    Initializes database schema and idempotently seeds Dadar Mumbai Kirana dataset.
    """
    # 1. Initialize SQLite schema
    init_db()

    # 2. Seed baseline demo dataset
    conn = get_db_connection()
    try:
        seed_all(conn)
    finally:
        close_db_connection(conn)

    yield


app = FastAPI(
    title="Munim-AI KiranaOS Backend",
    description="Deterministic append-only financial and inventory engine for Indian kiranas.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware (permits frontend dev server & mobile clients)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(memory_router)
app.include_router(voice_router)
app.include_router(cfo_router)
app.include_router(cmo_router)


@app.get("/")
def root():
    """Service status and store metadata."""
    return {
        "service": "Munim-AI KiranaOS Backend",
        "version": "0.1.0",
        "store": STORE_NAME,
        "status": "online",
        "docs_url": "/docs",
    }
