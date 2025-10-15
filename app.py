import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Security, Response
from fastapi.openapi.utils import get_openapi
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from rag.retrieve import search_chunks
from rag.answer import synthesize

# --- Settings ---
API_KEY = os.getenv("API_KEY", "dev")
SERVICE_NAME = "Bache Talks RAG API"
SERVICE_VERSION = "3.0-alpha"
ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS")  # e.g. "*", or "https://your.site"
BASE_URL = os.getenv("BASE_URL", "https://bache-rag-api.onrender.com")

# --- Security scheme (single, named 'ApiKeyAuth') ---
api_key_header = APIKeyHeader(name="Authorization", scheme_name="ApiKeyAuth", auto_error=False)

def _check_auth(authorization: Optional[str]):
    if not authorization or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

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

class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str

# --- App ---
app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)

# (Optional) CORS for future browser clients (not needed for GPT Actions)
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

# GET shows in schema; HEAD is hidden (but serves Render health checks)
@app.get("/", tags=["meta"], summary="Root", response_model=HealthResponse)
def root() -> HealthResponse:
    return HealthResponse(ok=True, service=SERVICE_NAME, version=SERVICE_VERSION)

@app.head("/", include_in_schema=False)
def root_head():
    return Response(status_code=200)

@app.post("/search", response_model=SearchResponse, tags=["rag"], summary="Semantic search over chunk index")
def search(req: SearchRequest, authorization: Optional[str] = Security(api_key_header)):
    _check_auth(authorization)
    chunks = search_chunks(req.query, req.top_k)
    return SearchResponse(chunks=chunks)

@app.post("/answer", response_model=AnswerResponse, tags=["rag"], summary="Citation-grounded synthesis")
def answer(req: AnswerRequest, authorization: Optional[str] = Security(api_key_header)):
    _check_auth(authorization)
    return synthesize(req.query, req.chunk_ids)

# --- Custom OpenAPI: add `servers`, keep exactly ONE security scheme ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=SERVICE_NAME,
        version=SERVICE_VERSION,
        routes=app.routes,
    )
    # Base URL so GPT builder doesn't warn
    openapi_schema["servers"] = [{"url": BASE_URL}]
    # Ensure only ONE security scheme is advertised (matches scheme_name above)
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Authorization"}
    }
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi