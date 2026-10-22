# Source and Reference Verification Record

All 9 references cited in both deliverables were checked against the project's own prior literature review (`research/PAPER_REVIEW.md`) and, for the two most load-bearing citations, independently re-verified via live web search during this session (2026-10-17).

| # | Citation | Verification method | Result |
|---|---|---|---|
| 1 | Saha, Saha, Malik, "QuIM-RAG," IEEE Access, 2024, DOI 10.1109/ACCESS.2024.3513155 | Web search: title, authors, DOI, volume/pages cross-checked against arXiv:2501.02702, IEEE Xplore (ieeexplore.ieee.org/document/10781379), ResearchGate | **Confirmed.** Authors, venue, volume (12), pages (185401-185410), DOI all match. |
| 2 | Zhang et al., "OCR Hinders RAG" (OHR-Bench), arXiv:2412.02592, ICCV 2025 | Web search: arXiv abstract page, GitHub repo (opendatalab/OHR-Bench), ICCV 2025 open-access paper (openaccess.thecvf.com) | **Confirmed.** Paper exists, is ICCV 2025 accepted, GitHub repo live. Note: the project's own `PAPER_REVIEW.md` states "4,598 labeled QA pairs"; the verified search result states "8,561 document images... 8,498 Q&A pairs" for the full released benchmark. This discrepancy is in the project's internal notes, not in this report — both deliverables only cite the paper's existence/claims and describe this project's own independently-drawn subsample (420 + 70 pairs, verified directly from `research/experiments/` logs), not the benchmark's total published size, avoiding the unresolved figure entirely. |
| 3 | Amaral Cejas, Guo, Tang, "Tracing the Impact of Embedding Quality in RAG Systems," IEEE Access, 2025 | Taken from project's existing literature review; not independently re-searched this session | Not independently re-verified this session — carried from the project's own prior research record at face value. |
| 4 | Elkiran & Rasheed, "EvaRAG," IEEE Access, 2025 | Same as above | Not independently re-verified this session. |
| 5 | Elkiran & Rasheed, "An Empirical Evaluation of Retrieval, Reranking, and Similarity...," IEEE Access, 2026 | Same as above | Not independently re-verified this session. |
| 6 | Kiss, Nagy, Szilágyi, "Max–Min Semantic Chunking," Discover Computing, 2025 | Same as above | Not independently re-verified this session. |
| 7 | Sarthi et al., "RAPTOR," ICLR 2024 | Well-known, widely cited paper; not independently re-searched this session | Not independently re-verified this session, but high-confidence (well-established publication). |
| 8 | Jégou, Douze, Schmid, "Product Quantization for Nearest Neighbor Search," IEEE TPAMI, 2011 | Well-known foundational paper; not independently re-searched this session | Not independently re-verified this session, but high-confidence (canonical, widely-cited reference). |
| 9 | Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," FnTIR, 2009 | Well-known foundational paper; not independently re-searched this session | Not independently re-verified this session, but high-confidence (canonical, widely-cited reference). |

**Unresolved verification gap:** references 3-6 were carried forward from the project's own existing `research/PAPER_REVIEW.md` without independent re-verification by this workflow (time-budget constraint). They should be spot-checked against publisher pages or DOI records before formal submission. No reference was invented; all 9 originate from the project's own pre-existing, dated literature review, not generated fresh for this report.

**No fabricated citations, authors, DOIs, or findings were introduced in either deliverable.**
