from __future__ import annotations

import plotly.express as px
import streamlit as st
from sqlalchemy.orm import Session

from pages.common import render_kpis, render_paper_card
from services.analytics_service import dashboard_metrics


def render(session: Session) -> None:
    metrics = dashboard_metrics(session)
    st.markdown('<div class="eyebrow">RESEARCH INTELLIGENCE</div>', unsafe_allow_html=True)
    st.title("Your literature, in context.")
    st.write(
        "AI Research Intelligence Dashboard helps researchers explore research papers, analyze scientific "
        "literature, identify trends, and detect potential research gaps using AI and NLP."
    )
    st.markdown(
        '<div class="demo-banner"><span class="demo-dot"></span><strong>DEMO COLLECTION</strong> '
        'Illustrative sample papers and citation counts are included. Add or search for real research to grow your library.</div>',
        unsafe_allow_html=True,
    )
    render_kpis(metrics)
    st.markdown('<div class="section-heading"><div><span class="eyebrow">COLLECTION SIGNALS</span><h3>At a glance</h3></div></div>', unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    top_topic = metrics["top_topic"][0][0] if metrics["top_topic"] else "—"
    top_author = metrics["top_author"][0][0] if metrics["top_author"] else "—"
    col_a.metric("Most represented topic", top_topic)
    col_b.metric("Most active author", top_author)
    col_c.metric("Latest publication", metrics["latest_year"] or "—")
    frame = metrics["frame"]
    left, right = st.columns([1.3, 1])
    if not frame.empty:
        with left:
            st.markdown("#### Publications over time")
            yearly = frame.dropna(subset=["publication_year"]).groupby("publication_year", as_index=False).size()
            figure = px.area(yearly, x="publication_year", y="size", markers=True)
            figure.update_traces(line_color="#4964e9", fillcolor="rgba(73,100,233,.12)")
            figure.update_layout(xaxis_title=None, yaxis_title="Papers", margin=dict(l=4, r=4, t=12, b=4))
            st.plotly_chart(figure, width="stretch")
        with right:
            st.markdown("#### Research topics")
            topic_counts = frame.explode("topics").groupby("topics", as_index=False).size().sort_values("size")
            figure = px.bar(topic_counts.tail(7), x="size", y="topics", orientation="h")
            figure.update_traces(marker_color="#7685ee")
            figure.update_layout(xaxis_title="Papers", yaxis_title=None, margin=dict(l=4, r=4, t=12, b=4))
            st.plotly_chart(figure, width="stretch")
    st.markdown("#### Recently added to the library")
    for paper in metrics["papers"][:3]:
        render_paper_card(session, paper, compact=True)