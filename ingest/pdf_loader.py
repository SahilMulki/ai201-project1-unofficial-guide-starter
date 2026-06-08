"""
Loads PDF files from the documents/ folder using pdfplumber.
Each page becomes one document; the caller (chunker) splits them further.
Caches extracted text to documents/cache/.
"""

import re
import json
from pathlib import Path

CACHE_DIR = Path("documents/cache")
DOCS_DIR = Path("documents")


def _clean_page_text(text: str) -> str:
    """Remove PDF extraction artifacts while keeping substantive content."""
    # Collapse runs of whitespace / form-feed characters
    text = re.sub(r"\f", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Drop lines that are only numbers (page numbers)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    # Drop repeated header/footer boilerplate common in UMD PDFs
    text = re.sub(
        r"University of Maryland[^\n]*\n", "", text, flags=re.IGNORECASE
    )
    text = re.sub(r"Office of Undergraduate Studies[^\n]*\n", "", text, flags=re.IGNORECASE)
    # Collapse blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_pdf_documents(docs_dir: str = "documents") -> list[dict]:
    """
    Scans docs_dir for *.pdf files and returns one document dict per page:
      {"text": ..., "source": "pdf", "metadata": {"filename": ..., "page": ...}}

    Drop your PDF files into the documents/ folder before running.
    """
    try:
        import pdfplumber
    except ImportError:
        print("[PDF] pdfplumber not installed — run: pip install pdfplumber")
        return []

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "pdf_raw.json"

    if cache_file.exists():
        print("[PDF] Loading from cache...")
        with open(cache_file) as f:
            docs = json.load(f)
        print(f"[PDF] {len(docs)} page documents loaded from cache.")
        return docs

    pdf_files = list(Path(docs_dir).glob("*.pdf"))
    if not pdf_files:
        print(
            f"[PDF] No PDF files found in {docs_dir}/. "
            "Drop the Gen Ed PDF there and re-run."
        )
        return []

    documents = []
    for pdf_path in pdf_files:
        print(f"[PDF] Extracting: {pdf_path.name}...")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    raw = page.extract_text() or ""
                    cleaned = _clean_page_text(raw)
                    if len(cleaned) < 50:
                        continue
                    documents.append({
                        "text": cleaned,
                        "source": "pdf",
                        "metadata": {
                            "filename": pdf_path.name,
                            "page": page_num,
                            "url": str(pdf_path),
                        },
                    })
            print(f"  → {len(documents)} pages extracted so far")
        except Exception as e:
            print(f"  ✗ Failed to load {pdf_path.name}: {e}")

    with open(cache_file, "w") as f:
        json.dump(documents, f, indent=2)

    print(f"[PDF] Done. {len(documents)} page documents saved to cache.")
    return documents
