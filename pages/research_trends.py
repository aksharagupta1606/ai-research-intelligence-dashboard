from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.orm import Session

from services.analytics_service import all_papers, build_frame


def render(session: Session) -> None:
    st.title("Research Trends")
    st.write("Explore publication activity, topic mix, author output, and citation patterns in the current collection.")
    frame = build_frame(all_papers(session))
    if frame.empty:
        st.info("Add papers to see research trends.")
        return
    years = sorted(int(year) for year in frame.publication_year.dropna().unique())
    min_year, max_year = min(years), max(years)
    col1, col2, col3 = st.columns([1.2, 1, 1])
    selected_years = col1.slider("Year range", min_year, max_year, (min_year, max_year), key="trend_year_range")
    all_topics = sorted({topic for topics in frame.topics for topic in topics})
    topic = col2.selectbox("Topic", ["All topics", *all_topics], key="trend_topic")
    all_authors = sorted({author for authors in frame.authors for author in authors})
    author = col3.selectbox("Author", ["All authors", *all_authors], key="trend_author")
    filtered = frame[
        frame.publication_year.between(selected_years[0], selected_years[1])
        | frame.publication_year.isna()
    ].copy()
    if topic != "All topics":
        filtered = filtered[filtered.topics.apply(lambda values: topic in values)]
    if author != "All authors":
        filtered = filtered[filtered.authors.apply(lambda values: author in values)]
    st.caption(f"Showing {len(filtered)} papers after filters.")
    if filtered.empty:
        st.info("No papers match these filters. Choose a wider year range or another topic.")
        return

    annual = filtered.dropna(subset=["publication_year"]).groupby("publication_year", as_index=False).size()
    publications = px.line(annual, x="publication_year", y="size", markers=True, title="Publications by year")
    publications.update_traces(line_color="#5067e8", marker_size=8)
    publications.update_layout(xaxis_title=None, yaxis_title="Papers", margin=dict(l=5, r=5, t=44, b=5))
    st.plotly_chart(publications, width="stretch")

    topics = filtered.explode("topics").groupby("topics", as_index=False).size().sort_values("size", ascending=False)
    keywords = _frequencies(filtered, "keywords").head(10).sort_values("count")
    authors = _frequencies(filtered, "authors").head(10).sort_values("count")
    row1a, row1b = st.columns(2)
    with row1a:
        chart = px.bar(topics.sort_values("size"), x="size", y="topics", orientation="h", title="Papers by research topic")
        chart.update_traces(marker_color="#8793ef")
        chart.update_layout(xaxis_title="Papers", yaxis_title=None, margin=dict(l=5, r=5, t=44, b=5))
        st.plotly_chart(chart, width="stretch")
    with row1b:
        if not keywords.empty:
            chart = px.bar(keywords, x="count", y="label", orientation="h", title="Top keywords")
            chart.update_traces(marker_color="#43a99a")
            chart.update_layout(xaxis_title="Paper occurrences", yaxis_title=None, margin=dict(l=5, r=5, t=44, b=5))
            st.plotly_chart(chart, width="stretch")
    row2a, row2b = st.columns(2)
    with row2a:
        if not authors.empty:
            chart = px.bar(authors, x="count", y="label", orientation="h", title="Author productivity")
            chart.update_traces(marker_color="#aa85df")
            chart.update_layout(xaxis_title="Papers", yaxis_title=None, margin=dict(l=5, r=5, t=44, b=5))
            st.plotly_chart(chart, width="stretch")
    with row2b:
        chart = px.histogram(filtered, x="citation_count", nbins=14, title="Citation distribution")
        chart.update_traces(marker_color="#e6a55a")
        chart.update_layout(xaxis_title="Citations (demo values are illustrative)", yaxis_title="Papers", margin=dict(l=5, r=5, t=44, b=5))
        st.plotly_chart(chart, width="stretch")

    year_topic = filtered.explode("topics").dropna(subset=["publication_year"])
    if not year_topic.empty:
        trend = year_topic.groupby(["publication_year", "topics"], as_index=False).size()
        chart = px.line(trend, x="publication_year", y="size", color="topics", markers=True, title="Research topic trends")
        chart.update_layout(xaxis_title=None, yaxis_title="Papers", legend_title=None, margin=dict(l=5, r=5, t=44, b=5))
        st.plotly_chart(chart, width="stretch")


def _frequencies(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    counts: dict[str, int] = {}
    for values in frame[column]:
        for value in set(values or []):
            counts[value] = counts.get(value, 0) + 1
    return pd.DataFrame(
        [{"label": label, "count": count} for label, count in counts.items()]
    ).sort_values("count", ascending=False) if counts else pd.DataFrame(columns=["label", "count"])