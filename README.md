Here’s a clean, professional README.md tailored for your new repo bache-rag-api, harmonized with your archive’s CC0 ethos and the scholarly tone of the Bache project:

⸻


# Bache Talks RAG API

**Semantic Retrieval API for the Chris Bache Archive (2014 – 2025)**  
FastAPI backend providing citation-grounded semantic search across the verified public-talk corpus of philosopher-mystic **Christopher M. Bache**.  
Implements `/search` and `/answer` endpoints used by the Custom GPT *Bache Talks Librarian*.

---

## 📖 Overview

This service transforms the [**Chris Bache Archive**](https://github.com/bache-archive/chris-bache-archive) from a static collection of transcripts into an interactive research engine.

Each talk transcript (≈1 M characters total) is pre-segmented into ~2,800 overlapping paragraph chunks, embedded using **OpenAI text-embedding-3-large**, and indexed with **FAISS** for high-speed cosine search.  

The API returns fully citable excerpts with stable metadata:

(talk_id, archival_title, recorded_date, chunk_index, sha256)

and supports grounded summaries for scholarly and spiritual study.

---

## ⚙️ Endpoints

| Route | Method | Description |
|--------|---------|-------------|
| `/search` | `POST` | Semantic nearest-neighbor search. Returns top-k transcript chunks matching a natural-language query. |
| `/answer` | `POST` | Synthesizes a concise, citation-grounded summary from selected chunk IDs. |

### Example request

```bash
curl -X POST https://bache-rag-api.onrender.com/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"Diamond Luminosity","top_k":3}'


⸻

🧠 Architecture

app.py                # FastAPI app definition
rag/retrieve.py       # FAISS search wrapper
rag/answer.py         # Citation synthesis
vectors/              # (optional) local index files
requirements.txt      # Python dependencies

Tech stack
    •    FastAPI – lightweight Python web framework
    •    FAISS – vector similarity search
    •    OpenAI text-embedding-3-large – 3,072-dimensional semantic vectors
    •    Parquet + SHA-256 – verifiable archival storage

⸻

🚀 Local Development

# setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run
export API_KEY=dev
uvicorn app:app --host 0.0.0.0 --port 8000

Test:

curl -s -X POST http://localhost:8000/search \
  -H "Authorization: Bearer dev" \
  -H "Content-Type: application/json" \
  -d '{"query":"Diamond Luminosity"}' | jq


⸻

🌐 Deployment

This service is designed for Render free tier:

# render.yaml
services:
  - type: web
    name: bache-rag-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT

Add environment variable:

API_KEY=<your_generated_key>


⸻

🧩 Integration with Custom GPT
    •    Schema URL: https://bache-rag-api.onrender.com/openapi.json
    •    Authentication: API Key → Header Authorization: Bearer <key>
    •    Usage: Called automatically by the Bache Talks Librarian Custom GPT for retrieval and synthesis.

⸻

🧾 License
    •    Code: MIT License © 2025 Bache Archive
    •    Corpus & Transcripts: CC0 1.0 Universal (public domain dedication)

⸻

✨ Acknowledgments

Based on the visionary public work of Christopher M. Bache
and his decades-long exploration of consciousness and the “Future Human.”
Developed by the Bache Archive Project to preserve, search, and share these teachings for future generations.

---

This README is concise yet complete: professional for GitHub and Render, immediately reproducible by others, and perfectly aligned with your CC0 + MIT dual-license structure.
