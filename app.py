from __future__ import annotations

from pathlib import Path

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.database import SessionLocal, init_db
from database.models import Paper
from database.seed import seed_database
from pages import (
    author_intelligence,
    overview,
    paper_analyzer,
    paper_comparison,
    pdf_analyzer,
    research_explorer,
    research_gaps,
    research_questions,
    research_trends,
    saved_research,
)

PAGE_RENDERERS = {
    "Overview": overview.render,
    "Research Explorer": research_explorer.render,
    "Paper Analyzer": paper_analyzer.render,
    "Research Trends": research_trends.render,
    "Research Gap Finder": research_gaps.render,
    "Compare Papers": paper_comparison.render,
    "Author Intelligence": author_intelligence.render,
    "PDF Analyzer": pdf_analyzer.render,
    "Saved Research": saved_research.render,
    "Research Questions": research_questions.render,
}

st.set_page_config(
    page_title="AI Research Intelligence",
    page_icon=":material/biotech:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_styles() -> None:
    css_path = Path(__file__).resolve().parent / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def show_empty_state(session: Session) -> None:
    st.title("Your research workspace is ready")
    st.write("There are no papers in the current database yet.")
    if st.button("Load the 30-paper demo collection", type="primary", icon=":material/database:"):
        added = seed_database()
        st.success(f"Added {added} illustrative research records.")
        st.rerun()
    st.caption("You can also import research through OpenAlex search or analyze a PDF.")


def main() -> None:
    load_styles()
    init_db()
    session = SessionLocal()
    try:
        if session.scalar(select(Paper.id).limit(1)) is None:
            seed_database()

        pending_page = st.session_state.pop("pending_page", None)
        if pending_page in PAGE_RENDERERS:
            st.session_state["nav_page"] = pending_page
        flash_message = st.session_state.pop("flash_message", None)

        with st.sidebar:
            st.markdown(
                '<div class="brand-block"><div class="brand-mark">R</div><div>'
                '<div class="brand-name">Research Atlas</div><div class="brand-kicker">INTELLIGENCE WORKSPACE</div></div></div>',
                unsafe_allow_html=True,
            )
            st.markdown("<div class='sidebar-label'>WORKSPACE</div>", unsafe_allow_html=True)
            page_name = st.radio(
                "Navigate",
                list(PAGE_RENDERERS),
                key="nav_page",
                label_visibility="collapsed",
            )
            st.markdown("<div class='sidebar-separator'></div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='sidebar-stat'><strong>{len(PAGE_RENDERERS)}</strong>"
                "<span>research tools</span></div>",
                unsafe_allow_html=True,
            )
            st.caption("Your paper library and analyses are stored in the local SQLite database.")
            st.markdown(
                "<div class='sidebar-note'><strong>About gap signals</strong><br>"
                "All detected gaps are tentative and require expert validation.</div>",
                unsafe_allow_html=True,
            )

        if flash_message:
            st.success(flash_message)

        PAGE_RENDERERS[page_name](session)
    except Exception as error:
        from utils.logger import logger

        logger.error("A dashboard page failed to render (%s).", type(error).__name__)
        st.error("This page could not be loaded. Your database has not been removed.")
        st.caption(f"Details: {type(error).__name__}: {error}")
    finally:
        session.close()


if __name__ == "__main__":
    main()