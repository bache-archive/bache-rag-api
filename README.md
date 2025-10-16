# 🧠 Bache Talks RAG API

**Semantic Retrieval API for the Chris Bache Archive (2014 – 2025)**  
FastAPI backend providing citation-grounded semantic search and synthesis across the verified public-talk corpus of philosopher-mystic **Christopher M. Bache**.  
Implements `/search` and `/answer` endpoints used by the Custom GPT **Bache Talks Librarian**.

[![version](https://img.shields.io/badge/version-v3.1.0-blue)](https://bache-rag-api.onrender.com)  
[API Docs](https://bache-rag-api.onrender.com/docs) · [OpenAPI JSON](https://bache-rag-api.onrender.com/openapi.json) · [Status](https://bache-rag-api.onrender.com/_rag_status)

---

## 📖 Overview

This service transforms the [**Chris Bache Archive**](https://github.com/bache-archive/chris-bache-archive) from a static transcript collection into an **interactive, citable research engine**.

Each of the 63 public talks (≈ 1 million characters) is pre-segmented into ≈ 2 800 paragraph-level chunks, embedded with **OpenAI `text-embedding-3-large` (3 072 dims)**, and indexed in-memory with **FAISS** for high-speed cosine search.

**Index statistics:** `parquet_rows = 2561`, `faiss_ntotal = 2561`  
**Citation format:** `(YYYY-MM-DD, Archival Title, chunk N)`

The API returns **verifiable excerpts** with stable metadata:

(talk_id, archival_title, recorded_date, chunk_index, sha256)

and produces grounded multi-talk summaries for scholarly, historical, and spiritual study.

---

## ⚙️ Endpoints

| Route | Method | Description |
|-------|---------|-------------|
| `/search` | `POST` | Semantic nearest-neighbor search. Returns top-k transcript chunks matching a natural-language query. |
| `/answer` | `POST` | Synthesizes a concise, citation-grounded answer from retrieved chunks. |

### Example Request

```bash
curl -X POST https://bache-rag-api.onrender.com/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"Diamond Luminosity","top_k":3}'


⸻

🧩 Architecture

app.py          → FastAPI app entry point
rag/retrieve.py → FAISS + Parquet retrieval layer
rag/answer.py   → Deterministic synthesis with inline citations
vectors/        → Local FAISS + Parquet index (copied from archive)
reports/        → Evaluation logs
requirements.txt→ Python dependencies

Tech Stack
	•	FastAPI – lightweight Python web framework
	•	FAISS – vector similarity search
	•	OpenAI text-embedding-3-large – 3 072-dim semantic vectors
	•	Parquet + SHA-256 – verifiable archival metadata

⸻

🪶 Data Source

Vectors and metadata were built from the canonical
chris-bache-archive repository (v2.6-dev, Oct 2025).
They are bundled locally in vectors/ for deterministic builds on Render.

⸻

🚀 Local Development

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Run the API locally:

export API_KEY=dev
uvicorn app:app --host 0.0.0.0 --port 8000

Test:

curl -s -X POST http://localhost:8000/search \
  -H "Authorization: Bearer dev" \
  -H "Content-Type: application/json" \
  -d '{"query":"Diamond Luminosity"}' | jq

Quick status check (from any shell):

curl -sS https://bache-rag-api.onrender.com/_debug | jq
curl -sS https://bache-rag-api.onrender.com/_rag_status | jq


⸻

🌐 Deployment (Render)

# render.yaml
services:
  - type: web
    name: bache-rag-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT

Environment Variables

Name	Example	Description
API_KEY	your_generated_key	Auth for /search and /answer
OPENAI_API_KEY	sk-…	Used for embedding & synthesis
FAISS_INDEX_PATH	vectors/bache-talks.index.faiss	Local FAISS index
METADATA_PATH	vectors/bache-talks.embeddings.parquet	Local Parquet metadata
EMBED_MODEL	text-embedding-3-large	Embedding model name
EMBED_DIM	3072	Embedding dimensionality
MAX_PER_TALK	2	Limit of chunks per talk


⸻

🤖 Integration with Custom GPT

Name: Bache Talks Librarian
Schema: https://bache-rag-api.onrender.com/openapi.json
Auth: Authorization: Bearer <API_KEY>

GPT Instructions
	•	Call /search (top_k = 8) → compose a 2–6 sentence summary
	•	Use citations in format (YYYY-MM-DD, Title, chunk N)
	•	Never answer from priors; ground answers in retrieved context
	•	If no matches, suggest query refinements

⸻

🧾 Version History

v3.1.0 (2025-10-16) — Stable Render Deployment + Citation Schema Overhaul
	•	Removed git submodule dependency; bundled local vectors for free-tier Render builds
	•	Rewrote app.py for self-contained imports and single auth scheme
	•	Added robust /_debug and /_rag_status endpoints for diagnostics
	•	Introduced human-readable citation format (YYYY-MM-DD, Title, chunk N)
	•	Verified Render API ✅ (parquet_rows = 2561, faiss_ntotal = 2561)
	•	Confirmed Custom GPT integration with working multi-talk summaries

v3.0-alpha (2025-10-15) — First Live RAG Deployment
	•	63 talks → ≈ 2 800 vectors × 3 072 dims
	•	Citation-grounded synthesis pipeline
	•	Render deployment + Custom GPT integration (4.5 / 5 eval score)

⸻

📜 License
	•	Code: MIT License © 2025 Bache Archive
	•	Corpus & Transcripts: CC0 1.0 Universal (Public Domain Dedication)

⸻

✨ Acknowledgments

Based on the visionary public teachings of Christopher M. Bache,
and his decades-long exploration of consciousness and the “Future Human.”
Developed by the Bache Archive Project to preserve, search, and share these teachings for future generations.

“Preserving the living voice of humanity’s awakening — one talk at a time.”
