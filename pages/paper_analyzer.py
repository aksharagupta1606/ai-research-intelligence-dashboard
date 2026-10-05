from __future__ import annotations

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Paper
from pages.common import render_analysis, save_analysis
from services.ai_service import analyze_paper


def render(session: Session) -> None:
    st.title("Paper Analyzer")
    st.write("Analyze research text or run a local NLP analysis on a paper in your library.")
    papers = list(
        session.scalars(
            select(Paper).options(
                selectinload(Paper.authors), selectinload(Paper.topics), selectinload(Paper.keywords)
            ).order_by(Paper.title)
        ).unique()
    )
    selected_id = st.session_state.get("selected_paper_id")
    selected = session.get(Paper, selected_id) if selected_id else None
    library_tab, text_tab = st.tabs(["From my library", "Paste research text"])
    analysis_tab, text, source_paper = None, "", None
    with library_tab:
        if not papers:
            st.info("Add a paper to your library before analyzing it.")
        else:
            paper_ids = [paper.id for paper in papers]
            initial = paper_ids.index(selected.id) if selected and selected.id in paper_ids else 0
            paper_id = st.selectbox(
                "Select a paper",
                paper_ids,
                index=initial,
                format_func=lambda item: next((paper.title for paper in papers if paper.id == item), str(item)),
                key="analyzer_paper_select",
            )
            source_paper = next(paper for paper in papers if paper.id == paper_id)
            st.caption(
                f"{source_paper.publication_year or 'Year n/a'} · "
                f"{', '.join(author.name for author in source_paper.authors)}"
            )
            st.write(source_paper.abstract or "No abstract is available. The title will still be analyzed.")
            text = f"{source_paper.title}. {source_paper.abstract}"
            if st.button("Analyze selected paper", type="primary", icon=":material/auto_awesome:", key="analyze-library"):
                _analyze(session, source_paper, text)
                st.rerun()
    with text_tab:
        title = st.text_input("Paper title (optional)", key="pasted_paper_title")
        pasted_text = st.text_area(
            "Paste an abstract or paper text",
            height=260,
            placeholder="Paste research text here. Local NLP works without an AI API key.",
            key="pasted_research_text",
        )
        if st.button("Analyze pasted text", type="primary", icon=":material/auto_awesome:", key="analyze-pasted"):
            if len(pasted_text.strip()) < 80:
                st.warning("Add at least a few sentences so the analysis has enough context.")
            else:
                st.session_state["analysis_result"] = analyze_paper(pasted_text.strip())
                st.session_state["analysis_title"] = title.strip() or "Pasted research text"
                st.session_state["analysis_text"] = pasted_text.strip()
                st.rerun()
    result = st.session_state.get("analysis_result")
    if result:
        st.divider()
        st.caption(f"Analyzing: {st.session_state.get('analysis_title', 'Research paper')}")
        _render_analysis_result(st, result)


def _analyze(session: Session, paper: Paper, text: str) -> None:
    if len(text.strip()) < 80:
        st.warning("This paper has too little available text. Paste a longer abstract or use the PDF Analyzer.")
        return
    result = analyze_paper(text)
    save_analysis(session, paper.id, result)
    st.session_state["analysis_result"] = result
    st.session_state["analysis_title"] = paper.title
    st.session_state["analysis_text"] = text
    st.session_state["selected_paper_id"] = paper.id


def _render_analysis_result(st, result: dict) -> None:
    st.markdown(f"### {st.session_state.get('analysis_title', 'Research paper')}")
    st.caption(f"Analysis source: {result.get('source', 'NLP-generated analysis')}")
    st.markdown("#### Short summary")
    st.write(result.get("summary") or "No summary could be generated.")
    with st.expander("Full analysis", expanded=True):
        st.markdown("**Detailed summary**")
        st.write(result.get("detailed_summary") or "Not available.")
        columns = st.columns(2)
        fields = [
            ("Keywords", ", ".join(result.get("keywords", []))),
            ("Main topics", ", ".join(result.get("topics", []))),
            ("Methodology", result.get("methodology")),
            ("Dataset information", result.get("dataset")),
            ("Key findings", result.get("findings")),
            ("Limitations", result.get("limitations")),
            ("Future work", result.get("future_work")),
        ]
        for index, (name, value) in enumerate(fields):
            with columns[index % 2]:
                st.markdown(f"**{name}**")
                st.write(value or "Not explicitly identified in the available text.")
        st.markdown("**Potential research gaps — requires expert validation**")
        for gap in result.get("research_gaps", []):
            st.markdown(f"- {gap}")