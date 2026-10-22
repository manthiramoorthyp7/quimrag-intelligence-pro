import pandas as pd
import streamlit as st

from quimrag.core import extract_pdf
from quimrag_ui.components import empty_state, note, section, stat_row
from quimrag_ui.state import engine, init_state
from quimrag_ui.theme import page_header


def render():
    init_state()
    e = engine()
    page_header("Document Intelligence Studio", "Ingestion, extraction and chunk inspection",
                "PDF upload, OCR fallback with real per-word confidence, and the page/chunk explorer.")

    section("Add PDF documents")
    uploads = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True, label_visibility="collapsed")
    ocr = st.toggle("OCR scanned pages", True)
    st.caption("OCR requires Tesseract installed separately (macOS: `brew install tesseract`).")
    if uploads and st.button("Process and index", type="primary"):
        bar = st.progress(0)
        msg = st.empty()
        for i, f in enumerate(uploads):
            msg.write(f"Processing {f.name}…")
            pages, notes, page_meta = extract_pdf(f.getvalue(), ocr)
            e.add_document(f.name, pages, page_meta)
            if notes:
                st.warning("\n".join(notes))
            bar.progress((i + 1) / len(uploads))
        msg.success("Indexing complete.")

    if e.documents:
        section("Indexed documents")
        rows = []
        for n, p in e.documents.items():
            doc_chunks = [c for c in e.chunks if c["document"] == n]
            ocr_pages = sum(1 for c in doc_chunks if c.get("source") == "ocr")
            confs = [c["ocr_confidence"] for c in doc_chunks if c.get("ocr_confidence") is not None]
            rows.append({
                "Document": n, "Pages": len(p), "Chunks": len(doc_chunks),
                "OCR chunks": ocr_pages,
                "Mean OCR confidence": f"{sum(confs)/len(confs)*100:.0f}%" if confs else "—",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        empty_state("No documents indexed", "Upload one or more PDFs above to get started.")
        return

    section("Document structure", "Extracted page text, chunk boundaries and OCR confidence per chunk")
    name = st.selectbox("Document", list(e.documents))
    pg = st.select_slider("Page", options=list(range(1, len(e.documents[name]) + 1)))
    st.text_area("Extracted page text", e.documents[name][pg - 1], height=140, disabled=True)

    chunks = [c for c in e.chunks if c["document"] == name and c["page"] == pg]
    if not chunks:
        note("No chunks on this page (likely empty extracted text).")
    for c in chunks:
        if c.get("source") == "ocr" and c.get("ocr_confidence") is not None:
            tag = f" · OCR, confidence {c['ocr_confidence']*100:.0f}%"
        elif c.get("source") == "ocr":
            tag = " · OCR (confidence unavailable)"
        else:
            tag = " · native text"
        with st.expander(f"{c['chunk_id']} · {len(c['text'])} characters{tag}"):
            st.text(c["text"])

    section("Extraction diagnostics")
    total_ocr = sum(1 for c in e.chunks if c.get("source") == "ocr")
    total_failed = sum(1 for c in e.chunks if c.get("source") == "ocr_failed")
    confs = [c["ocr_confidence"] for c in e.chunks if c.get("ocr_confidence") is not None]
    stat_row([
        ("Native-text chunks", sum(1 for c in e.chunks if c.get("source") == "native"), None),
        ("OCR'd chunks", total_ocr, None),
        ("OCR failures", total_failed, "see page warnings above" if total_failed else None),
        ("Mean OCR confidence", f"{sum(confs)/len(confs)*100:.0f}%" if confs else "n/a (no OCR'd pages)", None),
    ])
