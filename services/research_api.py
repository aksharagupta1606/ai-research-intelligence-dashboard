from __future__ import annotations

import requests

from config.settings import OPENALEX_MAILTO
from utils.logger import logger

OPENALEX_URL = "https://api.openalex.org/works"


def search_openalex(query: str, limit: int = 10) -> list[dict]:
    if not query.strip():
        return []
    params = {"search": query.strip(), "per-page": min(max(limit, 1), 50), "select": "id,doi,title,publication_year,authorships,abstract_inverted_index,cited_by_count,primary_location"}
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO
    try:
        response = requests.get(OPENALEX_URL, params=params, timeout=12)
        response.raise_for_status()
        records = response.json().get("results", [])
    except (requests.RequestException, ValueError, TypeError):
        logger.warning("OpenAlex search failed; the local paper collection remains available.")
        raise RuntimeError("OpenAlex is temporarily unavailable. Search the demo collection instead.")
    return [_normalize_openalex(record) for record in records]


def _normalize_openalex(record: dict) -> dict:
    abstract = ""
    inverted = record.get("abstract_inverted_index") or {}
    if inverted:
        words = [""] * (max(position for positions in inverted.values() for position in positions) + 1)
        for word, positions in inverted.items():
            for position in positions:
                words[position] = word
        abstract = " ".join(words)
    authors = [
        item.get("author", {}).get("display_name", "")
        for item in record.get("authorships", [])
        if item.get("author", {}).get("display_name")
    ]
    location = record.get("primary_location") or {}
    source = location.get("source") or {}
    doi = (record.get("doi") or "").removeprefix("https://doi.org/")
    return {
        "title": record.get("title") or "Untitled research work",
        "abstract": abstract,
        "publication_year": record.get("publication_year"),
        "authors": authors,
        "journal": source.get("display_name", ""),
        "doi": doi or None,
        "url": record.get("doi") or record.get("id"),
        "citation_count": record.get("cited_by_count") or 0,
        "source": "OpenAlex",
    }