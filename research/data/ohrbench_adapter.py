"""Adapter for OHR-Bench (Zhang et al., "OCR Hinders RAG," ICCV 2025,
arXiv:2412.02592, opendatalab). Reads the benchmark IN PLACE from a local
clone and never modifies it. Produces a reproducible, stratified QA subset
in the (query, relevant_pages) CSV format quimrag.metrics.parse_relevant
already understands, split into a calibration set (for fitting Evidence-
Adaptive Retrieval's weights/thresholds) and an evaluation set (for
headline numbers) that never overlap.

OHR-Bench page indexing: retrieval_base/gt/<domain>/<stem>.json is a list of
{"text", "page_idx"} with page_idx 0-indexed, and qas.json's evidence_page_no
uses the SAME 0-indexed page_idx (verified directly against the JPMORGAN
10-Q sample: evidence_page_no=24 contains the exact answer text). quimrag's
QuIMRAG.add_document assigns 1-indexed page numbers (enumerate(pages, 1)), so
relevant_pages values here add 1 to evidence_page_no.
"""
import csv
import json
import os
import random
from collections import defaultdict

OHRBENCH_ROOT = os.path.expanduser("~/QuIM-RAG-Project/data/OHR-Bench/data")
DOMAINS = ["law", "finance", "textbook", "manual", "paper", "news"]


def _gt_path(doc_type, stem):
    return os.path.join(OHRBENCH_ROOT, "retrieval_base", "gt", doc_type, f"{stem}.json")


def load_qas():
    """A handful of qas.json records have a doc_name that doesn't match any file under
    retrieval_base/gt/<domain>/ (e.g. doc_name 'textbook/textbook_needrop_en_1574' vs the
    actual file 'jiaocai_needrop_en_1574.json') -- an upstream naming inconsistency in
    OHR-Bench itself. Those are filtered out here rather than fuzzy-matched, since a wrong
    guess would silently pair a question with the wrong document's ground truth."""
    with open(os.path.join(OHRBENCH_ROOT, "qas.json")) as f:
        qas = json.load(f)
    qas = [q for q in qas if not q.get("is_extra_qa", False) and q.get("doc_type") in DOMAINS]
    keep = [q for q in qas if os.path.exists(_gt_path(q["doc_type"], q["doc_name"].split("/")[-1]))]
    skipped = len(qas) - len(keep)
    if skipped:
        print(f"[ohrbench_adapter] skipping {skipped} QA pair(s) whose doc_name has no matching gt file (upstream inconsistency)")
    return keep


def load_gt_pages(doc_type, stem):
    """-> list[str], pages[i] is the ground-truth text of 0-indexed page i (gaps filled with '')."""
    with open(_gt_path(doc_type, stem)) as f:
        data = json.load(f)
    by_idx = {d["page_idx"]: d["text"] for d in data}
    n = max(by_idx) + 1 if by_idx else 0
    return [by_idx.get(i, "") for i in range(n)]


def stratified_subset(qas, per_domain=70, seed=42):
    """Equal-sized sample per domain (not cherry-picked), fixed seed for reproducibility."""
    rng = random.Random(seed)
    by_domain = defaultdict(list)
    for q in qas:
        by_domain[q["doc_type"]].append(q)
    out = []
    for d in DOMAINS:
        pool = list(by_domain.get(d, []))
        rng.shuffle(pool)
        out.extend(pool[:per_domain])
    rng.shuffle(out)
    return out


def split_calibration_eval(subset, calib_frac=0.4, seed=42):
    """Stratified by domain so both splits cover all 6 domains; disjoint by construction."""
    rng = random.Random(seed)
    by_domain = defaultdict(list)
    for q in subset:
        by_domain[q["doc_type"]].append(q)
    calib, ev = [], []
    for items in by_domain.values():
        items = list(items)
        rng.shuffle(items)
        n_c = int(len(items) * calib_frac)
        calib.extend(items[:n_c])
        ev.extend(items[n_c:])
    return calib, ev


def to_eval_rows(qas_subset):
    rows = []
    for q in qas_subset:
        rows.append({
            "query": q["questions"],
            "relevant_pages": f"{q['doc_name']}:{q['evidence_page_no'] + 1}",
            "doc_type": q["doc_type"],
            "answer_form": q.get("answer_form", ""),
            "answers": q.get("answers", ""),
            "evidence_context": (q.get("evidence_context") or "")[:300],
            "doc_name": q["doc_name"],
        })
    return rows


def unique_documents(qas_subset):
    """-> sorted list of (doc_type, stem, doc_name) needed to ingest this subset."""
    seen = {}
    for q in qas_subset:
        seen[q["doc_name"]] = (q["doc_type"], q["doc_name"].split("/")[-1], q["doc_name"])
    return sorted(seen.values())


def ingest_into(engine, qas_subset, progress=None):
    """Bulk-loads every unique document referenced by qas_subset into `engine`
    (a QuIMRAG): embed=False per document, one reindex() at the end -- see
    quimrag/core.py's reindex() docstring for why this matters for runtime."""
    docs = unique_documents(qas_subset)
    loaded = []
    for i, (doc_type, stem, doc_name) in enumerate(docs):
        pages = load_gt_pages(doc_type, stem)
        if pages:
            engine.add_document(doc_name, pages, embed=False)
            loaded.append(doc_name)
        if progress:
            progress((i + 1) / len(docs), doc_name)
    engine.reindex()
    return loaded


def write_csv(rows, path):
    if not rows:
        raise ValueError(f"No rows to write to {path}.")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def build_and_save(out_dir, per_domain=70, calib_frac=0.4, seed=42):
    """Writes ohrbench_calibration.csv and ohrbench_eval.csv to out_dir.
    Returns (calib_rows, eval_rows) for immediate in-process use."""
    qas = load_qas()
    subset = stratified_subset(qas, per_domain=per_domain, seed=seed)
    calib, ev = split_calibration_eval(subset, calib_frac=calib_frac, seed=seed)
    calib_rows, eval_rows = to_eval_rows(calib), to_eval_rows(ev)
    os.makedirs(out_dir, exist_ok=True)
    write_csv(calib_rows, os.path.join(out_dir, "ohrbench_calibration.csv"))
    write_csv(eval_rows, os.path.join(out_dir, "ohrbench_eval.csv"))
    return calib_rows, eval_rows


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    calib_rows, eval_rows = build_and_save(here)
    print(f"calibration: {len(calib_rows)} QA pairs -> {here}/ohrbench_calibration.csv")
    print(f"evaluation:  {len(eval_rows)} QA pairs -> {here}/ohrbench_eval.csv")
    from collections import Counter
    print("calibration domains:", Counter(r["doc_type"] for r in calib_rows))
    print("evaluation domains: ", Counter(r["doc_type"] for r in eval_rows))
