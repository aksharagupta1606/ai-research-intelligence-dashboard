from __future__ import annotations

from collections import Counter

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Paper, PaperAnalysis


def render(session: Session) -> None:
    st.title("Research Gap Finder")
    st.write("A screening aid for locating underrepresented areas in this paper collection.")
    st.warning(
        "These are potential research gaps detected from available papers, not scientifically proven gaps. "
        "Validate each finding with domain experts and a broader literature search."
    )
    papers = list(
        session.scalars(
            select(Paper).options(
                selectinload(Paper.topics), selectinload(Paper.analyses)
            ).order_by(Paper.publication_year.desc())
        ).unique()
    )
    if not papers:
        st.info("Add papers before generating potential research gaps.")
        return
    topic_counts = Counter(topic.name for paper in papers for topic in paper.topics)
    weakest_topic = min(topic_counts, key=topic_counts.get)
    most_common_topic, most_common_count = topic_counts.most_common(1)[0]
    pair_counts = Counter()
    for paper in papers:
        names = sorted({topic.name for topic in paper.topics})
        for index, first in enumerate(names):
            for second in names[index + 1 :]:
                pair_counts[(first, second)] += 1
    low_pair = min(pair_counts, key=pair_counts.get) if pair_counts else (weakest_topic, most_common_topic)
    recent_year = max((paper.publication_year or 0) for paper in papers)
    recent_papers = [paper for paper in papers if paper.publication_year and paper.publication_year >= recent_year - 2]
    limitations = []
    for paper in papers:
        for analysis in paper.analyses[-1:]:
            if analysis.limitations:
                limitations.append((paper, analysis.limitations))
    candidates = [
        {
            "title": f"Limited coverage of {weakest_topic} in the available collection",
            "evidence": [
                f"{weakest_topic} appears in {topic_counts[weakest_topic]} paper(s), compared with {most_common_topic} ({most_common_count}).",
                f"The current collection contains {len(papers)} papers; counts depend on the available sample.",
            ],
            "related": [paper for paper in papers if any(topic.name == weakest_topic for topic in paper.topics)][:4],
            "frequency": topic_counts[weakest_topic],
            "confidence": min(0.9, round(0.35 + 0.55 * (1 - topic_counts[weakest_topic] / max(most_common_count, 1)), 2)),
            "direction": f"Expand the corpus for {weakest_topic} and compare study settings, data sources, and evaluation protocols.",
        },
        {
            "title": f"Few papers connect {low_pair[0]} with {low_pair[1]}",
            "evidence": [
                f"The topic pair appears together in {pair_counts.get(low_pair, 0)} paper(s) in this collection.",
                "This signal is based on assigned paper topics, not a comprehensive review.",
            ],
            "related": [paper for paper in papers if any(topic.name in low_pair for topic in paper.topics)][:4],
            "frequency": pair_counts.get(low_pair, 0),
            "confidence": 0.52,
            "direction": f"Search for cross-disciplinary work joining {low_pair[0]} and {low_pair[1]}, then evaluate whether shared datasets or methods are missing.",
        },
        {
            "title": "Validation in recent deployment settings may be underreported",
            "evidence": [
                f"{len(recent_papers)} papers fall within the three most recent years represented ({max(0, recent_year - 2)}–{recent_year}).",
                f"{len(limitations)} stored analysis notes mention limitations; local NLP can miss nuanced discussion.",
            ],
            "related": recent_papers[:4],
            "frequency": len(recent_papers),
            "confidence": 0.44,
            "direction": "Review recent full texts for prospective validation, external datasets, and reproducibility details.",
        },
    ]
    st.markdown("### Potential research gaps")
    for item in candidates:
        with st.container(border=True):
            title_col, confidence_col = st.columns([4, 1])
            title_col.markdown(f"#### {item['title']}")
            confidence_col.metric("Signal", f"{item['confidence']:.0%}")
            st.caption(f"Detected from available papers · Frequency: {item['frequency']}")
            st.markdown("**Evidence**")
            for evidence in item["evidence"]:
                st.markdown(f"- {evidence}")
            st.markdown(f"**Suggested direction:** {item['direction']}")
            st.markdown("**Related papers**")
            for paper in item["related"]:
                st.markdown(f"- {paper.title} ({paper.publication_year or 'year n/a'})")
            st.caption("Requires expert validation before drawing conclusions.")

    if limitations:
        st.markdown("### Frequently noted limitations in saved analyses")
        for paper, limitation in limitations[:8]:
            st.markdown(f"- **{paper.title}:** {limitation[:280]}")