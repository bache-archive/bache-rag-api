#!/usr/bin/env python3
"""
rag/answer.py — Citation-grounded synthesis for Bache Talks RAG

- Uses OpenAI (if OPENAI_API_KEY is set) to write a 2–5 sentence answer
  grounded ONLY in retrieved transcript snippets.
- Falls back to a compact extractive summary when no API key or model is available.
- Returns structured citations matching the chunks actually used, plus a human-readable
  "sources_text" block that prints the new citation strings.

Contract:
    synthesize(query: str, chunk_ids: List[str]) -> Dict
Returns:
    {
      "answer": str,
      "citations": [
        {
          "talk_id": ...,
          "archival_title": ...,
          "recorded_date": ...,
          "chunk_index": ...,
          "citation": ...,          # human-readable label
          "url": ...                # optional
        },
        ...
      ],
      "sources_text": "— Bache · 2021-04-21 · ATTMind Podcast · ... · chunk 12 · https://..."
    }
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import os
import re

from dotenv import load_dotenv
load_dotenv()

# Retrieval (new class-based retriever)
from rag.retrieve import Retriever

# ----------------------------
# Optional OpenAI client
# ----------------------------
_OPENAI_KEY = os.getenv("OPENAI_API_KEY")
_MODEL = os.getenv("ANSWERS_MODEL", "gpt-4o-mini")  # small, fast; change if you like

_openai_client = None
if _OPENAI_KEY:
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=_OPENAI_KEY)
    except Exception:
        _openai_client = None

# ----------------------------
# Global retriever instance
# ----------------------------
# You can override paths/model via env vars if needed.
_RETRIEVER = Retriever(
    parquet_path=os.getenv("METADATA_PATH", "vectors/bache-talks.embeddings.parquet"),
    faiss_path=os.getenv("FAISS_INDEX_PATH", "vectors/bache-talks.index.faiss"),
    model=os.getenv("EMBED_MODEL", "text-embedding-3-large"),
    per_talk_cap=int(os.getenv("MAX_PER_TALK", "2")),
    top_k_default=8,
)

# ----------------------------
# Tunables
# ----------------------------
MAX_CHUNKS_FOR_SYNTH = 6   # smaller context → crisper answers
MAX_SNIPPET_CHARS   = 750  # trim each snippet before sending to the LLM


# ----------------------------
# Helpers
# ----------------------------

def _trim_to_sentence(s: str, limit: int) -> str:
    s = (s or "").strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    # try to end on a sentence boundary near the end
    # reverse search for punctuation near the end
    rev = cut[::-1]
    m = re.search(r"(?s)[.!?](?:\"|')?\s", rev)
    if m:
        end = len(cut) - m.start()
        return s[:end].strip()
    return cut.rstrip(" ,;—") + "…"


def _format_context(chunks: List[Dict[str, Any]]) -> str:
    """Label each snippet with readable header for the LLM prompt."""
    lines = []
    for c in chunks[:MAX_CHUNKS_FOR_SYNTH]:
        # Prefer published date if present
        date = c.get("recorded_date") or c.get("published") or "UNKNOWN"
        title = c.get("archival_title", "") or ""
        head = f"[{date}, {title}, chunk {c.get('chunk_index', 0)}]"
        text = _trim_to_sentence(c.get("text", ""), MAX_SNIPPET_CHARS)
        lines.append(f"{head}\n{text}")
    return "\n\n".join(lines)


def _citations_from_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cites: List[Dict[str, Any]] = []
    for c in chunks[:MAX_CHUNKS_FOR_SYNTH]:
        cites.append({
            "talk_id":        c.get("talk_id", ""),
            "archival_title": c.get("archival_title", ""),
            "recorded_date":  c.get("recorded_date", "") or c.get("published", ""),
            "chunk_index":    int(c.get("chunk_index", 0)),
            "citation":       c.get("citation", ""),   # human-readable label
            "url":            c.get("url", None),
        })
    return cites


def _format_sources(chunks: List[Dict[str, Any]]) -> str:
    """
    Human-readable 'Sources' block using the new 'citation' label.
    Example line:
      — Bache · 2021-04-21 · ATTMind Podcast · Future Human and Global Collapse · chunk 12 · https://youtu.be/...
    """
    lines = []
    for c in chunks[:MAX_CHUNKS_FOR_SYNTH]:
        cit = c.get("citation") or c.get("transcript_path") or "unknown"
        url = c.get("url")
        chunk = c.get("chunk_index")
        if url:
            lines.append(f"— {cit} · chunk {chunk} · {url}")
        else:
            lines.append(f"— {cit} · chunk {chunk}")
    return "\n".join(lines)


def _llm_answer(query: str, chunks: List[Dict[str, Any]]) -> str:
    """Generate a short, citation-grounded answer with OpenAI. Returns '' on failure."""
    if _openai_client is None:
        return ""
    system = (
        "You are the librarian of the Chris Bache public talks archive. "
        "Answer ONLY from the provided transcript snippets. Do NOT invent any facts. "
        "Write 2–5 concise sentences in a neutral, precise tone. "
        "Do not include bracketed references like [1]; citations are returned separately."
    )
    user = (
        f"Question: {query}\n\n"
        f"Snippets (each labeled with date/title/chunk):\n\n{_format_context(chunks)}\n\n"
        "Write a 2–5 sentence answer grounded ONLY in the snippets above."
    )
    try:
        resp = _openai_client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return ""


def _extractive_fallback(chunks: List[Dict[str, Any]], query: str) -> str:
    """No OpenAI or failure → compact extractive synthesis."""
    snippets: List[str] = []
    for c in chunks[:MAX_CHUNKS_FOR_SYNTH]:
        t = _trim_to_sentence(c.get("text", ""), 280)
        if t:
            snippets.append(t)
    if not snippets:
        return "No relevant passages were found in the public talks archive for this query."
    # Keep it to ~3 sentences max
    return " ".join(snippets[:3]).rstrip(" ,;—") + "."


# ----------------------------
# Retrieval glue
# ----------------------------

def search_chunks(query: str, top_k: int = 8, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Compatibility wrapper for earlier code that expected a function."""
    return _RETRIEVER.search(query=query, k=top_k, filters=filters)

