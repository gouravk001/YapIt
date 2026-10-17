from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import model_routes, notes, types
from app.config.loader import load_model_registry, load_types
from app.providers.factory import create_providers
from app.services.note_service import NoteService
from app.services.pipeline_service import PipelineService
from app.storage.database import init_db
from app.storage.queries import upsert_type

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

    # Seed types into the DB
    for td in type_definitions:
        await upsert_type(td.name, td.version, td.model_dump(), db_path=db_path)

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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error processing request to %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "detail": str(exc)},
    )


app.include_router(notes.router)
app.include_router(types.router)
app.include_router(model_routes.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
