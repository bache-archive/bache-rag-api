import os
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field

from rag.retrieve import search_chunks
from rag.answer import synthesize

# --- Settings ---
API_KEY = os.getenv("API_KEY", "dev")
SERVICE_NAME = "Bache Talks RAG API"
SERVICE_VERSION = "3.0-alpha"
ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS")  # e.g. "*", or "https://your.site"
# Base URL used to populate the OpenAPI `servers` section (silences GPT builder warning)
BASE_URL = os.getenv("BASE_URL", "https://bache-rag-api.onrender.com")

# --- Models ---
class Chunk(BaseModel):
    talk_id: str
    archival_title: str
    recorded_date: str  # YYYY-MM-DD
    chunk_index: int
    text: str
    token_estimate: Optional[int] = None
    sha256: Optional[str] = None

class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural-language query")
    top_k: int = Field(8, ge=1, le=20, description="Top-K result limit (1-20)")

class SearchResponse(BaseModel):
    chunks: List[Chunk]

class Citation(BaseModel):
    talk_id: str
    archival_title: str
    recorded_date: str
    chunk_index: int

class AnswerRequest(BaseModel):
    query: str
    chunk_ids: List[str] = Field(..., description="Implementation-defined IDs, e.g. '2018-08-30:28'")

class AnswerResponse(BaseModel):
    answer: str
    citations: List[Citation]

# --- App ---
app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)

# (Optional) CORS if you later hit from a browser
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

def _check_auth(authorization: Optional[str]):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/", tags=["meta"], summary="Root")
def root() -> dict:
    return {"ok": True, "service": SERVICE_NAME, "version": SERVICE_VERSION}

@app.post("/search", response_model=SearchResponse, tags=["rag"], summary="Semantic search over chunk index")
def search(req: SearchRequest, authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    chunks = search_chunks(req.query, req.top_k)
    return SearchResponse(chunks=chunks)

@app.post("/answer", response_model=AnswerResponse, tags=["rag"], summary="Citation-grounded synthesis")
def answer(req: AnswerRequest, authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    return synthesize(req.query, req.chunk_ids)

# --- Custom OpenAPI with `servers` ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=SERVICE_NAME,
        version=SERVICE_VERSION,
        routes=app.routes,
    )
    openapi_schema["servers"] = [{"url": BASE_URL}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi