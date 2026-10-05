from __future__ import annotations

from collections import Counter
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.schemas import PaperComparisonRequest, PaperTextRequest
from config.settings import MAX_UPLOAD_BYTES
from database.database import SessionLocal, init_db
from database.models import Author, Paper, SavedPaper, Topic, UploadedDocument
from services.ai_service import analyze_paper, compare_papers
from services.analytics_service import paper_to_dict
from services.library_service import set_saved
from services.pdf_service import extract_pdf
from utils.logger import logger

app = FastAPI(
    title="AI Research Intelligence Dashboard API",
    description="Research paper search, analysis, trend, comparison, and upload services.",
    version="1.0.0",
)


@app.middleware("http")
async def log_api_failures(request, call_next):
    try:
        return await call_next(request)
    except Exception as error:
        logger.error("API request failed (%s).", type(error).__name__)
        raise


def _session() -> Session:
    init_db()
    return SessionLocal()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AI Research Intelligence Dashboard"}


@app.get("/api/papers")
def list_papers(
    q: str = "",
    topic: str | None = None,
    author: str | None = None,
    year: int | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    session = _session()
    try:
        query = select(Paper).options(
            selectinload(Paper.authors), selectinload(Paper.topics), selectinload(Paper.keywords)
        )
        if q.strip():
            like = f"%{q.strip()}%"
            query = query.where((Paper.title.ilike(like)) | (Paper.abstract.ilike(like)))
        if year:
            query = query.where(Paper.publication_year == year)
        papers = list(session.scalars(query.order_by(Paper.publication_year.desc(), Paper.title)).unique())
        if topic:
            papers = [paper for paper in papers if any(topic.lower() == item.name.lower() for item in paper.topics)]
        if author:
            papers = [paper for paper in papers if any(author.lower() in item.name.lower() for item in paper.authors)]
        total = len(papers)
        return {"items": [paper_to_dict(paper) for paper in papers[offset : offset + limit]], "total": total}
    finally:
        session.close()


@app.get("/api/papers/{paper_id}")
def get_paper(paper_id: int):
    session = _session()
    try:
        paper = session.scalar(
            select(Paper)
            .where(Paper.id == paper_id)
            .options(
                selectinload(Paper.authors), selectinload(Paper.topics), selectinload(Paper.keywords),
                selectinload(Paper.analyses),
            )
        )
        if paper is None:
            raise HTTPException(404, "Paper not found.")
        result = paper_to_dict(paper)
        result["analysis"] = [
            {
                "summary": entry.summary, "detailed_summary": entry.detailed_summary,
                "methodology": entry.methodology, "dataset": entry.dataset, "findings": entry.findings,
                "limitations": entry.limitations, "future_work": entry.future_work,
                "research_gaps": entry.research_gaps,
            }
            for entry in paper.analyses
        ]
        return result
    finally:
        session.close()


@app.get("/api/search")
def search_papers(
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return list_papers(q=q, limit=limit)


@app.get("/api/topics")
def list_topics():
    session = _session()
    try:
        topics = session.scalars(select(Topic).order_by(Topic.name)).all()
        return [{"name": topic.name, "paper_count": len(topic.papers)} for topic in topics]
    finally:
        session.close()


@app.get("/api/authors")
def list_authors(q: str = ""):
    session = _session()
    try:
        query = select(Author).order_by(Author.name)
        if q:
            query = query.where(Author.name.ilike(f"%{q}%"))
        return [{"name": author.name, "paper_count": len(author.papers)} for author in session.scalars(query).all()]
    finally:
        session.close()


@app.get("/api/trends")
def trends():
    session = _session()
    try:
        papers = session.scalars(
            select(Paper).options(selectinload(Paper.topics), selectinload(Paper.authors))
        ).unique().all()
        years = Counter(p.publication_year for p in papers if p.publication_year)
        topics = Counter(topic.name for p in papers for topic in p.topics)
        return {
            "publications_by_year": [{"year": year, "count": years[year]} for year in sorted(years)],
            "papers_by_topic": [{"topic": name, "count": count} for name, count in topics.most_common()],
        }
    finally:
        session.close()


@app.post("/api/analyze")
def analyze(request: PaperTextRequest):
    return analyze_paper(request.text)


@app.post("/api/upload")
async def upload_pdf(file: Annotated[UploadFile, File()]):
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(415, "Upload a PDF file.")
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"PDF exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.")
    try:
        result = extract_pdf(contents, file.filename or "upload.pdf")
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    session = _session()
    try:
        document = UploadedDocument(
            filename=result["filename"],
            file_path="",
            extracted_text=result["text"],
            word_count=result["words"],
            page_count=result["pages"],
        )
        session.add(document)
        session.commit()
        return {"id": document.id, **result}
    finally:
        session.close()


@app.post("/api/papers/{paper_id}/save")
def save_paper(paper_id: int):
    session = _session()
    try:
        try:
            set_saved(session, paper_id, True)
        except LookupError as error:
            raise HTTPException(404, str(error)) from error
        return {"paper_id": paper_id, "saved": True}
    finally:
        session.close()


@app.delete("/api/papers/{paper_id}/save")
def unsave_paper(paper_id: int):
    session = _session()
    try:
        try:
            set_saved(session, paper_id, False)
        except LookupError as error:
            raise HTTPException(404, str(error)) from error
        return {"paper_id": paper_id, "saved": False}
    finally:
        session.close()


@app.post("/api/compare")
def compare(request: PaperComparisonRequest):
    session = _session()
    try:
        papers = session.scalars(
            select(Paper).where(Paper.id.in_(request.paper_ids)).options(
                selectinload(Paper.authors), selectinload(Paper.topics), selectinload(Paper.keywords)
            )
        ).unique().all()
        if len(papers) != len(set(request.paper_ids)):
            raise HTTPException(404, "One or more selected papers were not found.")
        dicts = [paper_to_dict(paper) for paper in papers]
        return {"papers": dicts, **compare_papers(dicts)}
    finally:
        session.close()