from __future__ import annotations

import math
from collections import Counter

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Author, Paper


def render(session: Session) -> None:
    st.title("Author Intelligence")
    st.write("Review publication activity, research areas, citations, and co-author connections.")
    authors = session.scalars(select(Author).order_by(Author.name)).all()
    if not authors:
        st.info("No author records are available yet.")
        return
    author_by_id = {author.id: author for author in authors}
    author_id = st.selectbox(
        "Select an author",
        list(author_by_id),
        format_func=lambda item: author_by_id[item].name,
        key="author-select",
    )
    author = author_by_id[author_id]
    papers = list(
        session.scalars(
            select(Paper).options(
                selectinload(Paper.authors), selectinload(Paper.topics), selectinload(Paper.keywords)
            ).order_by(Paper.publication_year)
        ).unique()
    )
    authored = [paper for paper in papers if any(item.id == author.id for item in paper.authors)]
    if not authored:
        st.info("No papers are connected to this author.")
        return
    cols = st.columns(4)
    cols[0].metric("Publications", len(authored))
    cols[1].metric("Total citations", f"{sum(paper.citation_count for paper in authored):,}")
    cols[2].metric("Research topics", len({topic.name for paper in authored for topic in paper.topics}))
    cols[3].metric("Co-authors", len({co.name for paper in authored for co in paper.authors if co.id != author.id}))

    timeline = pd.DataFrame(
        [{"year": paper.publication_year, "title": paper.title, "citations": paper.citation_count}
         for paper in authored if paper.publication_year]
    )
    if not timeline.empty:
        yearly = timeline.groupby("year", as_index=False).agg(publications=("title", "count"))
        chart = px.bar(yearly, x="year", y="publications", title="Publication timeline")
        chart.update_traces(marker_color="#6578ed")
        chart.update_layout(xaxis_title=None, yaxis_title="Papers", margin=dict(l=5, r=5, t=44, b=5))
        st.plotly_chart(chart, width="stretch")

    topics = Counter(topic.name for paper in authored for topic in paper.topics)
    keywords = Counter(item.keyword for paper in authored for item in paper.keywords)
    coauthors = Counter(co.name for paper in authored for co in paper.authors if co.id != author.id)
    left, right = st.columns(2)
    with left:
        st.markdown("#### Main research topics")
        for name, count in topics.most_common():
            st.markdown(f"- **{name}** · {count} paper(s)")
        st.markdown("#### Most common keywords")
        for name, count in keywords.most_common(8):
            st.markdown(f"- {name} · {count} paper(s)")
    with right:
        st.markdown("#### Co-author network")
        if coauthors:
            _draw_network(author.name, coauthors)
        else:
            st.caption("No co-author connections have been recorded.")

    st.markdown("#### Publications")
    for paper in reversed(authored):
        with st.container(border=True):
            st.markdown(f"**{paper.title}**")
            st.caption(
                f"{paper.publication_year or 'Year n/a'} · {paper.citation_count:,} citations · "
                f"{', '.join(topic.name for topic in paper.topics)}"
            )


def _draw_network(author_name: str, coauthors: Counter) -> None:
    names = [name for name, _ in coauthors.most_common(8)]
    theta = [2 * math.pi * index / max(1, len(names)) for index in range(len(names))]
    positions = {name: (math.cos(angle), math.sin(angle)) for name, angle in zip(names, theta)}
    edges_x, edges_y = [], []
    for name in names:
        x, y = positions[name]
        edges_x.extend([0, x, None])
        edges_y.extend([0, y, None])
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=edges_x, y=edges_y, mode="lines", line=dict(color="#ccd2f2", width=1.5), hoverinfo="skip"))
    figure.add_trace(
        go.Scatter(
            x=[positions[name][0] for name in names],
            y=[positions[name][1] for name in names],
            mode="markers+text",
            text=names,
            textposition="bottom center",
            marker=dict(size=[13 + min(coauthors[name], 8) * 2 for name in names], color="#6f7fe8"),
            hovertext=[f"{name}: {coauthors[name]} shared paper(s)" for name in names],
            hoverinfo="text",
            name="Co-authors",
        )
    )
    figure.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", text=[author_name], textposition="top center", marker=dict(size=27, color="#24345b"), name="Selected author"))
    figure.update_layout(
        showlegend=False, height=340, xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=18, b=10), plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(figure, width="stretch")