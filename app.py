#!/usr/bin/env python3
"""
app.py — Bache Talks RAG API
FastAPI service providing semantic retrieval and citation-grounded synthesis
over the public Chris Bache talk transcripts.

Author: bache-archive
Version: 3.1
License: MIT
"""

import os
import sys
import logging
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Security, Response
from fastapi.openapi.utils import get_openapi
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------
# Make the submodule importable: vendor/chris-bache-archive
# ---------------------------------------------------------------------
VENDOR_PATH = os.path.join(os.path.dirname(__file__), "vendor", "chris-bache-archive")
if VENDOR_PATH not in sys.path:
    sys.path.insert(0, VENDOR_PATH)

# Now import the canonical RAG engine from the submodule
from rag.retrieve import Retriever  # type: ignore
from rag.answer import answer_from_chunks  # type: ignore

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bache-rag-api")

# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------
API_KEY = os.getenv("API_KEY", "dev")
SERVICE_NAME = "Bache Talks RAG API"
SERVICE_VERSION = "3.1"
BASE_URL = os.getenv("BASE_URL", "https://bache-rag-api.onrender.com")
ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS")  # e.g. "*", or "https://your.site"

# RAG / FAISS config via env (also used by Retriever)
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "vectors/bache-talks.index.faiss")
METADATA_PATH = os.getenv("METADATA_PATH", "vectors/bache-talks.embeddings.parquet")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")
MAX_PER_TALK = int(os.getenv("MAX_PER_TALK", "2"))

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
    # Core
    id: Optional[int] = None
    talk_id: Optional[str] = None
    archival_title: Optional[str] = None
    # The parquet typically uses "published"; keep recorded_date for b/w-compat.
    recorded_date: Optional[str] = Field(None, description="Recording date (YYYY-MM-DD)")
    published: Optional[str] = None
    chunk_index: Optional[int] = None
    text: Optional[str] = None
    token_estimate: Optional[int] = Field(default=None, alias="token_est")
    sha256: Optional[str] = Field(default=None, alias="hash")
    channel: Optional[str] = None
    source_type: Optional[str] = None
    # Human-readable extras
    citation: Optional[str] = None
    url: Optional[str] = None
    transcript_path: Optional[str] = None
    # Optional debug score
    score: Optional[float] = Field(default=None, alias="_score")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural-language query")
    top_k: int = Field(8, ge=1, le=20, description="Top-K result limit (1–20)")


class SearchResponse(BaseModel):
    chunks: List[Chunk]


class Citation(BaseModel):
    talk_id: Optional[str] = None
    archival_title: Optional[str] = None
    recorded_date: Optional[str] = None
    published: Optional[str] = None
    chunk_index: Optional[int] = None
    citation: Optional[str] = None
    url: Optional[str] = None


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

# Singleton Retriever (submodule implementation)
_RETRIEVER = Retriever(
    parquet_path=METADATA_PATH,
    faiss_path=FAISS_INDEX_PATH,
    model=EMBED_MODEL,
    per_talk_cap=MAX_PER_TALK,
    top_k_default=8,
)


def _normalize_date(row: Dict[str, Any]) -> str:
    """Prefer published → date → recorded_date, return '' if none."""
    return str(row.get("published") or row.get("date") or row.get("recorded_date") or "")


def _row_to_chunk(row: Dict[str, Any]) -> Chunk:
    """Map retriever row → API Chunk model (preserve pretty fields)."""
    return Chunk(
        id=row.get("id"),
        talk_id=row.get("talk_id"),
        archival_title=row.get("archival_title"),
        recorded_date=_normalize_date(row),   # put a value here for clients that read recorded_date
        published=row.get("published"),
        chunk_index=row.get("chunk_index"),
        text=row.get("text"),
        token_est=row.get("token_est") or row.get("token_estimate"),
        hash=row.get("hash"),
        channel=row.get("channel"),
        source_type=row.get("source_type"),
        citation=row.get("citation"),
        url=row.get("url"),
        transcript_path=row.get("transcript_path"),
        _score=row.get("_score"),
    )


def _status_dict() -> dict:
    """Expose retriever runtime status + env/config."""
    try:
        status = _RETRIEVER.status()
    except Exception as e:
        status = {"error": f"{type(e).__name__}: {e}"}
    status.update(
        {
            "faiss_index_path": FAISS_INDEX_PATH,
            "metadata_path": METADATA_PATH,
            "embed_model": EMBED_MODEL,
            "per_talk_cap": MAX_PER_TALK,
            "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        }
    )
    return status


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
    rows = _RETRIEVER.search(req.query, k=req.top_k)
    chunks = [_row_to_chunk(r) for r in rows]
    # ensure recorded_date is set even if parquet only had 'published'
    for c in chunks:
        if not c.recorded_date:
            c.recorded_date = c.published or None
    return SearchResponse(chunks=chunks)


@app.post("/answer", response_model=AnswerResponse, tags=["rag"], summary="Citation-grounded synthesis")
def answer(req: AnswerRequest, authorization: Optional[str] = Security(api_key_header)):
    """
    Generate a short, citation-grounded summary.

    If `chunk_ids` are provided and the retriever supports `get_by_ids`, those are used;
    otherwise the system performs retrieval before composing an answer.
    """
    _check_auth(authorization)
    logger.info("ANSWER query=%r chunk_ids=%d", req.query, len(req.chunk_ids or []))

    rows: List[Dict[str, Any]] = []
    if req.chunk_ids and hasattr(_RETRIEVER, "get_by_ids"):
        try:
            rows = _RETRIEVER.get_by_ids(req.chunk_ids)  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning("get_by_ids failed (%s); falling back to search", e)

    if not rows:
        rows = _RETRIEVER.search(req.query, k=8)

    answer_text = answer_from_chunks(req.query, rows, max_sentences=5)

    citations = [
        Citation(
            talk_id=str(r.get("talk_id") or ""),
            archival_title=str(r.get("archival_title") or ""),
            recorded_date=_normalize_date(r) or None,
            published=r.get("published"),
            chunk_index=int(r.get("chunk_index") or 0),
            citation=r.get("citation"),
            url=r.get("url"),
        )
        for r in rows[:6]
    ]

    return AnswerResponse(answer=answer_text, citations=citations)


# --- DEBUG: verify env + file existence --------------------------------
@app.get("/_debug", tags=["meta"], summary="Debug file/env status")
def debug_status() -> dict:
    """Expose basic env + file presence to help diagnose FAISS loading in Render."""
    return {
        "cwd": os.getcwd(),
        "env": {
            "FAISS_INDEX_PATH": FAISS_INDEX_PATH,
            "METADATA_PATH": METADATA_PATH,
            "EMBED_MODEL": EMBED_MODEL,
            "MAX_PER_TALK": MAX_PER_TALK,
        },
        "exists": {
            "faiss_index_exists": os.path.exists(FAISS_INDEX_PATH),
            "metadata_exists": os.path.exists(METADATA_PATH),
        },
    }


@app.get("/_rag_status", tags=["meta"], summary="RAG/FAISS runtime status")
def get_rag_status() -> dict:
    """Report runtime status of FAISS + metadata (and whether an OpenAI key is present)."""
    return _status_dict()


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