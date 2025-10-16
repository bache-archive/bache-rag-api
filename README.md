# 🧠 Bache Talks RAG API

**Semantic Retrieval API for the Chris Bache Archive (2014 – 2025)**  
FastAPI backend providing citation-grounded semantic search and synthesis across the verified public-talk corpus of philosopher-mystic **Christopher M. Bache**.  
Implements `/search` and `/answer` endpoints used by the Custom GPT **Bache Talks Librarian**.

[![version](https://img.shields.io/badge/version-v3.1-blue)](https://bache-rag-api.onrender.com)  
[API Docs](https://bache-rag-api.onrender.com/docs) · [OpenAPI JSON](https://bache-rag-api.onrender.com/openapi.json) · [Status](https://bache-rag-api.onrender.com/_rag_status)

---

## 📖 Overview

This service transforms the [**Chris Bache Archive**](https://github.com/bache-archive/chris-bache-archive) from a static transcript collection into an **interactive, citable research engine**.

Each of the 63 public talks (≈ 1 million characters) is pre-segmented into ≈ 2 800 paragraph-level chunks, embedded using **OpenAI `text-embedding-3-large` (3 072 dims)**, and indexed with **FAISS** for high-speed cosine search.

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

app.py                         → FastAPI app entry point
rag/retrieve.py                → FAISS + Parquet retrieval layer
rag/answer.py                  → Deterministic synthesis with inline citations
vendor/chris-bache-archive/    → Submodule (source corpus + vectors + tools)
reports/                       → Evaluation logs
requirements.txt               → Python dependencies

Tech Stack
	•	FastAPI – lightweight Python web framework
	•	FAISS – vector similarity search
	•	OpenAI text-embedding-3-large – 3 072-dim semantic vectors
	•	Parquet + SHA-256 – verifiable archival metadata
	•	Git Submodules – links canonical data from chris-bache-archive

⸻

🪶 Linked Submodule

This repo embeds the full archive as a Git submodule:

vendor/chris-bache-archive → https://github.com/bache-archive/chris-bache-archive

To clone and initialize everything:

git clone --recurse-submodules https://github.com/bache-archive/bache-rag-api.git
cd bache-rag-api

To pull the latest archive updates:

git submodule update --remote --merge vendor/chris-bache-archive
git commit -am "Update chris-bache-archive submodule to latest"
git push


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


⸻

🌐 Deployment (Render)

# render.yaml
services:
  - type: web
    name: bache-rag-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT

Environment variables

Name	Example	Description
API_KEY	your_generated_key	Auth for /search and /answer
OPENAI_API_KEY	sk-...	Used for embedding & synthesis
FAISS_INDEX_PATH	vendor/chris-bache-archive/vectors/bache-talks.index.faiss	Path inside submodule
METADATA_PATH	vendor/chris-bache-archive/vectors/bache-talks.embeddings.parquet	Metadata file
EMBED_MODEL	text-embedding-3-large	Embedding model name
EMBED_DIM	3072	Embedding dimensionality
MAX_PER_TALK	2	Limit of chunks per talk


⸻

🤖 Integration with Custom GPT

Name: Bache Talks Librarian
Schema: https://bache-rag-api.onrender.com/openapi.json
Auth: Authorization: Bearer <API_KEY>

GPT Instructions:
	•	Call /search (top_k = 8) → compose a 2–6 sentence summary.
	•	Use citations in format (YYYY-MM-DD, Title, chunk N).
	•	Never answer from priors; ground answers in retrieved context.
	•	If no matches, suggest query refinements.

⸻

🧾 Version History

v3.1 (2025-10-16) — Archive Submodule Integration + Metadata Enhancements
	•	Integrated chris-bache-archive as Git submodule → no more manual file copying
	•	Added URL and venue fields to Parquet metadata
	•	Rebuilt embeddings + FAISS index (clean counts 2561 × 3072)
	•	Verified retriever smoke test ✅
	•	README and CHANGELOG synchronized across repos

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
