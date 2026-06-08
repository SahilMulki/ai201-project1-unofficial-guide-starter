"""
Token-aware chunker for the UMD Unofficial Guide RAG pipeline.

Uses the all-MiniLM-L6-v2 tokenizer so chunk boundaries are exact token counts.
The model's hard limit is 256 tokens; we target 200 with 40-token overlap so
each chunk fits with room for the [CLS]/[SEP] special tokens the model prepends.
"""

import uuid
from transformers import AutoTokenizer

TOKENIZER_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 200   # tokens (model max = 256, stay safely under)
CHUNK_OVERLAP = 40  # tokens

_tokenizer = None


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
    return _tokenizer


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping token-bounded chunks.
    Uses character-offset mapping so the original text (case, punctuation)
    is preserved exactly — no decode artifacts.
    """
    tok = _get_tokenizer()
    encoding = tok(
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
        truncation=False,
    )
    token_ids = encoding["input_ids"]
    offsets = encoding["offset_mapping"]  # (char_start, char_end) per token

    if len(token_ids) <= chunk_size:
        return [text.strip()]

    chunks = []
    start = 0
    while start < len(token_ids):
        end = min(start + chunk_size, len(token_ids))

        char_start = offsets[start][0]
        char_end = offsets[end - 1][1]
        chunk_str = text[char_start:char_end].strip()

        if chunk_str:
            chunks.append(chunk_str)
        if end == len(token_ids):
            break
        start += chunk_size - overlap

    return chunks


def chunk_documents(
    documents: list[dict],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """
    Convert a list of raw documents into a flat list of chunk dicts.

    Each chunk dict:
      {
        "id":           str (UUID),
        "text":         str,
        "source":       str,
        "chunk_index":  int,
        "total_chunks": int,
        "metadata":     dict,
      }
    """
    print(f"Chunking {len(documents)} documents "
          f"(chunk_size={chunk_size}, overlap={overlap})...")

    chunks = []
    for doc in documents:
        text = (doc.get("text") or "").strip()
        if not text:
            continue

        text_chunks = chunk_text(text, chunk_size, overlap)

        for i, chunk_str in enumerate(text_chunks):
            if len(chunk_str) < 20:
                continue
            chunks.append({
                "id": str(uuid.uuid4()),
                "text": chunk_str,
                "source": doc.get("source", "unknown"),
                "chunk_index": i,
                "total_chunks": len(text_chunks),
                "metadata": doc.get("metadata", {}),
            })

    print(f"  → {len(chunks)} chunks produced from {len(documents)} documents.")
    return chunks
