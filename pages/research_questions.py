from __future__ import annotations

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Paper
from services.ai_service import generate_research_questions


def render(session: Session) -> None:
    st.title("Research Question Generator")
    st.write("Generate five starting questions from the selected topic and the papers currently in your library.")
    papers = list(
        session.scalars(
            select(Paper).options(selectinload(Paper.topics)).order_by(Paper.publication_year.desc())
        ).unique()
    )
    topic_names = sorted({topic.name for paper in papers for topic in paper.topics})
    topic = st.selectbox("Research topic", topic_names or ["Data Science"], key="question-topic")
    matching = [
        paper for paper in papers if any(item.name == topic for item in paper.topics)
    ]
    if st.button("Generate five questions", type="primary", icon=":material/lightbulb:", key="generate-questions"):
        gaps = [
            f"Limited representation of {topic.lower()} in the available paper collection.",
            f"More external validation is needed for methods related to {topic.lower()}.",
            f"Comparative evidence about datasets and evaluation settings is limited.",
        ]
        records = [{"title": paper.title} for paper in matching[:4]]
        st.session_state["generated_questions"] = generate_research_questions(topic, gaps, records)
    if st.session_state.get("generated_questions"):
        st.info("AI-generated suggestions — use as starting points and validate with domain experts.")
        for index, item in enumerate(st.session_state["generated_questions"], start=1):
            with st.container(border=True):
                st.markdown(f"#### {index}. {item['question']}")
                st.markdown(f"**Related research gap:** {item['gap']}")
                st.markdown(f"**Suggested methodology:** {item['methodology']}")
                st.markdown(f"**Relevant papers:** {', '.join(item['papers']) or 'No topic-matched papers; search the library to broaden the evidence.'}")
                st.caption(item["label"])