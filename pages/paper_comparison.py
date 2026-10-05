from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Paper, PaperAnalysis
from services.ai_service import compare_papers
from services.nlp_service import classify_topic, extract_keywords, extract_methodology, extract_future_work


def render(session: Session) -> None:
    st.title("Compare Papers")
    st.write("Compare two to four papers side by side, including TF-IDF similarity and shared terms.")
    papers = list(
        session.scalars(
            select(Paper).options(
                selectinload(Paper.authors), selectinload(Paper.topics), selectinload(Paper.keywords),
                selectinload(Paper.analyses),
            ).order_by(Paper.title)
        ).unique()
    )
    if len(papers) < 2:
        st.info("Add at least two papers before comparing.")
        return
    by_id = {paper.id: paper for paper in papers}
    default_ids = [paper_id for paper_id in st.session_state.get("comparison_ids", []) if paper_id in by_id]
    selected_ids = st.multiselect(
        "Choose two to four papers",
        [paper.id for paper in papers],
        default=default_ids[:4],
        format_func=lambda paper_id: by_id[paper_id].title,
        max_selections=4,
        key="compare-paper-select",
    )
    if len(selected_ids) < 2:
        st.info("Select at least two papers to see the comparison.")
        return
    chosen = [by_id[paper_id] for paper_id in selected_ids]
    records = []
    for paper in chosen:
        latest = paper.analyses[-1] if paper.analyses else None
        records.append(
            {
                "id": paper.id,
                "title": paper.title,
                "authors": ", ".join(author.name for author in paper.authors),
                "year": paper.publication_year,
                "topic": ", ".join(topic.name for topic in paper.topics) or ", ".join(classify_topic(paper.abstract)),
                "keywords": ", ".join(item.keyword for item in paper.keywords) or ", ".join(extract_keywords(paper.abstract)),
                "methodology": latest.methodology if latest else extract_methodology(paper.abstract),
                "dataset": latest.dataset if latest else "Not explicitly identified in the abstract.",
                "accuracy": "Not reported in available metadata",
                "limitations": latest.limitations if latest else "Use Paper Analyzer to identify limitations.",
                "future_work": latest.future_work if latest else extract_future_work(paper.abstract),
                "citations": paper.citation_count,
                "_text": f"{paper.title} {paper.abstract}",
            }
        )
    st.markdown("### Side-by-side comparison")
    table = pd.DataFrame(records).drop(columns=["id", "_text"]).set_index("title").T
    st.dataframe(table, width="stretch", height=400)

    analysis = compare_papers(records)
    matrix = pd.DataFrame(
        analysis["similarity"],
        index=[record["title"] for record in records],
        columns=[record["title"] for record in records],
    )
    st.markdown("### Text similarity")
    figure = px.imshow(
        matrix,
        text_auto=".0%",
        color_continuous_scale=["#eff1ff", "#7c8cf1", "#394fd3"],
        zmin=0,
        zmax=1,
        aspect="auto",
    )
    figure.update_layout(coloraxis_colorbar_title="Similarity", margin=dict(l=4, r=4, t=16, b=4))
    st.plotly_chart(figure, width="stretch")
    if analysis["common_keywords"]:
        st.markdown("**Common keywords:** " + ", ".join(analysis["common_keywords"]))
    else:
        st.markdown("**Common keywords:** No shared high-ranking TF-IDF keywords.")
    with st.expander("Unique keywords by paper"):
        for record, unique in zip(records, analysis["unique_keywords"]):
            st.markdown(f"- **{record['title']}:** {', '.join(unique[:12]) or 'No unique keywords found'}")
    st.caption("Similarity is calculated from titles and abstracts using TF-IDF and cosine similarity; it is not a measure of scientific quality.")