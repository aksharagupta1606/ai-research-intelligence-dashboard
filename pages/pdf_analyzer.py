from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from database.models import UploadedDocument
from pages.paper_analyzer import _render_analysis_result
from services.ai_service import analyze_paper
from services.pdf_service import extract_pdf


def render(session: Session) -> None:
    st.title("PDF Analyzer")
    st.write("Upload one or more research PDFs to extract selectable text and generate paper analysis.")
    st.caption("PDFs are limited to 25 MB by default. Scanned image-only files need OCR before text analysis.")
    files = st.file_uploader(
        "Upload research PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf-analyzer-uploader",
        help="Corrupted, password-protected, and image-only PDFs are reported without crashing the app.",
    )
    if st.button("Extract and analyze PDFs", type="primary", icon=":material/upload_file:", disabled=not files):
        results = []
        for uploaded in files or []:
            try:
                extracted = extract_pdf(uploaded.getvalue(), uploaded.name)
                document = UploadedDocument(
                    filename=extracted["filename"],
                    file_path="",
                    extracted_text=extracted["text"],
                    word_count=extracted["words"],
                    page_count=extracted["pages"],
                )
                session.add(document)
                session.commit()
                result = {"extracted": extracted, "analysis": None}
                if extracted["text"]:
                    result["analysis"] = analyze_paper(extracted["text"])
                results.append(result)
            except ValueError as error:
                results.append({"extracted": {"filename": uploaded.name, "warning": str(error)}, "analysis": None})
        st.session_state["pdf_analysis_results"] = results
        st.rerun()

    results = st.session_state.get("pdf_analysis_results", [])
    if results:
        st.markdown("### Latest upload results")
        for item in results:
            extracted = item["extracted"]
            with st.container(border=True):
                st.markdown(f"#### {extracted['filename']}")
                if extracted.get("warning"):
                    st.warning(extracted["warning"])
                    continue
                st.caption(f"{extracted['pages']} pages · {extracted['words']:,} words · Stored in local database")
                if item["analysis"]:
                    _render_analysis_result(st, item["analysis"])
                    related = session.query(UploadedDocument).filter_by(filename=extracted["filename"]).order_by(UploadedDocument.uploaded_at.desc()).first()
                    if related:
                        st.caption(f"Document record #{related.id}")

    documents = session.query(UploadedDocument).order_by(UploadedDocument.uploaded_at.desc()).limit(10).all()
    if documents:
        st.markdown("### Previously analyzed PDFs")
        for document in documents:
            with st.expander(f"{document.filename} · {document.page_count} pages · {document.word_count:,} words"):
                st.write(document.extracted_text[:1200] + ("…" if len(document.extracted_text) > 1200 else ""))
                st.caption(f"Uploaded {document.uploaded_at.strftime('%Y-%m-%d %H:%M') if document.uploaded_at else 'recently'}")