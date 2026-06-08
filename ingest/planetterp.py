"""
Fetches professor reviews from the PlanetTerp API two ways:
  1. Professor-based: first N professors (alphabetical) + their reviews
  2. Course-based: targeted fetch for high-priority courses so we don't
     miss popular courses whose professors fall later alphabetically

Caches raw results to documents/cache/.
"""

import time
import json
import requests
from pathlib import Path

BASE_URL = "https://planetterp.com/api/v1"
CACHE_DIR = Path("documents/cache")
HEADERS = {"User-Agent": "UMD-Unofficial-Guide/1.0 (educational RAG project)"}

# Courses to explicitly fetch regardless of professor ordering.
# These cover the most-searched intro, CS, premed, and gen-ed areas.
PRIORITY_COURSES = [
    # CS core
    "CMSC131", "CMSC132", "CMSC216", "CMSC250", "CMSC330", "CMSC351",
    "CMSC411", "CMSC412", "CMSC414", "CMSC417", "CMSC420", "CMSC421",
    "CMSC422", "CMSC423", "CMSC424", "CMSC430", "CMSC433", "CMSC436",
    # Math / Stats
    "MATH140", "MATH141", "MATH241", "MATH246", "STAT400",
    # Premed sciences
    "BSCI105", "BSCI106", "CHEM131", "CHEM135", "CHEM231", "CHEM271",
    "PHYS161", "PHYS260", "PHYS261", "BCHM461",
    # Popular gen-ed
    "ENGL101", "PSYC100", "ECON200", "ECON201",
]


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


def _docs_from_professor_data(name: str, data: dict) -> list[dict]:
    """Convert one professor's API response into document dicts."""
    slug = data.get("slug") or ""
    prof_type = data.get("type") or ""
    docs = []
    for review in (data.get("reviews") or []):
        text = (review.get("review") or "").strip()
        if len(text) < 25:
            continue
        docs.append({
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
    return docs


def _fetch_priority_course_docs() -> list[dict]:
    """
    Fetch reviews from the /course endpoint for each priority course.
    Returns documents in the same format as professor-based fetching.
    """
    docs = []
    for course_name in PRIORITY_COURSES:
        data = _get("course", {"name": course_name, "reviews": "true"})
        if not data:
            continue
        reviews = data.get("reviews") or []
        for review in reviews:
            text = (review.get("review") or "").strip()
            prof_name = review.get("professor") or "Unknown Professor"
            if len(text) < 25:
                continue
            docs.append({
                "text": _format_review(prof_name, review),
                "source": "planetterp",
                "metadata": {
                    "professor": prof_name,
                    "slug": "",
                    "type": "professor",
                    "course": course_name,
                    "rating": review.get("rating"),
                    "expected_grade": review.get("expected_grade") or "",
                    "grade": review.get("grade") or "",
                    "created": review.get("created") or "",
                    "url": f"https://planetterp.com/course/{course_name}",
                },
            })
        print(f"  {course_name}: {len(reviews)} reviews")
        time.sleep(0.3)
    return docs


def load_planetterp_documents(max_professors: int = 500) -> list[dict]:
    """
    Returns a deduplicated list of document dicts, one per review.
    Combines professor-based and course-based fetching.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "planetterp_raw.json"

    if cache_file.exists():
        print("[PlanetTerp] Loading from cache...")
        with open(cache_file) as f:
            docs = json.load(f)
        print(f"[PlanetTerp] {len(docs)} review documents loaded from cache.")
        return docs

    all_docs: list[dict] = []
    seen_texts: set[str] = set()  # dedup key: first 120 chars of review text

    def _add(docs: list[dict]):
        for doc in docs:
            key = doc["text"][:120]
            if key not in seen_texts:
                seen_texts.add(key)
                all_docs.append(doc)

    # ── 1. Professor-based (first N alphabetically) ──────────────────────
    print(f"[PlanetTerp] Fetching up to {max_professors} professors...")
    professors = _fetch_all_professors(max_professors)
    print(f"[PlanetTerp] Got {len(professors)} professors. Fetching reviews...")

    for i, prof in enumerate(professors):
        name = (prof.get("name") or "").strip()
        if not name:
            continue
        data = _get("professor", {"name": name, "reviews": "true"})
        if not data:
            continue
        _add(_docs_from_professor_data(name, data))
        if i % 25 == 0:
            print(f"  {i}/{len(professors)} professors, {len(all_docs)} reviews so far")
        time.sleep(0.3)

    print(f"[PlanetTerp] Professor-based: {len(all_docs)} reviews")

    # ── 2. Course-based (priority courses, fills gaps) ───────────────────
    print(f"[PlanetTerp] Fetching {len(PRIORITY_COURSES)} priority courses...")
    course_docs = _fetch_priority_course_docs()
    before = len(all_docs)
    _add(course_docs)
    print(f"[PlanetTerp] Course-based: +{len(all_docs) - before} new reviews "
          f"({len(course_docs)} fetched, duplicates dropped)")

    with open(cache_file, "w") as f:
        json.dump(all_docs, f, indent=2)

    print(f"[PlanetTerp] Done. {len(all_docs)} review documents saved to cache.")
    return all_docs
