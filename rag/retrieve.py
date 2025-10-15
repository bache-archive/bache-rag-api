from typing import List, Dict

# Replace with your FAISS-backed search later. Keep the shape stable now.
_SAMPLE: List[Dict] = [
    {
        "talk_id": "2018-08-30-diamonds-from-heaven",
        "archival_title": "Diamonds from Heaven",
        "recorded_date": "2018-08-30",
        "chunk_index": 28,
        "text": "Diamond Luminosity is described as a blazing, clear light of unconditional love and knowing.",
        "token_estimate": 120,
        "sha256": "demo_sha256_not_real"
    }
]

def search_chunks(query: str, top_k: int = 8) -> List[Dict]:
    # TODO: wire to FAISS; return real chunks with the same keys.
    return _SAMPLE[: min(top_k, len(_SAMPLE))]