def get_chunks_by_ids(chunk_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Best-effort lookup for explicit IDs.
    Supports:
      - numeric ids (Parquet/FAISS 'id')
      - 'talk_id:chunk_index' strings, e.g. '2018-08-30-timewaver:12'
    """
    if not chunk_ids:
        return []

    rows: List[Dict[str, Any]] = []
    df = _RETRIEVER.df           # positional access
    df_by_id = _RETRIEVER.df_by_id  # id-based access

    for cid in chunk_ids:
        cid = str(cid).strip()
        got = None

        # Numeric id?
        if cid.isdigit():
            try:
                row = df_by_id.loc[int(cid)]
                got = row.to_dict()
            except Exception:
                pass

        # talk_id:chunk_index?
        if got is None and ":" in cid:
            try:
                talk_id, chunk_str = cid.split(":", 1)
                chunk_idx = int(chunk_str)
                match = df[(df["talk_id"] == talk_id) & (df["chunk_index"] == chunk_idx)]
                if not match.empty:
                    got = match.iloc[0].to_dict()
            except Exception:
                pass

        if got is not None:
            rows.append(got)

    # If none matched, return empty; caller will fall back to search
    return rows


# ----------------------------
# Main API
# ----------------------------

def synthesize(query: str, chunk_ids: List[str]) -> Dict[str, Any]:
    """
    If chunk_ids are provided, look them up; otherwise retrieve automatically.
    Always returns {'answer': str, 'citations': [...], 'sources_text': str }.
    """
    chunks = get_chunks_by_ids(chunk_ids) if chunk_ids else search_chunks(query, top_k=8)

    if not chunks:
        return {
            "answer": "No relevant passages were found in the public talks archive for this query.",
            "citations": [],
            "sources_text": "",
        }

    # Try the LLM first; if unavailable, fall back to extractive
    answer = _llm_answer(query, chunks) or _extractive_fallback(chunks, query)

    citations = _citations_from_chunks(chunks)
    sources_text = _format_sources(chunks)

    return {
        "answer": answer,
        "citations": citations,
        "sources_text": sources_text,
    }


# ---------- Manual test ----------
if __name__ == "__main__":
    out = synthesize("What is Diamond Luminosity?", chunk_ids=[])
    print(out["answer"], end="\n\n")
    print("Sources:\n" + out["sources_text"])