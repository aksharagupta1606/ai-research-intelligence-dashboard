from __future__ import annotations

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Paper
from pages.common import detail_panel, render_paper_card
from services.library_service import ingest_paper
from services.research_api import search_openalex


def render(session: Session) -> None:
    st.title("Research Explorer")
    st.write("Search the local demo collection or look up live metadata in OpenAlex.")
    local_tab, online_tab = st.tabs(["Library search", "Search OpenAlex"])

    with local_tab:
        papers = _load_papers(session)
        topics = sorted({topic.name for paper in papers for topic in paper.topics})
        authors = sorted({author.name for paper in papers for author in paper.authors})
        years = sorted({paper.publication_year for paper in papers if paper.publication_year})
        if st.button("Reset filters", key="reset-explorer", icon=":material/filter_alt_off:"):
            for key in ("explorer_query", "explorer_topic", "explorer_author", "explorer_year", "explorer_keyword", "explorer_citations", "explorer_sort"):
                st.session_state.pop(key, None)
            st.session_state["explorer_page"] = 0
            st.rerun()
        q1, q2, q3 = st.columns([2.2, 1, 1])
        query = q1.text_input("Search title or abstract", key="explorer_query", placeholder="e.g. low-resource language models")
        topic_filter = q2.selectbox("Topic", ["All topics", *topics], key="explorer_topic")
        author_filter = q3.selectbox("Author", ["All authors", *authors], key="explorer_author")
        f1, f2, f3 = st.columns([1, 1.3, 1.3])
        year_filter = f1.selectbox("Publication year", ["All years", *years], key="explorer_year")
        keyword_filter = f2.text_input("Keyword contains", key="explorer_keyword")
        min_cites, max_cites = f3.slider(
            "Citation range",
            0,
            max([paper.citation_count for paper in papers], default=1),
            (0, max([paper.citation_count for paper in papers], default=1)),
            key="explorer_citations",
        )
        sort_by = st.selectbox("Sort", ["Relevance", "Newest first", "Most cited"], key="explorer_sort")
        filtered = []
        for paper in papers:
            content = f"{paper.title} {paper.abstract}".lower()
            if query and query.lower() not in content:
                continue
            if topic_filter != "All topics" and topic_filter not in [item.name for item in paper.topics]:
                continue
            if author_filter != "All authors" and author_filter not in [item.name for item in paper.authors]:
                continue
            if year_filter != "All years" and paper.publication_year != year_filter:
                continue
            if keyword_filter and keyword_filter.lower() not in " ".join(item.keyword for item in paper.keywords).lower():
                continue
            if not min_cites <= paper.citation_count <= max_cites:
                continue
            filtered.append(paper)
        if sort_by == "Newest first":
            filtered.sort(key=lambda item: item.publication_year or 0, reverse=True)
        elif sort_by == "Most cited":
            filtered.sort(key=lambda item: item.citation_count, reverse=True)
        else:
            filtered.sort(key=lambda item: (query.lower() not in item.title.lower(), -item.citation_count))

        page_size = 8
        page_count = max(1, (len(filtered) + page_size - 1) // page_size)
        page_index = min(st.session_state.get("explorer_page", 0), page_count - 1)
        st.session_state["explorer_page"] = page_index
        st.caption(f"{len(filtered)} papers match · Page {page_index + 1} of {page_count}")
        for paper in filtered[page_index * page_size : (page_index + 1) * page_size]:
            render_paper_card(session, paper)
        prev, next_col = st.columns(2)
        if prev.button("Previous", disabled=page_index <= 0, key="explorer-prev"):
            st.session_state["explorer_page"] = page_index - 1
            st.rerun()
        if next_col.button("Next", disabled=page_index >= page_count - 1, key="explorer-next"):
            st.session_state["explorer_page"] = page_index + 1
            st.rerun()
        detail_panel(session)

    with online_tab:
        st.markdown("#### Search OpenAlex")
        st.caption("OpenAlex is a public research-works catalogue. Internet access is required; the local library remains available if it is offline.")
        online_query = st.text_input("Research topic, keyword, or author", key="openalex_query", placeholder="e.g. explainable AI healthcare")
        limit = st.slider("Maximum results", 5, 20, 10, key="openalex_limit")
        if st.button("Search OpenAlex", type="primary", icon=":material/search:"):
            if not online_query.strip():
                st.warning("Enter a topic or keyword to search.")
            else:
                with st.spinner("Searching OpenAlex…"):
                    try:
                        st.session_state["openalex_results"] = search_openalex(online_query, limit)
                        st.session_state.pop("openalex_error", None)
                    except RuntimeError as error:
                        st.session_state["openalex_results"] = []
                        st.session_state["openalex_error"] = str(error)
        if st.session_state.get("openalex_error"):
            st.info(st.session_state["openalex_error"])
        for index, record in enumerate(st.session_state.get("openalex_results", [])):
            with st.container(border=True):
                st.markdown(f"#### {record['title']}")
                st.caption(
                    f"{', '.join(record['authors'][:5]) or 'Author not listed'} · "
                    f"{record['publication_year'] or 'Year n/a'} · "
                    f"{record['citation_count']:,} citations · OpenAlex"
                )
                if record["abstract"]:
                    st.write(record["abstract"][:520] + ("…" if len(record["abstract"]) > 520 else ""))
                if record["doi"]:
                    st.caption(f"DOI: {record['doi']}")
                if record["url"]:
                    st.markdown(f"[Open source record]({record['url']})")
                if st.button("Add to my library", key=f"openalex-import-{index}", icon=":material/library_add:"):
                    paper, created = ingest_paper(session, record)
                    st.session_state["flash_message"] = "Paper added to the library." if created else "This paper is already in the library."
                    st.rerun()


def _load_papers(session: Session) -> list[Paper]:
    return list(
        session.scalars(
            select(Paper).options(
                selectinload(Paper.authors), selectinload(Paper.topics), selectinload(Paper.keywords)
            ).order_by(Paper.publication_year.desc(), Paper.title)
        ).unique()
    )