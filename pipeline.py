"""
Milestone 3 — Document Ingestion + Chunking Pipeline

Usage:
  python pipeline.py              # run ingestion + chunking, save chunks.json
  python pipeline.py --clear      # delete cache and re-fetch everything

Output:
  documents/chunks.json           # flat list of chunk dicts for Milestone 4
"""

import sys
import json
import textwrap
from pathlib import Path

from ingest.planetterp import load_planetterp_documents
from ingest.pdf_loader import load_pdf_documents
from chunker import chunk_documents, CHUNK_SIZE, CHUNK_OVERLAP

CHUNKS_PATH = Path("documents/chunks.json")
CACHE_DIR = Path("documents/cache")


def clear_cache():
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
        print(f"Deleted cache: {f}")


def print_sample_chunk(chunks: list[dict], source_filter: str | None = None):
    """Print one chunk so you can eyeball cleaning quality."""
    candidates = [c for c in chunks if not source_filter or c["source"] == source_filter]
    if not candidates:
        print(f"No chunks found for source: {source_filter}")
        return

    sample = candidates[len(candidates) // 3]
    print("\n" + "=" * 70)
    print(f"SAMPLE CHUNK [{source_filter or 'all'}]")
    print("=" * 70)
    print(f"  id          : {sample['id']}")
    print(f"  source      : {sample['source']}")
    print(f"  chunk_index : {sample['chunk_index']} / {sample['total_chunks'] - 1}")
    print(f"  metadata    : {sample['metadata']}")
    print()
    print(textwrap.fill(sample["text"], width=70))
    print("=" * 70)


def print_stats(chunks: list[dict]):
    from collections import Counter
    sources = Counter(c["source"] for c in chunks)
    print("\n--- Chunk stats ---")
    for src, count in sources.most_common():
        print(f"  {src:<15} {count:>6} chunks")
    print(f"  {'TOTAL':<15} {len(chunks):>6} chunks")

    lengths = [len(c["text"].split()) for c in chunks]
    avg = sum(lengths) / len(lengths) if lengths else 0
    print(f"\n  Avg chunk word count : {avg:.0f}")
    print(f"  Min / Max            : {min(lengths)} / {max(lengths)}")


def run():
    if "--clear" in sys.argv:
        clear_cache()

    print("\n=== Stage 1: Document Ingestion ===\n")
    documents = []

    pt_docs = load_planetterp_documents(max_professors=500)
    documents.extend(pt_docs)

    pdf_docs = load_pdf_documents("documents")
    documents.extend(pdf_docs)

    print(f"\nTotal raw documents: {len(documents)}\n")

    print("=== Stage 2: Chunking ===\n")
    chunks = chunk_documents(documents, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_PATH, "w") as f:
        json.dump(chunks, f, indent=2)
    print(f"\nChunks saved to {CHUNKS_PATH}")

    print_stats(chunks)
    print_sample_chunk(chunks, source_filter="planetterp")
    print_sample_chunk(chunks, source_filter="pdf")

    print(
        "\n✓ Pipeline complete. Review the sample chunks above.\n"
        "  If you see nav text, HTML entities, or off-topic content,\n"
        "  delete documents/cache/ and fix the cleaner before continuing.\n"
    )


if __name__ == "__main__":
    run()
