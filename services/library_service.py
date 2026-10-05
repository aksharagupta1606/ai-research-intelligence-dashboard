from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Author, Keyword, Paper, SavedPaper, Topic
from services.nlp_service import classify_topic, extract_keywords
from utils.text_utils import split_authors


def ingest_paper(session: Session, record: dict) -> tuple[Paper, bool]:
    title = (record.get("title") or "").strip()
    if not title:
        raise ValueError("A paper title is required.")
    doi = (record.get("doi") or "").strip() or None
    existing = session.scalar(select(Paper).where(Paper.doi == doi)) if doi else None
    if existing is None:
        existing = session.scalar(select(Paper).where(Paper.title == title))
    if existing:
        return existing, False

    paper = Paper(
        title=title[:500],
        abstract=record.get("abstract") or "",
        publication_year=record.get("publication_year"),
        journal=record.get("journal") or "",
        doi=doi,
        url=record.get("url"),
        citation_count=int(record.get("citation_count") or 0),
        source=record.get("source") or "Imported",
    )
    paper.authors = [
        _get_or_create(session, Author, "name", name)
        for name in split_authors(record.get("authors"))
    ]
    body = f"{paper.title}. {paper.abstract}"
    paper.topics = [
        _get_or_create(session, Topic, "name", topic)
        for topic in (record.get("topics") or classify_topic(body))
    ]
    paper.keywords = [
        _get_or_create(session, Keyword, "keyword", keyword)
        for keyword in (record.get("keywords") or extract_keywords(body, 8))
    ]
    session.add(paper)
    session.commit()
    session.refresh(paper)
    return paper, True


def _get_or_create(session: Session, model, field: str, value: str):
    item = session.scalar(select(model).where(getattr(model, field) == value))
    if item is None:
        item = model(**{field: value})
        session.add(item)
        session.flush()
    return item


def set_saved(session: Session, paper_id: int, saved: bool) -> bool:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise LookupError("Paper not found.")
    entry = session.scalar(select(SavedPaper).where(SavedPaper.paper_id == paper_id))
    if saved and entry is None:
        session.add(SavedPaper(paper_id=paper_id))
    elif not saved and entry is not None:
        session.delete(entry)
    session.commit()
    return saved