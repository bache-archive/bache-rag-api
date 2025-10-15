# 🧠 Bache Talks RAG API

**Semantic Retrieval API for the Chris Bache Archive (2014 – 2025)**  
FastAPI backend providing citation-grounded semantic search and synthesis across the verified public-talk corpus of philosopher-mystic **Christopher M. Bache**.  
Implements `/search` and `/answer` endpoints used by the Custom GPT **Bache Talks Librarian**.

[![version](https://img.shields.io/badge/version-v3.0--alpha-blue)](https://bache-rag-api.onrender.com)
[API Docs](https://bache-rag-api.onrender.com/docs) · [OpenAPI JSON](https://bache-rag-api.onrender.com/openapi.json) · [Status](https://bache-rag-api.onrender.com/_rag_status)

---

## 📖 Overview

This service transforms the [**Chris Bache Archive**](https://github.com/bache-archive/chris-bache-archive) from a static transcript collection into an **interactive research engine**.

Each of the 63 public talks (≈ 1 million characters) is pre-segmented into ≈ 2 800 overlapping paragraph chunks, embedded using **OpenAI `text-embedding-3-large` (3 072 dimensions)**, and indexed with **FAISS** for high-speed cosine search.

The API returns citable excerpts with stable metadata:

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

app.py                # FastAPI app entry point
rag/retrieve.py       # FAISS + Parquet search wrapper
rag/answer.py         # Deterministic synthesis with inline citations
vectors/              # (optional) local FAISS + Parquet index
reports/              # Evaluation logs
requirements.txt      # Python dependencies

Tech Stack
	•	FastAPI – lightweight Python web framework
	•	FAISS – vector similarity search
	•	OpenAI text-embedding-3-large – 3 072-dimensional semantic vectors
	•	Parquet + SHA-256 – verifiable archival storage

⸻

🚀 Local Development

# setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run
export API_KEY=dev
uvicorn app:app --host 0.0.0.0 --port 8000

Test locally:

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

Add environment variables:

API_KEY=<your_generated_key>
OPENAI_API_KEY=<your_openai_key>
FAISS_INDEX_PATH=vectors/bache-talks.index.faiss
METADATA_PATH=vectors/bache-talks.embeddings.parquet
EMBED_MODEL=text-embedding-3-large
EMBED_DIM=3072
MAX_PER_TALK=2


⸻

🤖 Integration with Custom GPT

Name: Bache Talks Librarian
Schema URL: https://bache-rag-api.onrender.com/openapi.json
Authentication: Header Authorization: Bearer <API_KEY>

GPT instructions:
	•	Use only the RAG Action for retrieval.
	•	Call /search (top_k = 8), then compose a 2–6 sentence summary with citations (YYYY-MM-DD, Title, chunk N).
	•	If no results, reply that none were found and suggest refinements.
	•	Do not answer from priors.

⸻

🧾 Version History

v3.0-alpha (2025-10-15) – First live RAG deployment
	•	Embedded 63 talks → 2 817 vectors × 3 072 dims
	•	FAISS + Parquet index validated
	•	Deterministic citation synthesis implemented
	•	Deployed on Render (free tier)
	•	Custom GPT integration verified (4.5 / 5 eval score)

⸻

📜 License
	•	Code: MIT License © 2025 Bache Archive
	•	Corpus & Transcripts: CC0 1.0 Universal (Public Domain Dedication)

⸻

✨ Acknowledgments

Based on the visionary public teachings of Christopher M. Bache
and his decades-long exploration of consciousness and the “Future Human.”
Developed by the Bache Archive Project to preserve, search, and share these teachings for future generations.

⸻

“Preserving the living voice of humanity’s awakening—one talk at a time.”