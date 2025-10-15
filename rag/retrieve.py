"""
rag/retrieve.py — Semantic retrieval layer for the Bache Talks RAG

- Lazy-loads FAISS index + Parquet metadata from env paths
- Performs semantic search with OpenAI embeddings → FAISS nearest neighbors
- Diversifies results (≤ MAX_PER_TALK per talk)
- Falls back to a small demo sample if FAISS or files are unavailable
"""

from typing import List, Dict, Tuple, Optional
import os
import logging

logger = logging.getLogger(__name__)

# ----------------------------
# Environment / constants
# ----------------------------
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "vectors/bache-talks.index.faiss")
METADATA_PATH    = os.getenv("METADATA_PATH", "vectors/bache-talks.embeddings.parquet")
EMBED_MODEL      = os.getenv("EMBED_MODEL", "text-embedding-3-large")
EMBED_DIM        = int(os.getenv("EMBED_DIM", "3072"))
MAX_PER_TALK     = int(os.getenv("MAX_PER_TALK", "3"))

# ----------------------------
# Optional deps (guarded)
# ----------------------------
try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None

try:
    import numpy as np
    import pandas as pd
except Exception:  # pragma: no cover
    np = None
    pd = None

# OpenAI client (only used when doing real search)
_OPENAI_KEY = os.getenv("OPENAI_API_KEY")
_openai_client = None
if _OPENAI_KEY:
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=_OPENAI_KEY)
    except Exception:
        _openai_client = None

# ----------------------------
# Globals (lazy-loaded)
# ----------------------------
_faiss_index = None  # type: ignore
_meta_df: Optional["pd.DataFrame"] = None

# ----------------------------
# Demo sample (fallback)
# ----------------------------
_SAMPLE: List[Dict] = [
    {
        "talk_id": "2018-08-30-diamonds-from-heaven",
        "archival_title": "Diamonds from Heaven",
        "recorded_date": "2018-08-30",
        "chunk_index": 28,
        "text": "Diamond Luminosity is described as a blazing, clear light of unconditional love and knowing.",
        "token_estimate": 120,
        "sha256": "demo_sha256_not_real",
    },
    {
        "talk_id": "2019-02-17-awakening-to-the-future-human",
        "archival_title": "Awakening to the Future Human",
        "recorded_date": "2019-02-17",
        "chunk_index": 34,
        "text": "The Future Human represents consciousness becoming self-luminous through collective evolution.",
        "token_estimate": 130,
        "sha256": "demo_sha256_not_real_2",
    },
    {
        "talk_id": "2020-05-09-a-new-vision-of-humanity",
        "archival_title": "A New Vision of Humanity",
        "recorded_date": "2020-05-09",
        "chunk_index": 12,
        "text": "Humanity is being invited to awaken as a planetary species, participating consciously in cosmic evolution.",
        "token_estimate": 125,
        "sha256": "demo_sha256_not_real_3",
    },
]

# ----------------------------
# Loaders
# ----------------------------
def _load_index_and_meta() -> None:
    """Idempotent lazy loader for FAISS index + Parquet metadata."""
    global _faiss_index, _meta_df

    if _faiss_index is not None and _meta_df is not None:
        return

    print("[RAG] Loading FAISS + metadata...")  # visible in Render logs

    # Hard guards
    if faiss is None or np is None or pd is None:
        print("[RAG] faiss/pandas/numpy not available; using demo fallback")
        _faiss_index = None
        _meta_df = None
        return

    if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(METADATA_PATH):
        print(f"[RAG] Files missing. FAISS_INDEX_PATH={FAISS_INDEX_PATH} exists={os.path.exists(FAISS_INDEX_PATH)}")
        print(f"[RAG] Files missing. METADATA_PATH={METADATA_PATH} exists={os.path.exists(METADATA_PATH)}")
        _faiss_index = None
        _meta_df = None
        return

    # Load index + metadata
    _faiss_index = faiss.read_index(FAISS_INDEX_PATH)
    _meta_df = pd.read_parquet(METADATA_PATH)

    print(f"[RAG] FAISS ready: ntotal={_faiss_index.ntotal}, dim={getattr(_faiss_index, 'd', None)}")
    print(f"[RAG] Metadata: rows={len(_meta_df)} cols={list(_meta_df.columns)}")


def _embed_query(text: str) -> Optional["np.ndarray"]:
    """Embed query using OpenAI; return float32 vector of EMBED_DIM (normalized)."""
    if _openai_client is None or np is None:
        return None
    try:
        resp = _openai_client.embeddings.create(model=EMBED_MODEL, input=text)
        vec = np.array(resp.data[0].embedding, dtype="float32")
        if vec.shape[0] != EMBED_DIM:
            # Mismatch safety
            return None
        # Normalize for cosine (IndexFlatIP with unit-normalized vectors)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec
    except Exception as e:
        logger.warning("OpenAI embed failed: %s", e)
        return None

# ----------------------------
# Public API
# ----------------------------
def perform_search(query: str, top_k: int = 16) -> List[Dict]:
    """
    Semantic search:
      - If FAISS + metadata + OpenAI are available, do real ANN search
      - Else, return demo sample
    """
    _load_index_and_meta()

    if _faiss_index is None or _meta_df is None:
        logger.info("Using demo fallback (FAISS/meta not ready)")
        return _SAMPLE[: min(top_k, len(_SAMPLE))]

    qvec = _embed_query(query)
    if qvec is None:
        logger.info("Embedding unavailable; returning first rows as fallback")
        # Return first rows (deterministic) to prove we're reading real metadata
        return _rows_to_chunks(list(range(min(top_k, len(_meta_df)))))

    # Search FAISS (IP assumes vectors in index are already normalized)
    try:
        q = qvec.reshape(1, -1)
        scores, ids = _faiss_index.search(q, top_k * 4)  # overfetch for diversity
        idxs = [int(i) for i in ids[0] if i >= 0]
        return _rows_to_chunks(idxs)
    except Exception as e:
        logger.warning("FAISS search failed (%s); using metadata fallback", e)
        return _rows_to_chunks(list(range(min(top_k, len(_meta_df)))))

