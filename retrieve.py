"""
Milestone 4 — Retrieval

Provides get_retriever() which returns a retrieve(query, k) callable backed
by the ChromaDB collection built by embed.py.

Run as a script to test the 3 evaluation queries:
  python retrieve.py
"""

import textwrap
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = Path("documents/chroma_db")
COLLECTION_NAME = "umd_guide"
MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_K = 5


def get_retriever(k: int = DEFAULT_K):
    """
    Returns a retrieve(query, k=k) function bound to the ChromaDB collection.
    Call this once at startup; the returned function is cheap to call repeatedly.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    model = SentenceTransformer(MODEL_NAME)

    def retrieve(query: str, k: int = k, where: dict | None = None) -> list[dict]:
        """
        Embed query and return top-k chunks.

        Args:
          query: natural language question
          k:     number of results to return
          where: optional ChromaDB metadata filter, e.g. {"course": "CMSC131"}
                 Useful for course- or professor-specific queries.

        Each result dict:
          {
            "text":       str,
            "score":      float,   # cosine distance [0,2]; lower = more similar
            "similarity": float,   # 1 - score; higher = more similar
            "source":     str,
            "metadata":   dict,
          }
        """
        query_embedding = model.encode(
            query,
            normalize_embeddings=True,
        ).tolist()

        query_kwargs = dict(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "distances", "metadatas"],
        )
        if where:
            query_kwargs["where"] = where

        results = collection.query(**query_kwargs)

        hits = []
        for text, dist, meta in zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0],
        ):
            hits.append({
                "text": text,
                "score": round(dist, 4),         # cosine distance; lower = better
                "similarity": round(1 - dist, 4), # converted for readability
                "source": meta.get("source", ""),
                "metadata": meta,
            })
        return hits

    return retrieve


# ── Evaluation test ──────────────────────────────────────────────────────────

EVAL_QUERIES = [
    {
        "id": 1,
        "question": "Who is the most recommended professor for CMSC131?",
        "expected": "A highly-rated professor for CMSC131 (e.g. Nelson Padua-Perez or Fawzi Emad) with positive review text.",
        "where": {"course": "CMSC131"},   # course filter so we don't get CMSC330 reviews
    },
    {
        "id": 2,
        "question": "What do students say about CMSC351 Algorithms difficulty and average GPA?",
        "expected": "Reviews describing CMSC351 as challenging/weed-out, possibly mentioning low GPA or tough exams.",
        "where": {"course": "CMSC351"},
    },
    {
        "id": 3,
        "question": "What Distributive Studies Gen Ed categories must UMD undergrads complete?",
        "expected": "DSSP, DSHU, DSNS, DSNL, DSBS categories from the Gen Ed PDF.",
        "where": None,
    },
    {
        "id": 4,
        "question": "What do premed students recommend for biology or chemistry requirements at UMD?",
        "expected": "Advice about BSCI105/BIOL101 or chemistry sequences from student reviews.",
        "where": None,
    },
    {
        "id": 5,
        "question": "Which CMSC professors have the highest student ratings on PlanetTerp?",
        "expected": "Professors with rating 5/5 and strong positive reviews for CMSC courses.",
        "where": {"source": "planetterp"},
    },
]


def _print_results(query: dict, hits: list[dict]):
    print("\n" + "=" * 72)
    print(f"Query {query['id']}: {query['question']}")
    print(f"Expected: {query['expected']}")
    print("-" * 72)
    for i, hit in enumerate(hits, 1):
        source = hit["source"]
        meta = hit["metadata"]
        sim = hit["similarity"]
        dist = hit["score"]

        # Build a concise attribution line depending on source type
        if source == "planetterp":
            attr = (f"  [{i}] planetterp | prof={meta.get('professor','')} "
                    f"course={meta.get('course','')} "
                    f"rating={meta.get('rating','')} "
                    f"| similarity={sim:.3f} (dist={dist:.3f})")
        elif source == "pdf":
            attr = (f"  [{i}] pdf | file={meta.get('filename','')} "
                    f"page={meta.get('page','')} "
                    f"| similarity={sim:.3f} (dist={dist:.3f})")
        else:
            attr = f"  [{i}] {source} | similarity={sim:.3f} (dist={dist:.3f})"

        print(attr)
        # Wrap text at 70 chars, indented
        wrapped = textwrap.fill(hit["text"], width=68, initial_indent="      ",
                                subsequent_indent="      ")
        print(wrapped)
        print()

    # Quick relevance self-check
    best = hits[0]["similarity"] if hits else 0
    if best < 0.3:
        print("  ⚠  Best similarity < 0.30 — results may be off-topic.")
    elif best < 0.5:
        print("  ⚠  Best similarity < 0.50 — moderate match, review carefully.")
    else:
        print("  ✓  Best similarity ≥ 0.50 — looks like a strong match.")
    print("=" * 72)


def run_eval():
    if not CHROMA_DIR.exists():
        print("Vector store not found. Run:  python embed.py")
        return

    print("Loading retriever...")
    retrieve = get_retriever(k=DEFAULT_K)

    for query in EVAL_QUERIES:
        hits = retrieve(query["question"], where=query.get("where"))
        _print_results(query, hits)


if __name__ == "__main__":
    run_eval()
