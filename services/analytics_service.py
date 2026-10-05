from __future__ import annotations

from collections import Counter

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Paper, SavedPaper
from services.nlp_service import extract_keywords, keyword_frequency


def all_papers(session: Session) -> list[Paper]:
    return list(
        session.scalars(
            select(Paper).options(
                selectinload(Paper.authors), selectinload(Paper.topics), selectinload(Paper.keywords)
            ).order_by(Paper.publication_year.desc(), Paper.title)
        ).unique()
    )


def paper_to_dict(paper: Paper) -> dict:
    return {
        "id": paper.id,
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": [author.name for author in paper.authors],
        "publication_year": paper.publication_year,
        "journal": paper.journal,
        "doi": paper.doi,
        "url": paper.url,
        "citation_count": paper.citation_count,
        "source": paper.source,
        "topics": [topic.name for topic in paper.topics],
        "keywords": [keyword.keyword for keyword in paper.keywords],
    }


def build_frame(papers: list[Paper]) -> pd.DataFrame:
    rows = []
    for paper in papers:
        base = paper_to_dict(paper)
        if not base["keywords"]:
            base["keywords"] = extract_keywords(f"{paper.title} {paper.abstract}", 6)
        rows.append(base)
    return pd.DataFrame(rows)


def dashboard_metrics(session: Session) -> dict:
    papers = all_papers(session)
    frame = build_frame(papers)
    authors = {author.name for paper in papers for author in paper.authors}
    topics = {topic.name for paper in papers for topic in paper.topics}
    keyword_counts = keyword_frequency([f"{p.title}. {p.abstract}" for p in papers], 1)
    author_counts = Counter(author.name for paper in papers for author in paper.authors)
    years = [paper.publication_year for paper in papers if paper.publication_year]
    saved_total = session.query(SavedPaper).count()
    return {
        "total_papers": len(papers),
        "total_authors": len(authors),
        "total_topics": len(topics),
        "avg_year": round(sum(years) / len(years)) if years else None,
        "avg_citations": round(sum(p.citation_count for p in papers) / len(papers)) if papers else 0,
        "latest_year": max(years) if years else None,
        "top_topic": Counter(topic.name for paper in papers for topic in paper.topics).most_common(1),
        "top_keyword": keyword_counts[0][0] if keyword_counts else "—",
        "top_author": author_counts.most_common(1),
        "saved_count": saved_total,
        "papers": papers,
        "frame": frame,
    }