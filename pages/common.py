from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import streamlit as st

from database.models import Paper, PaperAnalysis, SavedPaper
from services.analytics_service import paper_to_dict
from services.library_service import set_saved
from services.nlp_service import classify_topic, extract_keywords
from services.recommendation_service import similar_papers


def set_page_after_rerun(page_name: str) -> None:
    st.session_state["pending_page"] = page_name


def toggle_compare(paper_id: int) -> None:
    selected = list(st.session_state.get("comparison_ids", []))
    if paper_id in selected:
        selected.remove(paper_id)
    elif len(selected) < 4:
        selected.append(paper_id)
    else:
        st.session_state["flash_message"] = "Paper comparison is limited to four papers."
        return
    st.session_state["comparison_ids"] = selected


def save_toggle(session: Session, paper_id: int) -> None:
    saved = set_saved(session, paper_id, not is_saved(session, paper_id))
    st.session_state["flash_message"] = "Paper saved to your library." if saved else "Paper removed from saved research."


def is_saved(session: Session, paper_id: int) -> bool:
    return session.scalar(select(SavedPaper.id).where(SavedPaper.paper_id == paper_id)) is not None


def render_kpis(metrics: dict) -> None:
    columns = st.columns(4)
    items = [
        ("Total papers", f"{metrics['total_papers']:,}", "article"),
        ("Authors", f"{metrics['total_authors']:,}", "groups"),
        ("Research topics", f"{metrics['total_topics']:,}", "topic"),
        ("Average citations", f"{metrics['avg_citations']:,}", "format_quote"),
    ]
    for column, (label, value, icon) in zip(columns, items):
        column.markdown(
            f'<div class="kpi-card"><div class="kpi-icon">◈</div><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div><div class="kpi-foot"><span class="material-icon">{icon}</span> research library</div></div>',
            unsafe_allow_html=True,
        )


def render_paper_card(session: Session, paper: Paper, compact: bool = False) -> None:
    with st.container(border=True):
        st.markdown(f"#### {paper.title}")
        author_line = ", ".join(author.name for author in paper.authors) or "Author information unavailable"
        topic_line = " · ".join(topic.name for topic in paper.topics) or "Unclassified"
        st.caption(
            f"{author_line}  ·  {paper.publication_year or 'Year n/a'}  ·  {paper.citation_count:,} citations"
        )
        st.markdown(paper.abstract[:540] + ("…" if len(paper.abstract) > 540 else ""))
        badges = [topic.name for topic in paper.topics] + [keyword.keyword for keyword in paper.keywords[:5]]
        if badges:
            st.markdown(" ".join(f"`{badge}`" for badge in badges[:8]))
        if paper.source.startswith("Demo"):
            st.caption("Illustrative demo record · Citation counts are sample values.")
        actions = st.columns(4 if not compact else 3)
        if actions[0].button(
            "Analyze",
            key=f"paper-analyze-{paper.id}",
            icon=":material/analytics:",
            width="stretch",
        ):
            st.session_state["selected_paper_id"] = paper.id
            st.session_state.pop("analyzer_paper_select", None)
            set_page_after_rerun("Paper Analyzer")
            st.rerun()
        saved = is_saved(session, paper.id)
        if actions[1].button(
            "Saved" if saved else "Save",
            key=f"paper-save-{paper.id}",
            icon=":material/bookmark_added:" if saved else ":material/bookmark_add:",
            width="stretch",
        ):
            save_toggle(session, paper.id)
            st.rerun()
        if actions[2].button(
            "Remove from compare" if paper.id in st.session_state.get("comparison_ids", []) else "Compare",
            key=f"paper-compare-{paper.id}",
            icon=":material/compare_arrows:",
            width="stretch",
        ):
            toggle_compare(paper.id)
            st.rerun()
        if not compact and actions[3].button(
            "Details",
            key=f"paper-details-{paper.id}",
            icon=":material/open_in_new:",
            width="stretch",
        ):
            st.session_state["detail_paper_id"] = paper.id
            st.rerun()
        if st.session_state.get("detail_paper_id") == paper.id:
            with st.expander("Paper details", expanded=True):
                st.write(f"**Journal:** {paper.journal or 'Not listed'}")
                st.write(f"**Topics:** {topic_line}")
                st.write(f"**Keywords:** {', '.join(item.keyword for item in paper.keywords) or ', '.join(extract_keywords(paper.abstract))}")
                st.write(f"**Source:** {paper.source}")
                if paper.doi:
                    st.markdown(f"[DOI](https://doi.org/{paper.doi})")
                if paper.url:
                    st.markdown(f"[Open paper]({paper.url})")


def render_analysis(session: Session, paper: Paper, analysis: dict) -> None:
    st.markdown(f"### {paper.title}")
    st.caption(f"Analysis source: {analysis.get('source', 'NLP-generated analysis')}")
    st.markdown("#### Summary")
    st.write(analysis.get("summary") or "No summary available.")
    with st.expander("Detailed analysis", expanded=True):
        st.markdown("**Detailed summary**")
        st.write(analysis.get("detailed_summary") or "Not available.")
        left, right = st.columns(2)
        for column, label, value in [
            (left, "Main topics", ", ".join(analysis.get("topics", []))),
            (right, "Keywords", ", ".join(analysis.get("keywords", []))),
            (left, "Methodology", analysis.get("methodology")),
            (right, "Dataset", analysis.get("dataset")),
            (left, "Key findings", analysis.get("findings")),
            (right, "Limitations", analysis.get("limitations")),
            (left, "Future work", analysis.get("future_work")),
        ]:
            with column:
                st.markdown(f"**{label}**")
                st.write(value or "Not explicitly identified in the available text.")
        st.markdown("**Potential research gaps — requires expert validation**")
        for gap in analysis.get("research_gaps", []):
            st.markdown(f"- {gap}")


def save_analysis(session: Session, paper_id: int, analysis: dict) -> None:
    entry = PaperAnalysis(
        paper_id=paper_id,
        summary=analysis.get("summary", ""),
        detailed_summary=analysis.get("detailed_summary", ""),
        methodology=analysis.get("methodology", ""),
        dataset=analysis.get("dataset", ""),
        findings=analysis.get("findings", ""),
        limitations=analysis.get("limitations", ""),
        future_work=analysis.get("future_work", ""),
        research_gaps="\n".join(analysis.get("research_gaps", [])),
    )
    session.add(entry)
    session.commit()


def detail_panel(session: Session) -> None:
    paper_id = st.session_state.get("detail_paper_id")
    if not paper_id:
        return
    paper = session.scalar(
        select(Paper)
        .where(Paper.id == paper_id)
        .options(selectinload(Paper.authors), selectinload(Paper.topics), selectinload(Paper.keywords))
    )
    if paper is None:
        st.session_state.pop("detail_paper_id", None)
        return
    with st.container(border=True):
        title, close = st.columns([8, 1])
        title.markdown(f"### Selected paper: {paper.title}")
        if close.button("Close", key="close-details"):
            st.session_state.pop("detail_paper_id", None)
            st.rerun()
        st.write(paper.abstract or "No abstract is available.")
        st.caption(f"{paper.publication_year or 'Year n/a'} · {', '.join(a.name for a in paper.authors)} · {paper.source}")


def paper_dict(paper: Paper) -> dict:
    return paper_to_dict(paper)