from __future__ import annotations

from pydantic import BaseModel, Field


class PaperTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=250_000)
    title: str | None = Field(default=None, max_length=500)


class PaperComparisonRequest(BaseModel):
    paper_ids: list[int] = Field(min_length=2, max_length=4)


class PaperResponse(BaseModel):
    id: int
    title: str
    abstract: str
    authors: list[str]
    publication_year: int | None
    journal: str
    doi: str | None
    url: str | None
    citation_count: int
    source: str
    topics: list[str]
    keywords: list[str]


class AnalysisResponse(BaseModel):
    source: str
    summary: str
    detailed_summary: str
    keywords: list[str]
    topics: list[str]
    methodology: str
    dataset: str
    findings: str
    limitations: str
    future_work: str
    research_gaps: list[str]