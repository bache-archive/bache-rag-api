"""
rag/answer.py — Citation-grounded synthesis for the Bache Talks RAG

This module turns retrieved chunks into a short, multi-talk, citation-grounded answer.
It's LLM-free for now (deterministic stitching) but preserves the output shape so you can
swap in an LLM later without changing the API.

Contract:
    synthesize(query: str, chunk_ids: List[str]) -> Dict
Returns:
    {
      "answer": str,
      "citations": [
        {"talk_id": ..., "archival_title": ..., "recorded_date": ..., "chunk_index": ...},
        ...
      ]
    }
"""

from typing import List, Dict, Tuple, Optional
import itertools

# Demo-mode retrieval/lookup hooks
from rag.retrieve import _SAMPLE as DEMO_CHUNKS
from rag.retrieve import search_chunks as retrieve_search


# ----------------------------
# Helpers
# ----------------------------

def make_chunk_id(chunk: Dict) -> str:
    """Stable ID format used by the demo: '{talk_id}:{chunk_index}'."""
    return f"{chunk['talk_id']}:{chunk['chunk_index']}"


def index_demo_chunks() -> Dict[str, Dict]:
    """Build an in-memory ID -> chunk map from the demo sample."""
    return {make_chunk_id(c): c for c in DEMO_CHUNKS}


def dedupe_preserve_order(chunks: List[Dict]) -> List[Dict]:
    seen: set[Tuple[str, int]] = set()
    out: List[Dict] = []
    for c in chunks:
        key = (c["talk_id"], c["chunk_index"])
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def diversify_by_talk(chunks: List[Dict], per_talk_limit: int = 3) -> List[Dict]:
    """Limit the number of chunks per talk to improve cross-talk coverage."""
    buckets: Dict[str, List[Dict]] = {}
    for c in chunks:
        buckets.setdefault(c["talk_id"], []).append(c)
    diversified: List[Dict] = []
    for talk_id, lst in buckets.items():
        diversified.extend(lst[:per_talk_limit])
    return diversified


def format_citation_obj(c: Dict) -> Dict:
    return {
        "talk_id": c["talk_id"],
        "archival_title": c["archival_title"],
        "recorded_date": c["recorded_date"],
        "chunk_index": c["chunk_index"],
    }


def pick_citations(chunks: List[Dict], max_citations: int = 4) -> List[Dict]:
    """
    Prefer 1 per talk first (breadth), then fill remaining slots by rank.
    """
    if not chunks:
        return []

    # First pass: one per talk (preserving order)
    by_talk_first: List[Dict] = []
    seen_talks: set[str] = set()
    for c in chunks:
        if c["talk_id"] not in seen_talks:
            seen_talks.add(c["talk_id"])
            by_talk_first.append(c)

    citations: List[Dict] = [format_citation_obj(c) for c in by_talk_first[:max_citations]]

    # If we still have room, append more in original order (avoiding duplicates)
    if len(citations) < max_citations:
        chosen_keys = {(ct["talk_id"], ct["chunk_index"]) for ct in citations}
        for c in chunks:
            key = (c["talk_id"], c["chunk_index"])
            if key not in chosen_keys:
                citations.append(format_citation_obj(c))
                chosen_keys.add(key)
                if len(citations) >= max_citations:
                    break

    return citations


def simple_summarize(query: str, chunks: List[Dict], target_sentences: Tuple[int, int] = (2, 6)) -> str:
    """
    Deterministic, lightweight compositor (no LLM yet).
    Strategy:
      - Take 2–3 short excerpts from diversified top chunks.
      - Add connective tissue to read as a coherent paragraph.
      - Keep it crisp; avoid repetition.
    """
    if not chunks:
        return "No relevant passages were found in the public talks for this query. Try refining the topic or naming a talk or date."

    # Pull up to 3 short excerpts to avoid verbosity
    excerpts: List[str] = []
    for c in chunks[:3]:
        t = c["text"].strip()
        # Trim very long snippets to keep answer tight (~220 chars)
        if len(t) > 220:
            t = t[:217].rstrip() + "…"
        excerpts.append(t)

    # Compose
    lead = f"This summary draws on multiple public talks related to “{query}.”"
    body_parts: List[str] = []
    if excerpts:
        body_parts.append(excerpts[0])
    if len(excerpts) > 1:
        body_parts.append(excerpts[1])
    if len(excerpts) > 2:
        body_parts.append(excerpts[2])

    # Simple connective phrasing
    joined = " ".join(body_parts)
    conclusion = "Together these passages outline a coherent view across Bache’s talks."

    return " ".join([lead, joined, conclusion]).strip()


# ----------------------------
# Public API
# ----------------------------

def synthesize(query: str, chunk_ids: List[str]) -> Dict:
    """
    If chunk_ids are provided, look them up; otherwise perform a fresh search.
    Returns a concise answer with 2–4 citations when available.
    """
    # Resolve chunks
    chunks: List[Dict] = []
    if chunk_ids:
        # Demo lookup from in-memory sample
        id_index = index_demo_chunks()
        for cid in chunk_ids:
            c = id_index.get(cid)
            if c:
                chunks.append(c)
    else:
        # Auto-retrieve when no IDs are supplied
        chunks = retrieve_search(query, top_k=8)

    # Normalize: dedupe, diversify, cap to 8
    chunks = dedupe_preserve_order(chunks)
    chunks = diversify_by_talk(chunks, per_talk_limit=3)[:8]

    # Compose deterministic answer
    answer_text = simple_summarize(query, chunks)

    # Pick citations (aim for 2–4 if available)
    citations = pick_citations(chunks, max_citations=4)
    if len(citations) == 1 and len(chunks) > 1:
        # Nudge toward at least 2 citations when content allows
        extra = pick_citations(chunks[1:], max_citations=1)
        citations.extend(extra)

    return {
        "answer": answer_text,
        "citations": citations,
    }