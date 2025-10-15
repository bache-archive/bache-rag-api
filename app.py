"""
app.py — Bache Talks RAG API
FastAPI service providing semantic retrieval and citation-grounded synthesis
over the public Chris Bache talk transcripts.

Author: bache-archive
Version: 3.0-alpha
License: CC0-1.0
"""

import os
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Security, Response
from fastapi.openapi.utils import get_openapi
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from rag.retrieve import search_chunks, rag_status
from rag.answer import synthesize

# ---------------------------------------------------------------------
# Logging (ensure INFO shows in Render logs)
# ---------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bache-rag-api")

# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------
API_KEY = os.getenv("API_KEY", "dev")
SERVICE_NAME = "Bache Talks RAG API"
SERVICE_VERSION = "3.0-alpha"
BASE_URL = os.getenv("BASE_URL", "https://bache-rag-api.onrender.com")
ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS")  # e.g. "*", or "https://your.site"

# For debug endpoint defaults (also used by retrieve.py via env)
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "vectors/bache-talks.index.faiss")
METADATA_PATH = os.getenv("METADATA_PATH", "vectors/bache-talks.embeddings.parquet")

# Single security scheme — avoids GPT “multiple security schemes” error
api_key_header = APIKeyHeader(name="Authorization", scheme_name="ApiKeyAuth", auto_error=False)


def _check_auth(authorization: Optional[str]):
    """Simple bearer check."""
    if not authorization or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------
class Chunk(BaseModel):
    talk_id: str
    archival_title: str
    recorded_date: str
    chunk_index: int
    text: str
    token_estimate: Optional[int] = None
    sha256: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural-language query")
    top_k: int = Field(8, ge=1, le=20, description="Top-K result limit (1–20)")


class SearchResponse(BaseModel):
    chunks: List[Chunk]


class Citation(BaseModel):
    talk_id: str
    archival_title: str
    recorded_date: str
    chunk_index: int


class AnswerRequest(BaseModel):
    query: str
    chunk_ids: List[str] = Field(
        default_factory=list,
        description=(
            "Optional list of chunk IDs (format 'talk_id:chunk_index'). "
            "If empty or omitted, the server retrieves chunks automatically."
        ),
    )


class AnswerResponse(BaseModel):
    answer: str
    citations: List[Citation]


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str


# ---------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------
app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)

# Optional CORS (not required for GPT Actions)
if ALLOW_ORIGINS:
    from fastapi.middleware.cors import CORSMiddleware

    origins = [o.strip() for o in ALLOW_ORIGINS.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["*"],
    )


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.get("/", tags=["meta"], summary="Root", response_model=HealthResponse)
def root() -> HealthResponse:
    """Public health/status route (appears in schema)."""
    return HealthResponse(ok=True, service=SERVICE_NAME, version=SERVICE_VERSION)


@app.head("/", include_in_schema=False)
def root_head():
    """Render uses HEAD for health checks."""
    return Response(status_code=200)


@app.post("/search", response_model=SearchResponse, tags=["rag"], summary="Semantic search over chunk index")
def search(req: SearchRequest, authorization: Optional[str] = Security(api_key_header)):
    """Return top-K semantic matches for the query."""
    _check_auth(authorization)
    logger.info("SEARCH query=%r top_k=%d", req.query, req.top_k)
    chunks = search_chunks(req.query, req.top_k)
    return SearchResponse(chunks=chunks)


@app.post("/answer", response_model=AnswerResponse, tags=["rag"], summary="Citation-grounded synthesis")
def answer(req: AnswerRequest, authorization: Optional[str] = Security(api_key_header)):
    """
    Generate a short, citation-grounded summary.

    If `chunk_ids` are provided, they are looked up; otherwise the system
    performs retrieval internally before composing an answer (handled inside synthesize()).
    """
    _check_auth(authorization)
    logger.info("ANSWER query=%r chunk_ids=%d", req.query, len(req.chunk_ids or []))
    return synthesize(req.query, req.chunk_ids)


# --- DEBUG: verify env + file existence --------------------------------
@app.get("/_debug", tags=["meta"], summary="Debug file/env status")
def debug_status() -> dict:
    """Expose basic env + file presence to help diagnose FAISS loading in Render."""
    return {
        "cwd": os.getcwd(),
        "env": {
            "FAISS_INDEX_PATH": FAISS_INDEX_PATH,
            "METADATA_PATH": METADATA_PATH,
            "EMBED_MODEL": os.getenv("EMBED_MODEL"),
            "EMBED_DIM": os.getenv("EMBED_DIM"),
            "MAX_PER_TALK": os.getenv("MAX_PER_TALK"),
        },
        "exists": {
            "faiss_index_exists": os.path.exists(FAISS_INDEX_PATH),
            "metadata_exists": os.path.exists(METADATA_PATH),
        },
    }
    
@app.get("/_rag_status", tags=["meta"], summary="RAG/FAISS runtime status")
def get_rag_status() -> dict:
    """
    Report runtime status of FAISS + metadata (and whether an OpenAI key is present).
    """
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    try:
        status = rag_status()
    except Exception as e:
        status = {"error": f"{type(e).__name__}: {e}"}
    status["has_openai_key"] = has_openai
    return status


# ---------------------------------------------------------------------
# Custom OpenAPI (fixes GPT Action warnings)
# ---------------------------------------------------------------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=SERVICE_NAME,
        version=SERVICE_VERSION,
        routes=app.routes,
    )

    # Base URL advertised for schema consumers (GPT Actions)
    openapi_schema["servers"] = [{"url": BASE_URL}]

    # Exactly one security scheme
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Authorization"}
    }
    openapi_schema["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi