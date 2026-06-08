"""
End-to-end RAG pipeline: retrieve → generate.

Import ask() from here for the Gradio UI and any other callers.
"""

from retrieve import get_retriever
from generate import generate

_retrieve = None


def _get_retrieve():
    global _retrieve
    if _retrieve is None:
        _retrieve = get_retriever(k=5)
    return _retrieve


def ask(question: str, where: dict | None = None) -> dict:
    """
    Full RAG pipeline for one question.

    Args:
      question: natural language question from the user
      where:    optional ChromaDB metadata filter (e.g. {"course": "CMSC131"})
                When None, semantic search across the full corpus.

    Returns:
      {
        "answer":  str,
        "sources": list[str],
        "chunks":  list[dict],   # raw retrieval results (for debugging)
        "model":   str,
        "chunks_used": int,
      }
    """
    retrieve = _get_retrieve()
    chunks = retrieve(question, where=where)
    result = generate(question, chunks)
    result["chunks"] = chunks
    return result
