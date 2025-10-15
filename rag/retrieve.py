"""
rag/retrieve.py — Semantic retrieval layer for the Bache Talks RAG

This module abstracts vector search and returns a balanced list of transcript chunks
ready for synthesis.  It currently uses a mock sample but preserves the same data shape
as the real FAISS-backed implementation.

Later, you can replace `perform_search()` with a call to your FAISS index.
"""

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Mock data (same schema as real chunks)
# ---------------------------------------------------------------------

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

# ---------------------------------------------------------------------
# Core retrieval
# ---------------------------------------------------------------------

def perform_search(query: str, top_k: int = 16) -> List[Dict]:
    """
    Placeholder for semantic search.  For now, returns mock data.
    Replace with FAISS cosine-similarity lookup later.
    """
    logger.debug(f"Mock search for query='{query}' (top_k={top_k})")
    return _SAMPLE[: min(top_k, len(_SAMPLE))]


def search_chunks(query: str, top_k: int = 8) -> List[Dict]:
    """
    Retrieve semantically similar transcript chunks for a natural-language query.

    - Uses FAISS (future) or mock list (current)
    - Diversifies results: ≤3 chunks per talk
    - Returns at most `top_k` total
    """
    raw_results = perform_search(query, top_k=top_k * 2)

    # Group by talk_id for diversity
    grouped: Dict[str, List[Dict]] = {}
    for r in raw_results:
        grouped.setdefault(r["talk_id"], []).append(r)

    # Limit 3 per talk, preserve order
    diversified: List[Dict] = []
    for talk_id, chunks in grouped.items():
        diversified.extend(chunks[:3])

    # Cap total to top_k
    diversified = diversified[:top_k]

    logger.debug(f"Returning {len(diversified)} chunks from {len(grouped)} talks")
    return diversified


# ---------------------------------------------------------------------
# Convenience for CLI testing
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import json
    res = search_chunks("Future Human", top_k=8)
    print(json.dumps(res, indent=2))