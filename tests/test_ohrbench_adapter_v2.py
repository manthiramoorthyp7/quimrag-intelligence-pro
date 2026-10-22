"""Regression test for the document-level leakage bug found in
research/FINAL_VALIDATION/BASELINE_AUDIT.md (Section 3): the original
calibration/evaluation split was only row-disjoint, not document-disjoint,
which let 51% of calibration documents leak into evaluation. This test
pins down split_calibration_eval_by_document()'s zero-overlap guarantee so
that bug class cannot silently reappear.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "data"))

import ohrbench_adapter_v2 as A2


def _fake_qas(n_docs=20, queries_per_doc=5, domain="law"):
    qas = []
    for d in range(n_docs):
        for q in range(queries_per_doc):
            qas.append({
                "doc_name": f"{domain}_doc_{d}",
                "doc_type": domain,
                "questions": f"question {q} about doc {d}",
                "evidence_page_no": q % 3,
                "answer_form": "Short Answer",
                "answers": "x",
                "evidence_context": "",
            })
    return qas


def test_split_by_document_has_zero_overlap():
    qas = _fake_qas()
    calib, ev, overlap = A2.split_calibration_eval_by_document(qas, calib_frac=0.4, seed=42)
    assert overlap["doc_overlap_count"] == 0
    assert overlap["page_overlap_count"] == 0
    assert len(calib) + len(ev) == len(qas)


def test_split_by_document_never_splits_a_single_document_across_pools():
    qas = _fake_qas(n_docs=12, queries_per_doc=4)
    calib, ev, _ = A2.split_calibration_eval_by_document(qas, calib_frac=0.4, seed=7)
    calib_docs = {q["doc_name"] for q in calib}
    eval_docs = {q["doc_name"] for q in ev}
    assert calib_docs.isdisjoint(eval_docs)
    # every query for a given doc_name lands in exactly one of the two pools
    for doc in calib_docs:
        assert all(q["doc_name"] != doc for q in ev)


def test_split_is_deterministic_given_fixed_seed():
    qas = _fake_qas()
    calib1, ev1, _ = A2.split_calibration_eval_by_document(qas, seed=42)
    calib2, ev2, _ = A2.split_calibration_eval_by_document(qas, seed=42)
    assert [q["doc_name"] for q in calib1] == [q["doc_name"] for q in calib2]
    assert [q["doc_name"] for q in ev1] == [q["doc_name"] for q in ev2]
