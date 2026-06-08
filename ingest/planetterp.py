"""
Fetches professor reviews and course grade data from the PlanetTerp API.
Caches raw results to documents/cache/ so re-runs don't re-hit the API.
"""

import time
import json
import requests
from pathlib import Path

BASE_URL = "https://planetterp.com/api/v1"
CACHE_DIR = Path("documents/cache")
HEADERS = {"User-Agent": "UMD-Unofficial-Guide/1.0 (educational RAG project)"}


def _get(endpoint: str, params: dict | None = None) -> list | dict | None:
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == 2:
                print(f"    API error for {url} {params}: {e}")
                return None
            time.sleep(2 ** attempt)
    return None


def _fetch_all_professors(limit_total: int = 500) -> list[dict]:
    """Paginate through /professors to get the full list."""
    professors = []
    offset = 0
    batch = 100
    while len(professors) < limit_total:
        page = _get("professors", {"limit": batch, "offset": offset})
        if not page:
            break
        professors.extend(page)
        if len(page) < batch:
            break
        offset += batch
        time.sleep(0.4)
    return professors[:limit_total]


def _format_review(prof_name: str, review: dict) -> str:
    """Produce a self-contained, searchable text blob for one review."""
    course = review.get("course") or ""
    rating = review.get("rating")
    text = (review.get("review") or "").strip()
    expected = review.get("expected_grade") or ""
    received = review.get("grade") or ""

    header_parts = [f"Professor {prof_name}"]
    if course:
        header_parts.append(f"for {course}")
    if rating is not None:
        header_parts.append(f"(Rating: {rating}/5)")
    header = " ".join(header_parts) + ":"

    grade_note = ""
    if expected or received:
        parts = []
        if expected:
            parts.append(f"expected {expected}")
        if received:
            parts.append(f"received {received}")
        grade_note = f" [Student {', '.join(parts)}]"

    return f"{header} {text}{grade_note}"


def load_planetterp_documents(max_professors: int = 500) -> list[dict]:
    """
    Returns a list of document dicts, one per review:
      {"text": ..., "source": "planetterp", "metadata": {...}}
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "planetterp_raw.json"

    if cache_file.exists():
        print("[PlanetTerp] Loading from cache...")
        with open(cache_file) as f:
            docs = json.load(f)
        print(f"[PlanetTerp] {len(docs)} review documents loaded from cache.")
        return docs

    print(f"[PlanetTerp] Fetching up to {max_professors} professors...")
    professors = _fetch_all_professors(max_professors)
    print(f"[PlanetTerp] Got {len(professors)} professors. Fetching reviews...")

    documents = []
    for i, prof in enumerate(professors):
        name = (prof.get("name") or "").strip()
        if not name:
            continue

        data = _get("professor", {"name": name, "reviews": "true"})
        if not data:
            continue

        slug = data.get("slug") or ""
        prof_type = data.get("type") or ""
        reviews = data.get("reviews") or []

        for review in reviews:
            text = (review.get("review") or "").strip()
            if len(text) < 25:
                continue
            documents.append({
                "text": _format_review(name, review),
                "source": "planetterp",
                "metadata": {
                    "professor": name,
                    "slug": slug,
                    "type": prof_type,
                    "course": review.get("course") or "",
                    "rating": review.get("rating"),
                    "expected_grade": review.get("expected_grade") or "",
                    "grade": review.get("grade") or "",
                    "created": review.get("created") or "",
                    "url": f"https://planetterp.com/professor/{slug}",
                },
            })

        if i % 25 == 0:
            print(f"  {i}/{len(professors)} professors processed, "
                  f"{len(documents)} reviews so far")
        time.sleep(0.3)

    with open(cache_file, "w") as f:
        json.dump(documents, f, indent=2)

    print(f"[PlanetTerp] Done. {len(documents)} review documents saved to cache.")
    return documents
