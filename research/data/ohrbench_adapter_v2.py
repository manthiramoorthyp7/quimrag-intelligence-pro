"""Corrected OHR-Bench adapter for FINAL_VALIDATION (see
research/FINAL_VALIDATION/EXPERIMENT_PROTOCOL.md for the frozen protocol this
implements). Fixes two issues found during the 2026-10-21 baseline audit:

1. Uses `qas_v2.json` (8,498 records), the file OHR-Bench's own README names
   as current -- the original `ohrbench_adapter.py` used `qas.json` (4,598
   records), an older/non-canonical file. See DATASET_SELECTION.md.
2. Splits calibration/evaluation at the DOCUMENT level, not the query-row
   level -- the original adapter's split_calibration_eval() shuffled and cut
   individual query rows, which left 52/102 calibration documents (51%) also
   present in evaluation (BASELINE_AUDIT.md Section 3). This adapter instead
   shuffles and assigns whole documents, so a document's queries are never
   split across both pools.

Everything else (gt-path resolution, page loading, CSV schema, bulk ingest)
is reused unmodified from the original adapter via import -- this is a
targeted fix, not a rewrite, and the original adapter/its CSVs are left
untouched for historical comparison.
"""
import json
import os
import random
from collections import defaultdict

from ohrbench_adapter import (  # noqa: F401 -- re-exported for callers
    DOMAINS,
    OHRBENCH_ROOT,
    _gt_path,
    ingest_into,
    load_gt_pages,
    unique_documents,
    write_csv,
)

QAS_V2_PATH = os.path.join(OHRBENCH_ROOT, "qas_v2.json")

# qas_v2.json uses a DIFFERENT domain taxonomy than qas.json, found this
# session: it has no "paper" doc_type at all (confirmed: 0 of 8,498 raw
# records) -- the closest conceptual match in v2's own taxonomy is "academic"
# (v2 also adds "administration", not present as a usable domain in v1's
# qas.json; not included here to keep the domain-set SIZE comparable to prior
# work's 6 domains, a deliberate, stated choice, not an oversight).
DOMAINS_V2 = ["law", "finance", "textbook", "manual", "academic", "news"]


def to_eval_rows_v2(qas_subset):
    """Like the original adapter's to_eval_rows(), but handles qas_v2.json's
    richer schema where evidence_page_no may be a LIST of pages (multi-page
    evidence), not just a single int -- found this session when the original
    to_eval_rows() raised a TypeError on the first qas_v2 record with a list
    value. All evidence pages are kept (semicolon-joined), not just the
    first, since quimrag.metrics.parse_relevant already supports multi-page
    relevant_pages strings and dropping pages would understate gold recall."""
    rows = []
    for q in qas_subset:
        raw = q["evidence_page_no"]
        pages = raw if isinstance(raw, list) else [raw]
        relevant_pages = ";".join(f"{q['doc_name']}:{p + 1}" for p in pages)
        rows.append({
            "query": q["questions"],
            "relevant_pages": relevant_pages,
            "doc_type": q["doc_type"],
            "answer_form": q.get("answer_form", ""),
            "answers": q.get("answers", ""),
            "evidence_context": (q.get("evidence_context") or "")[:300],
            "doc_name": q["doc_name"],
        })
    return rows


def load_qas_v2():
    """Same gt-file-existence filter as the original adapter's load_qas(),
    applied to qas_v2.json instead of qas.json. qas_v2.json has no
    `is_extra_qa` field (confirmed BASELINE_AUDIT.md Section 4), so that
    filter is simply absent here, not reinterpreted as always-false."""
    with open(QAS_V2_PATH) as f:
        qas = json.load(f)
    qas = [q for q in qas if q.get("doc_type") in DOMAINS_V2]
    keep = [q for q in qas if os.path.exists(_gt_path(q["doc_type"], q["doc_name"].split("/")[-1]))]
    skipped = len(qas) - len(keep)
    if skipped:
        print(f"[ohrbench_adapter_v2] skipping {skipped} QA pair(s) whose doc_name has no matching gt file")
    return keep


