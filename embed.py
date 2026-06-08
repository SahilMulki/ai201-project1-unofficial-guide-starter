"""
Milestone 4 — Embedding + Vector Store

Reads documents/chunks.json, embeds every chunk with all-MiniLM-L6-v2,
and stores them in a persistent ChromaDB collection with full metadata.

Usage:
  python embed.py           # embed (skips if collection already populated)
  python embed.py --clear   # wipe collection and re-embed from scratch
"""

import sys
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = Path("documents/chunks.json")
CHROMA_DIR = Path("documents/chroma_db")
COLLECTION_NAME = "umd_guide"
MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_BATCH = 256   # chunks per encoding call


def _flatten_metadata(chunk: dict) -> dict:
    """
    ChromaDB metadata must be a flat dict of str/int/float/bool.
    Merge the top-level source fields with the nested metadata dict,
    converting None to "" so ChromaDB doesn't reject it.
    """
    flat = {
        "source": chunk.get("source", ""),
        "chunk_index": chunk.get("chunk_index", 0),
        "total_chunks": chunk.get("total_chunks", 1),
    }
    for k, v in chunk.get("metadata", {}).items():
        if v is None:
            flat[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            flat[k] = v
        else:
            flat[k] = str(v)
    return flat


def build_vector_store(clear: bool = False) -> chromadb.Collection:
    print(f"Loading chunks from {CHUNKS_PATH}...")
    with open(CHUNKS_PATH) as f:
        chunks = json.load(f)
    print(f"  {len(chunks)} chunks loaded.")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if clear:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"Deleted existing collection '{COLLECTION_NAME}'.")
        except Exception:
            pass

    # cosine distance so scores are in [0, 2]; lower = more similar
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    existing = collection.count()
    if existing > 0 and not clear:
        print(f"Collection already has {existing} embeddings — skipping re-embed.")
        print("Run with --clear to rebuild from scratch.")
        return collection

    print(f"\nLoading embedding model '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)

    texts = [c["text"] for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [_flatten_metadata(c) for c in chunks]

    print(f"Embedding {len(texts)} chunks in batches of {EMBED_BATCH}...")
    embeddings = model.encode(
        texts,
        batch_size=EMBED_BATCH,
        show_progress_bar=True,
        normalize_embeddings=True,  # required for cosine similarity via dot-product
    ).tolist()

    # ChromaDB add() is limited per call; chunk the upsert to avoid memory issues
    UPSERT_BATCH = 1000
    for start in range(0, len(chunks), UPSERT_BATCH):
        end = min(start + UPSERT_BATCH, len(chunks))
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=texts[start:end],
            metadatas=metadatas[start:end],
        )
        print(f"  Stored {end}/{len(chunks)} chunks in ChromaDB")

    print(f"\n✓ Vector store built: {collection.count()} embeddings in '{COLLECTION_NAME}'")
    return collection


if __name__ == "__main__":
    build_vector_store(clear="--clear" in sys.argv)
