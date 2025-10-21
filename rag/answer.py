#!/usr/bin/env python3
from typing import List, Dict, Tuple, Optional
import math

# -------- tiny utils --------

def _trim(s: str, limit: int = 500) -> str:
    s = (s or "").strip().replace("\n", " ")
    if len(s) <= limit:
        return s
    cut = s[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;—") + "…"

def _is_nan(x) -> bool:
    try:
        return isinstance(x, float) and math.isnan(x)
    except Exception:
        return False

def _fmt_hhmmss_from_sec(sec: Optional[float]) -> str:
    if sec is None or _is_nan(sec):
        return ""
    sec = int(max(0, round(float(sec))))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def _yt_url(youtube_id: Optional[str], start_sec: Optional[float]) -> str:
    if not youtube_id:
        return ""
    t = 0 if (start_sec is None or _is_nan(start_sec)) else int(max(0, round(float(start_sec))))
    return f"https://youtu.be/{youtube_id}?t={t}"

def _pick_date(row: Dict) -> str:
    # prefer recorded_date → published
    return (row.get("recorded_date") or row.get("published") or "").strip()

def _pick_title(row: Dict) -> str:
    return (row.get("archival_title") or row.get("title") or row.get("talk_id") or "").strip()

def _format_timecoded_citation(row: Dict) -> str:
    """
    Produce:
      (YYYY-MM-DD, Title, [HH:MM:SS–HH:MM:SS](https://youtu.be/<id>?t=<start>) [chunk N])
    Fallbacks cleanly if timing/url are missing.
    """
    date  = _pick_date(row)
    title = _pick_title(row)
    idx   = int(row.get("chunk_index", 0))

    yt_id   = (row.get("youtube_id") or "").strip()
    s_sec   = row.get("start_sec")
    e_sec   = row.get("end_sec")
    s_hms   = (row.get("start_hhmmss") or "").strip() or _fmt_hhmmss_from_sec(s_sec)
    e_hms   = (row.get("end_hhmmss") or "").strip()   or _fmt_hhmmss_from_sec(e_sec)

    # If we have a YouTube id and a start time (sec or hh:mm:ss), make it clickable
    if yt_id and (s_sec is not None and not _is_nan(s_sec) or s_hms):
        url = _yt_url(yt_id, s_sec)
        # If we lack end time, show only start
        if e_hms:
            label = f"{s_hms}–{e_hms}" if s_hms else e_hms
        else:
            label = s_hms or _fmt_hhmmss_from_sec(s_sec)
        time_md = f"[{label}]({url})"
        return f"({date}, {title}, {time_md} [chunk {idx}])"

    # No timing → fallback to original citation shape
    return f"({date}, {title}, [chunk {idx}])"

def _inline_cite(row: Dict) -> str:
    """
    Prefer the timecoded citation. If nothing available, fall back to (date, title, chunk N).
    """
    return _format_timecoded_citation(row)

# -------- Sources block formatting --------

def _source_line(row: Dict) -> str:
    """
    Render one source line with chunk index and a direct timecoded URL when possible.
    Example:
      — 2019-11-13, LSD & the Mind..., chunk 12 · https://youtu.be/<id>?t=903
    """
    date  = _pick_date(row)
    title = _pick_title(row)
    idx   = int(row.get("chunk_index", 0))

    yt_id = (row.get("youtube_id") or "").strip()
    s_sec = row.get("start_sec")
    # Either use stored URL (if provided) or synthesize a YouTube link with ?t=
    url = (row.get("url") or "").strip()
    if not url and yt_id and s_sec is not None and not _is_nan(s_sec):
        url = _yt_url(yt_id, s_sec)

    base = f"— {date}, {title} · chunk {idx}"
    if url:
        base += f" · {url}"
    return base

def format_sources(hits: List[Dict], max_sources: int = 6) -> str:
    """
    De-duplicate by (talk_id, chunk_index), preserve order, and include a timecoded URL if available.
    """
    seen = set()
    lines: List[str] = []
    for h in hits:
        key = (h.get("talk_id"), int(h.get("chunk_index", 0)))
        if key in seen:
            continue
        seen.add(key)
        lines.append(_source_line(h))
        if len(lines) >= max_sources:
            break
    return "\n".join(lines)

# -------- main composer --------

def answer_from_chunks(query: str, hits: List[Dict], max_snippets: int = 3) -> str:
    """
    Ultra-simple extractive composer:
      - picks up to `max_snippets` strongest chunks
      - returns a concise synthesis with an appended Sources block
      - uses *timecoded*, human-friendly citations when possible
    """
    if not hits:
        return "I don’t have sufficient context to answer. Try adding a date, venue, or specific term."

    # Take top N chunks as supporting snippets
    top = hits[:max_snippets]
    snippets: List[str] = []
    for h in top:
        txt = _trim(h.get("text", ""), limit=500)
        snippets.append(f"{txt} {_inline_cite(h)}")

    synthesis = "Based on the archived talks, here are the most relevant passages:"
    body = " ".join(snippets)

    # Sources block (de-duplicated, with direct timecoded links when available)
    sources_block = format_sources(hits)

    return f"{synthesis} {body}\n\nSources:\n{sources_block}"