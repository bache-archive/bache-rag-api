#!/usr/bin/env python3
"""
rag/answer.py

Render a short, citation-grounded synthesis without exposing internal "chunk" ids.
- Inline cites: "(YYYY-MM-DD, Title[, [hh:mm:ss–hh:mm:ss](...link...)])"
- Sources: bullet list, timestamped links when available; never show "chunk N".
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional

# ---------- helpers ----------

def _safe_str(v) -> str:
    return "" if v is None else str(v)

def _trim(s: str, limit: int = 500) -> str:
    s = (s or "").strip()
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0]
    return (cut or s[:limit]) + "…"

def _human_date(row: Dict) -> str:
    # prefer published → date → recorded_date (already normalized upstream)
    for k in ("published", "date", "recorded_date"):
        val = row.get(k)
        if val:
            return str(val)
    return ""

def _ts_url(row: Dict) -> Optional[str]:
    """
    Prefer precomputed ts_url if present; else compute if we have youtube_id & start_sec;
    else fall back to plain url; else None.
    """
    if row.get("ts_url"):
        return row["ts_url"]
    yt = row.get("youtube_id")
    ss = row.get("start_sec")
    if yt and ss is not None:
        try:
            t = int(max(0, float(ss)))
            return f"https://youtu.be/{yt}?t={t}"
        except Exception:
            return None
    return row.get("url") or None

def _ts_bracket(row: Dict) -> str:
    """
    Return markdown like: [00:54:17–00:54:44](https://youtu.be/ID?t=3257)
    If we only have a start time, show just [00:54:17](...).
    If no timing/link, return "".
    """
    start = row.get("start_hhmmss")
    end = row.get("end_hhmmss")
    link = _ts_url(row)
    if not start or not link:
        return ""
    label = start if not end else f"{start}–{end}"
    return f"[{label}]({link})"

def _human_title(row: Dict) -> str:
    # Prefer archival_title, then citation, then talk_id
    return _safe_str(row.get("archival_title") or row.get("citation") or row.get("talk_id"))

def _human_label(row: Dict, include_ts: bool = True) -> str:
    """
    "YYYY-MM-DD, Title" plus optional timestamp bracket.
    NEVER includes 'chunk'.
    """
    date = _human_date(row)
    title = _human_title(row)
    base = ", ".join([p for p in (date, title) if p])
    if include_ts:
        ts = _ts_bracket(row)
        return f"{base}, {ts}" if ts else base
    return base

def _inline_cite(row: Dict) -> str:
    """
    Human-friendly inline cite with NO chunk number.
    Examples:
      "(2023-01-06, LSD and the Mind of the Universe – S2S Podcast, [00:54:17–00:54:44](...))"
      "(2022-08-30, Psychedelics and Cosmological Exploration with Chris Bache – Reach Truth Podcast)"
    """
    return f"({_human_label(row, include_ts=True)})"

def _dedupe_sources(hits: List[Dict]) -> List[Dict]:
    """
    De-duplicate sources while preserving order.
    Key by (talk_id, start_hhmmss or url or archival_title) as a human-facing proxy.
    """
    seen: set[Tuple[str, str]] = set()
    out: List[Dict] = []
    for h in hits:
        talk = _safe_str(h.get("talk_id"))
        key2 = _safe_str(h.get("start_hhmmss") or h.get("url") or h.get("archival_title") or "")
        key = (talk, key2)
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out

def format_sources(hits: List[Dict], limit: int = 6) -> str:
    """
    Render a bullet list of sources with optional timestamped link.
    NO chunk numbers.
    """
    items: List[str] = []
    for h in _dedupe_sources(hits)[:limit]:
        date = _human_date(h)
        title = _human_title(h)
        ts = _ts_bracket(h)
        url = _ts_url(h) or ""
        if ts:
            items.append(f"— {date}, {title} · {ts}")
        else:
            items.append(f"— {date}, {title}" + (f" · {url}" if url else ""))
    return "\n".join(items)

# ---------- main entry ----------

def answer_from_chunks(query: str, hits: List[Dict], max_snippets: int = 3) -> str:
    """
    Compose a short QA response using the top hits:
      - includes inline timestamped brackets where available
      - uses human-readable citations (no chunk numbers)
    """
    if not hits:
        return "I don’t have sufficient context to answer. Try adding a date, venue, or specific term."

    top = hits[:max_snippets]
    snippets: List[str] = []
    for h in top:
        txt = _trim(h.get("text", ""), limit=500)
        cite = _inline_cite(h)  # includes timestamp bracket when available
        snippets.append(f"{txt} {cite}")

    synthesis = "Based on the archived talks, here are the most relevant passages:"
    body = " ".join(snippets)
    sources_block = format_sources(hits)

    return f"{synthesis} {body}\n\nSources:\n{sources_block}"