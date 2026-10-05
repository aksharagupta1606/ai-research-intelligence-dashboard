from __future__ import annotations

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Paper, SavedPaper
from pages.common import detail_panel, render_paper_card


def render(session: Session) -> None:
    st.title("Saved Research")
    st.write("A working shortlist of papers you want to revisit or compare.")
    q = st.text_input("Search saved papers", key="saved-search", placeholder="Search title, abstract, author, or keyword")
    entries = list(
        session.scalars(
            select(SavedPaper)
            .options(
                selectinload(SavedPaper.paper).selectinload(Paper.authors),
                selectinload(SavedPaper.paper).selectinload(Paper.topics),
                selectinload(SavedPaper.paper).selectinload(Paper.keywords),
            )
            .order_by(SavedPaper.created_at.desc())
        ).unique()
    )
    papers = [entry.paper for entry in entries]
    if q:
        needle = q.lower()
        papers = [
            paper for paper in papers
            if needle in paper.title.lower()
            or needle in paper.abstract.lower()
            or needle in " ".join(author.name for author in paper.authors).lower()
            or needle in " ".join(keyword.keyword for keyword in paper.keywords).lower()
        ]
    st.caption(f"{len(papers)} saved paper(s)")
    if not papers:
        st.info("No saved papers yet. Use Save in Research Explorer to add papers to this list.")
        return
    for paper in papers:
        render_paper_card(session, paper)
    detail_panel(session)