def stratified_subset(qas, per_domain=70, seed=42):
    """Unchanged logic from the original adapter (query-level stratified
    sample) -- the document-level fix happens in split_calibration_eval_by_document
    below, applied AFTER this sampling step, so the overall sample identity
    and size target stays comparable to prior work."""
    rng = random.Random(seed)
    by_domain = defaultdict(list)
    for q in qas:
        by_domain[q["doc_type"]].append(q)
    out = []
    for d in DOMAINS_V2:
        pool = list(by_domain.get(d, []))
        rng.shuffle(pool)
        out.extend(pool[:per_domain])
    rng.shuffle(out)
    return out


def split_calibration_eval_by_document(subset, calib_frac=0.4, seed=42):
    """THE FIX: partitions by doc_name first (shuffled per domain for stratification),
    then assigns ALL of that document's queries to whichever pool it was assigned
    to -- a document's queries are never split across both pools. Returns
    (calib_rows, eval_rows, overlap_report) where overlap_report is a dict of
    the actual achieved document/page overlap (should be zero by construction,
    verified and reported, not assumed)."""
    rng = random.Random(seed)
    by_domain_docs = defaultdict(lambda: defaultdict(list))
    for q in subset:
        by_domain_docs[q["doc_type"]][q["doc_name"]].append(q)

    calib, ev = [], []
    for domain, docs_map in by_domain_docs.items():
        doc_names = list(docs_map.keys())
        rng.shuffle(doc_names)
        total_q = sum(len(v) for v in docs_map.values())
        target_calib_q = int(total_q * calib_frac)
        running = 0
        for dn in doc_names:
            items = docs_map[dn]
            if running < target_calib_q:
                calib.extend(items)
                running += len(items)
            else:
                ev.extend(items)

    def _page_keys(q):
        raw = q["evidence_page_no"]
        pages = raw if isinstance(raw, list) else [raw]
        return [f"{q['doc_name']}:{p}" for p in pages]

    calib_docs = {q["doc_name"] for q in calib}
    eval_docs = {q["doc_name"] for q in ev}
    calib_pages = {pk for q in calib for pk in _page_keys(q)}
    eval_pages = {pk for q in ev for pk in _page_keys(q)}
    overlap_report = {
        "doc_overlap_count": len(calib_docs & eval_docs),
        "page_overlap_count": len(calib_pages & eval_pages),
        "n_calib_docs": len(calib_docs),
        "n_eval_docs": len(eval_docs),
        "n_calib_queries": len(calib),
        "n_eval_queries": len(ev),
    }
    return calib, ev, overlap_report


def build_and_save_v2(out_dir, per_domain=70, calib_frac=0.4, seed=42):
    qas = load_qas_v2()
    subset = stratified_subset(qas, per_domain=per_domain, seed=seed)
    calib, ev, overlap_report = split_calibration_eval_by_document(subset, calib_frac=calib_frac, seed=seed)
    calib_rows, eval_rows = to_eval_rows_v2(calib), to_eval_rows_v2(ev)
    os.makedirs(out_dir, exist_ok=True)
    write_csv(calib_rows, os.path.join(out_dir, "ohrbench_calibration_v2.csv"))
    write_csv(eval_rows, os.path.join(out_dir, "ohrbench_eval_v2.csv"))
    return calib_rows, eval_rows, overlap_report


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    calib_rows, eval_rows, overlap_report = build_and_save_v2(here)
    print(f"calibration: {len(calib_rows)} QA pairs -> {here}/ohrbench_calibration_v2.csv")
    print(f"evaluation:  {len(eval_rows)} QA pairs -> {here}/ohrbench_eval_v2.csv")
    print("overlap report (should be zero/zero):", overlap_report)
    from collections import Counter
    print("calibration domains:", Counter(r["doc_type"] for r in calib_rows))
    print("evaluation domains: ", Counter(r["doc_type"] for r in eval_rows))
