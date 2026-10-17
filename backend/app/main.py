from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import model_routes, notes, types
from app.api.error_handlers import register_error_handlers
from app.config.loader import load_model_registry, load_types
from app.providers.factory import create_providers
from app.services.note_service import NoteService
from app.services.pipeline_service import PipelineService
from app.services.type_service import seed_types
from app.storage.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("yapit")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    db_path = os.environ.get("DATABASE_PATH", "./yapit.db")
    await init_db(db_path)

    # Load configuration
    registry = load_model_registry()
    type_definitions = load_types()

    await seed_types(type_definitions, db_path)

    # Initialize model providers (faster-whisper and ollama)
    transcriber, llm = create_providers(registry)

    # Store components on app.state
    app.state.db_path = db_path
    app.state.registry = registry
    app.state.model_registry = registry
    app.state.types = type_definitions
    app.state.type_definitions = type_definitions
    app.state.pipeline_service = PipelineService(transcriber, llm, type_definitions)
    app.state.note_service = NoteService(db_path=db_path)

    logger.info("YapIt backend initialized and ready.")
    yield


app = FastAPI(
    title="YapIt Local Voice Notes API",
    version="1.0.0",
    description="Local speech-to-text and structuring API using faster-whisper and Gemma on Ollama.",
    lifespan=lifespan,
)

register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(notes.router)
app.include_router(types.router)
app.include_router(model_routes.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