def _rows_to_chunks(row_idxs: List[int]) -> List[Dict]:
    """Map row indices in the Parquet metadata to chunk dicts (with diversity)."""
    assert _meta_df is not None
    results: List[Dict] = []
    seen_per_talk: Dict[str, int] = {}

    for ridx in row_idxs:
        if ridx < 0 or ridx >= len(_meta_df):
            continue
        row = _meta_df.iloc[ridx]

        # Expected columns (adapt if your Parquet uses different names)
        talk_id        = str(row.get("talk_id", ""))
        archival_title = str(row.get("archival_title", ""))
        recorded_date  = str(row.get("recorded_date", ""))
        chunk_index    = int(row.get("chunk_index", 0))
        text           = str(row.get("text", ""))
        token_estimate = int(row.get("token_estimate", 0)) if "token_estimate" in row else None
        sha256         = str(row.get("sha256", "")) if "sha256" in row else None

        # Per-talk cap
        cnt = seen_per_talk.get(talk_id, 0)
        if cnt >= MAX_PER_TALK:
            continue
        seen_per_talk[talk_id] = cnt + 1

        results.append({
            "talk_id": talk_id,
            "archival_title": archival_title,
            "recorded_date": recorded_date,
            "chunk_index": chunk_index,
            "text": text,
            "token_estimate": token_estimate,
            "sha256": sha256,
        })

    return results

def search_chunks(query: str, top_k: int = 8) -> List[Dict]:
    """
    Retrieve semantically similar transcript chunks for a natural-language query.
    Diversifies results to ≤ MAX_PER_TALK and caps at top_k.
    """
    raw = perform_search(query, top_k=max(top_k * 3, 16))  # overfetch to allow diversity
    # Deduplicate by (talk_id, chunk_index) while preserving order
    dedup: List[Dict] = []
    seen: set[Tuple[str, int]] = set()
    for r in raw:
        key = (r["talk_id"], r["chunk_index"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    # Group and take ≤ MAX_PER_TALK per talk (already enforced in _rows_to_chunks, but keep belt+suspenders)
    grouped: Dict[str, List[Dict]] = {}
    for r in dedup:
        grouped.setdefault(r["talk_id"], []).append(r)

    diversified: List[Dict] = []
    for _, chunks in grouped.items():
        diversified.extend(chunks[:MAX_PER_TALK])

    return diversified[:top_k]

# --- RAG runtime status (for /_rag_status) ---
def rag_status() -> dict:
    """Return runtime status for FAISS + metadata (safe to expose)."""
    global _faiss_index, _meta_df
    try:
        _load_index_and_meta()
    except Exception as e:
        return {
            "faiss_imported": faiss is not None,
            "index_loaded": _faiss_index is not None,
            "meta_loaded": _meta_df is not None,
            "error": f"{type(e).__name__}: {e}",
        }

    # Extract some internals (guarded)
    index_dim = None
    index_ntotal = None
    try:
        if _faiss_index is not None:
            index_ntotal = int(getattr(_faiss_index, "ntotal", 0))
            index_dim = int(getattr(_faiss_index, "d", EMBED_DIM))
    except Exception:
        pass

    meta_rows = None
    try:
        if _meta_df is not None:
            meta_rows = int(len(_meta_df))
    except Exception:
        pass

    return {
        "faiss_imported": faiss is not None,
        "index_loaded": _faiss_index is not None,
        "index_ntotal": index_ntotal,
        "index_dim": index_dim,
        "meta_loaded": _meta_df is not None,
        "meta_rows": meta_rows,
    }

# --- Direct lookup by chunk_ids like "talk_id:chunk_index" -------------------
def get_chunks_by_ids(chunk_ids: List[str]) -> List[Dict]:
    """Return chunks matching explicit ids; empty if FAISS/meta not available."""
    _load_index_and_meta()
    if _meta_df is None:
        return []
    out: List[Dict] = []
    for cid in chunk_ids:
        try:
            talk_id, idx_str = cid.split(":")
            cidx = int(idx_str)
        except Exception:
            continue
        hit = _meta_df[
            (_meta_df["talk_id"] == talk_id) & (_meta_df["chunk_index"] == cidx)
        ]
        if len(hit) == 0:
            continue
        row = hit.iloc[0]
        out.append({
            "talk_id":        str(row.get("talk_id", "")),
            "archival_title": str(row.get("archival_title", "")),
            "recorded_date":  str(row.get("recorded_date", "")),
            "chunk_index":    int(row.get("chunk_index", 0)),
            "text":           str(row.get("text", "")),
            "token_estimate": int(row.get("token_estimate", 0)) if "token_estimate" in row else None,
            "sha256":         str(row.get("sha256", "")) if "sha256" in row else None,
        })
    return out

# Convenience for CLI testing
if __name__ == "__main__":  # pragma: no cover
    import json
    res = search_chunks("Future Human", top_k=8)
    print(json.dumps(res, indent=2))