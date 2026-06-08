"""
Milestone 5 — Grounded Generation

Wraps the Groq API to produce answers grounded strictly in retrieved chunks.
The system prompt forbids the model from using outside knowledge; source
attribution is enforced programmatically (not left to the model).

Usage (standalone test):
  python generate.py
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_CONTEXT_CHARS = 12_000   # hard cap to stay well within context window
MAX_TOKENS = 600

# ── System prompt — grounding is a hard rule, not a suggestion ───────────────

SYSTEM_PROMPT = """\
You are The Unofficial Guide, an assistant that helps University of Maryland \
(UMD) students find course and professor recommendations.

RULES — follow these exactly:
1. Answer ONLY using information from the DOCUMENTS section below.
2. Do NOT use your training knowledge, general facts, or outside sources.
3. If the documents do not contain enough information to answer the question, \
respond with exactly: "I don't have enough information on that."
4. When you cite specific facts (professor names, ratings, course details), \
reference them directly from the document text.
5. Be concise and direct. UMD students want actionable advice, not filler.
"""

USER_TEMPLATE = """\
DOCUMENTS:
{context}

---
QUESTION: {question}

Answer based only on the documents above. Do not invent any information not \
present in the documents."""


def _build_context(chunks: list[dict], max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Format retrieved chunks into a numbered context block.
    Truncates at max_chars to prevent context overflow.
    """
    parts = []
    total = 0
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = chunk.get("source", "")

        if source == "planetterp":
            tag = (f"[Doc {i} | PlanetTerp | "
                   f"prof={meta.get('professor', '?')} "
                   f"course={meta.get('course', '?')} "
                   f"rating={meta.get('rating', '?')}/5]")
        elif source == "pdf":
            tag = (f"[Doc {i} | PDF | "
                   f"file={meta.get('filename', '?')} "
                   f"page={meta.get('page', '?')}]")
        else:
            tag = f"[Doc {i}]"

        block = f"{tag}\n{chunk['text']}"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)

    return "\n\n".join(parts)


def _build_sources(chunks: list[dict]) -> list[str]:
    """
    Build a deduplicated list of human-readable source strings.
    This is appended programmatically — not left to the LLM.
    """
    seen = set()
    sources = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        source = chunk.get("source", "")
        if source == "planetterp":
            prof = meta.get("professor", "")
            course = meta.get("course", "")
            url = meta.get("url", "")
            label = f"PlanetTerp — {prof}"
            if course:
                label += f" / {course}"
            if url:
                label += f"  ({url})"
        elif source == "pdf":
            label = (f"PDF — {meta.get('filename', 'umd_gen_ed_reqs.pdf')} "
                     f"p.{meta.get('page', '?')}")
        else:
            label = source

        if label not in seen:
            seen.add(label)
            sources.append(label)

    return sources


def generate(question: str, chunks: list[dict]) -> dict:
    """
    Call Groq with the retrieved chunks as grounding context.

    Returns:
      {
        "answer":  str,          # LLM-generated, grounded answer
        "sources": list[str],    # programmatic source attribution
        "model":   str,
        "chunks_used": int,
      }
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    context = _build_context(chunks)
    user_message = USER_TEMPLATE.format(context=context, question=question)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.2,    # low temp for factual grounding; less hallucination
    )

    answer = response.choices[0].message.content.strip()
    sources = _build_sources(chunks)

    return {
        "answer":      answer,
        "sources":     sources,
        "model":       GROQ_MODEL,
        "chunks_used": len(chunks),
    }


# ── Standalone grounding test ────────────────────────────────────────────────

if __name__ == "__main__":
    import textwrap
    from retrieve import get_retriever

    retrieve = get_retriever(k=5)

    test_cases = [
        {
            "question": "Who is the most recommended professor for CMSC131?",
            "where": {"course": "CMSC131"},
        },
        {
            "question": "What Distributive Studies Gen Ed categories must UMD undergrads complete?",
            "where": None,
        },
        {
            # Grounding failure test: answer must be "I don't have enough information"
            "question": "What is the average rent near the UMD campus?",
            "where": None,
        },
    ]

    for tc in test_cases:
        print("\n" + "=" * 72)
        print(f"Q: {tc['question']}")
        chunks = retrieve(tc["question"], where=tc.get("where"))
        result = generate(tc["question"], chunks)
        print(f"\nA ({result['model']}, {result['chunks_used']} chunks):")
        print(textwrap.fill(result["answer"], width=70))
        print("\nSources:")
        for s in result["sources"]:
            print(f"  • {s}")
        print("=" * 72)
