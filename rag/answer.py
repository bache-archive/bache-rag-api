"""
rag/answer.py — Citation-grounded synthesis for Bache Talks RAG

- Uses OpenAI (if OPENAI_API_KEY is set) to write a 2–5 sentence answer
  grounded ONLY in retrieved transcript snippets.
- Falls back to a compact extractive summary when no API key or model is available.
- Returns structured citations matching the chunks actually used.

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

from typing import List, Dict
import os
import re

# Retrieval hooks
from rag.retrieve import search_chunks

# Optional: direct lookup by "talk_id:chunk_index" if your retrieve.py exposes it.
try:
    from rag.retrieve import get_chunks_by_ids  # type: ignore
except Exception:
    def get_chunks_by_ids(chunk_ids: List[str]) -> List[Dict]:
        # Graceful fallback if helper isn't present
        return []

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
# Tunables
# ----------------------------
MAX_CHUNKS_FOR_SYNTH = 6   # smaller context → crisper answers
MAX_SNIPPET_CHARS   = 750  # trim each snippet before sending to the LLM


def _trim_to_sentence(s: str, limit: int) -> str:
    s = (s or "").strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    # try to end on a sentence boundary
    # reverse search for punctuation near the end
    rev = cut[::-1]
    m = re.search(r"(?s)[.!?](?:\"|')?\s", rev)
    if m:
        end = len(cut) - m.start()
        return s[:end].strip()
    return cut.rstrip(" ,;—") + "…"


def _format_context(chunks: List[Dict]) -> str:
    lines = []
    for c in chunks[:MAX_CHUNKS_FOR_SYNTH]:
        head = f"[{c.get('recorded_date') or 'UNKNOWN'}, {c.get('archival_title','')}, chunk {c.get('chunk_index',0)}]"
        text = _trim_to_sentence(c.get("text", ""), MAX_SNIPPET_CHARS)
        lines.append(f"{head}\n{text}")
    return "\n\n".join(lines)


def _citations_from_chunks(chunks: List[Dict]) -> List[Dict]:
    cites = []
    for c in chunks[:MAX_CHUNKS_FOR_SYNTH]:
        cites.append({
            "talk_id":        c.get("talk_id", ""),
            "archival_title": c.get("archival_title", ""),
            "recorded_date":  c.get("recorded_date", ""),
            "chunk_index":    int(c.get("chunk_index", 0)),
        })
    return cites


def _llm_answer(query: str, chunks: List[Dict]) -> str:
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


def _extractive_fallback(chunks: List[Dict], query: str) -> str:
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


def synthesize(query: str, chunk_ids: List[str]) -> Dict:
    """
    If chunk_ids are provided, look them up; otherwise retrieve automatically.
    Always returns {'answer': str, 'citations': [...] }.
    """
    chunks = get_chunks_by_ids(chunk_ids) if chunk_ids else search_chunks(query, top_k=8)

    if not chunks:
        return {
            "answer": "No relevant passages were found in the public talks archive for this query.",
            "citations": [],
        }

    # Try the LLM first; if unavailable, fall back to extractive
    answer = _llm_answer(query, chunks) or _extractive_fallback(chunks, query)
    citations = _citations_from_chunks(chunks)
    return {"answer": answer, "citations": citations}