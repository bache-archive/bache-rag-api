from typing import List, Dict

def synthesize(query: str, chunk_ids: List[str]) -> Dict:
    # TODO: call your real composer; keep the response fields stable
    return {
        "answer": "Concise, citation-grounded summary (demo).",
        "citations": [
            {
                "talk_id": "2018-08-30-diamonds-from-heaven",
                "archival_title": "Diamonds from Heaven",
                "recorded_date": "2018-08-30",
                "chunk_index": 28
            }
        ]
    }