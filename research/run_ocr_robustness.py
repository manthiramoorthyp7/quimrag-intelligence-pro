"""Gap B: OCR robustness controlled degradation study.

Takes real, human-verified ground-truth text from OHR-Bench, renders it to a
clean page image, applies graduated SYNTHETIC degradation (blur, resolution
loss, skew, JPEG compression, noise, contrast reduction -- see
research/data/ocr_degradation.py), and runs each condition through the
PROJECT'S REAL OCR pipeline (quimrag.core._ocr_page, the same function used
in production, including the same contrast/median-filter preprocessing
extract_pdf applies). Measures: CER/WER vs. the real reference text, real
Tesseract confidence, whether confidence actually correlates with CER, and
the downstream effect on retrieval and on EAR's ocr_confidence signal when
it finally has real noise variance to learn from.

IMPORTANT: degradation here is synthetic image corruption of real text, not
genuine scanner/camera-captured noise. That is stated as a limitation, not
hidden -- see the report's "what this does and does not prove" section.

Usage: .venv/bin/python research/run_ocr_robustness.py
"""
import datetime
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, ROOT + "/data")

import numpy as np
import pandas as pd
from PIL import ImageEnhance, ImageFilter, ImageOps

import ohrbench_adapter as A
from ocr_degradation import SEVERITIES, degrade, render_text_page
from quimrag.core import QuIMRAG, _ocr_page
from quimrag import adaptive as EAR
from quimrag import metrics as M
from quimrag import ocr_eval
from quimrag_ui.registry import update_gap

N_PER_DOMAIN = 3   # kept small: each doc needs 4 OCR passes (clean handled separately) x real Tesseract calls
SEED = 7


_LATEX_RE = re.compile(r"\\[a-zA-Z]+|\\\$")


def _is_renderable_prose(text, max_latex_density=0.01, min_len=200, max_len=2200):
    """OHR-Bench's ground truth for table/formula-heavy pages is literal LaTeX
    markup (e.g. '\\begin{tabular}...'), not prose -- rendering that onto a
    single page via insert_textbox silently overflows and produces garbage
    neither a real scan nor real OCR would resemble. This filters the sample
    to pages that are genuinely renderable prose, so degradation (not a
    rendering artifact) is what's actually being measured."""
    if not (min_len < len(text) < max_len):
        return False
    density = len(_LATEX_RE.findall(text)) / len(text)
    return density < max_latex_density


def select_sample():
    qas = A.load_qas()
    by_domain = {}
    for q in qas:
        by_domain.setdefault(q["doc_type"], []).append(q)
    import random
    rng = random.Random(SEED)
    sample = []
    skipped_not_prose = 0
    for d, items in by_domain.items():
        items = list(items)
        rng.shuffle(items)
        seen_docs = set()
        for q in items:
            if q["doc_name"] in seen_docs:
                continue
            pages = A.load_gt_pages(q["doc_type"], q["doc_name"].split("/")[-1])
            idx = q["evidence_page_no"]
            if idx >= len(pages) or not _is_renderable_prose(pages[idx]):
                skipped_not_prose += 1
                continue
            seen_docs.add(q["doc_name"])
            sample.append(q)
            if len(seen_docs) >= N_PER_DOMAIN:
                break
    print(f"skipped {skipped_not_prose} candidate pages that were table/formula-markup, not renderable prose")
    return sample


def real_pipeline_preprocess(im):
    """Exactly the preprocessing extract_pdf applies before OCR -- so this
    experiment tests the real pipeline, not a stripped-down OCR call."""
    return ImageEnhance.Contrast(ImageOps.autocontrast(im.filter(ImageFilter.MedianFilter()))).enhance(1.25)


def main():
    sample = select_sample()
    print(f"selected {len(sample)} (document, page) pairs across {len(set(q['doc_type'] for q in sample))} domains")

    # ---- Stage 1: per-page degradation + real OCR + CER/WER -------------
    page_records = []  # one per (doc, condition)
    for q in sample:
        doc_type, stem, doc_name = q["doc_type"], q["doc_name"].split("/")[-1], q["doc_name"]
        pages = A.load_gt_pages(doc_type, stem)
        page_idx = q["evidence_page_no"]
        if page_idx >= len(pages) or not pages[page_idx].strip():
            continue
        clean_text = pages[page_idx]
        im = render_text_page(clean_text)

        for severity in SEVERITIES:
            degraded = degrade(im, severity, seed=SEED)
            t0 = time.time()
            prepped = real_pipeline_preprocess(degraded)
            ocr_text, conf = _ocr_page(prepped)
            ocr_ms = (time.time() - t0) * 1000
            row = ocr_eval.evaluate_pages([(f"{doc_name}:{page_idx}:{severity}", clean_text, ocr_text)])[0]
            page_records.append({
                "doc_name": doc_name, "doc_type": doc_type, "page_idx": page_idx, "severity": severity,
                "query": q["questions"], "ocr_text": ocr_text, "clean_text": clean_text,
                "ocr_confidence": conf, "CER": row["CER"], "WER": row["WER"], "ocr_ms": ocr_ms,
            })
        print(f"  {doc_name} p.{page_idx}: " + ", ".join(
            f"{r['severity']}=CER{r['CER']*100:.0f}%/conf{(r['ocr_confidence'] or 0)*100:.0f}%"
            for r in page_records if r["doc_name"] == doc_name))

    pr = pd.DataFrame(page_records)
    pr.to_csv(os.path.join(ROOT, "experiments", "ocr_robustness_per_page.csv"), index=False)

    # ---- Stage 2: does confidence correlate with actual CER? ------------
    from scipy.stats import pearsonr, spearmanr
    valid = pr.dropna(subset=["ocr_confidence"])
    if len(valid) > 2:
        pearson_r, pearson_p = pearsonr(valid["ocr_confidence"], valid["CER"])
        spearman_r, spearman_p = spearmanr(valid["ocr_confidence"], valid["CER"])
    else:
        pearson_r = pearson_p = spearman_r = spearman_p = float("nan")
    print(f"\nconfidence-vs-CER correlation: Pearson r={pearson_r:.3f} (p={pearson_p:.4g}), "
          f"Spearman rho={spearman_r:.3f} (p={spearman_p:.4g})")
    print("(negative r is the EXPECTED direction: higher confidence should mean lower error)")

    by_sev = pr.groupby("severity")[["CER", "WER", "ocr_confidence"]].mean()
    print("\nmean CER/WER/confidence by severity:\n", by_sev)

    # ---- Stage 3: downstream retrieval impact per condition -------------
    print("\nbuilding per-condition retrieval engines...")
    retrieval_results = {}
    for condition in ["clean"] + SEVERITIES:
        e = QuIMRAG()
        rows_for_eval = []
        for doc_name in pr["doc_name"].unique():
            doc_rows = pr[pr["doc_name"] == doc_name]
            if condition == "clean":
                text, meta = doc_rows.iloc[0]["clean_text"], {"source": "native", "ocr_confidence": None}
            else:
                dr = doc_rows[doc_rows["severity"] == condition]
                if dr.empty:
                    continue
                text, meta = dr.iloc[0]["ocr_text"], {"source": "ocr", "ocr_confidence": dr.iloc[0]["ocr_confidence"]}
            page_idx = int(doc_rows.iloc[0]["page_idx"])
            pages = [""] * page_idx + [text]
            page_meta = [{"source": "native", "ocr_confidence": None}] * page_idx + [meta]
            e.add_document(doc_name, pages, page_meta, embed=False)
            rows_for_eval.append({"query": doc_rows.iloc[0]["query"], "relevant_pages": f"{doc_name}:{page_idx+1}"})
        e.reindex()
        df_eval = pd.DataFrame(rows_for_eval)
        res = M.evaluate(e, df_eval, k=3, mode="Hybrid")
        retrieval_results[condition] = {
            "n_docs": len(e.documents), "n_scored": int(len(res)),
            "Recall@3": float(res["Recall@3"].mean()) if not res.empty else None,
            "nDCG@3": float(res["nDCG@3"].mean()) if not res.empty else None,
        }
        print(f"  {condition}: {retrieval_results[condition]}")

    # ---- Stage 4: does ocr_confidence become informative once it has real variance? ----
    print("\nbuilding mixed clean+degraded calibration set for EAR...")
    e_mix = QuIMRAG()
    mix_rows = []
    for doc_name in pr["doc_name"].unique():
        doc_rows = pr[pr["doc_name"] == doc_name]
        page_idx = int(doc_rows.iloc[0]["page_idx"])
        for condition in ["clean", "mild", "moderate"]:  # hold out "severe" for the held-out check below
            if condition == "clean":
                text, meta = doc_rows.iloc[0]["clean_text"], {"source": "native", "ocr_confidence": None}
            else:
                dr = doc_rows[doc_rows["severity"] == condition]
                if dr.empty:
                    continue
                text, meta = dr.iloc[0]["ocr_text"], {"source": "ocr", "ocr_confidence": dr.iloc[0]["ocr_confidence"]}
            variant_name = f"{doc_name}::{condition}"
            pages = [""] * page_idx + [text]
            page_meta = [{"source": "native", "ocr_confidence": None}] * page_idx + [meta]
            e_mix.add_document(variant_name, pages, page_meta, embed=False)
            mix_rows.append({"query": doc_rows.iloc[0]["query"], "relevant_pages": f"{variant_name}:{page_idx+1}"})
    e_mix.reindex()
    mix_df = pd.DataFrame(mix_rows)
    X, y = EAR.build_training_data(e_mix, mix_df, k=3)
    if len(X) > 5 and len(set(y)) > 1:
        model = EAR.EARModel().fit(X, y)
        new_weight = dict(zip(EAR.FEATURES, model.coef))
    else:
        model, new_weight = None, None
    print("EAR weights recalibrated on mixed clean+degraded data:", new_weight)

    old_weight = None
    old_path = os.path.join(PROJECT_ROOT, "research", "data", "ear_calibration.json")
    if os.path.exists(old_path):
        old = json.load(open(old_path))
        old_weight = dict(zip(old["features"], old["coef"]))

    run_id = "ocr_robustness_" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out = {
        "run_id": run_id,
        "sample_size": len(pr["doc_name"].unique()),
        "n_conditions": len(SEVERITIES) + 1,
        "confidence_vs_cer_correlation": {
            "pearson_r": pearson_r, "pearson_p": pearson_p, "spearman_r": spearman_r, "spearman_p": spearman_p,
        },
        "mean_by_severity": by_sev.reset_index().to_dict(orient="records"),
        "retrieval_by_condition": retrieval_results,
        "ear_weight_on_clean_ground_truth": old_weight,
        "ear_weight_on_mixed_clean_degraded": new_weight,
    }
    out_path = os.path.join(ROOT, "experiments", f"{run_id}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nWrote {out_path}")

    update_gap("ocr_robustness", status="done",
               dataset=f"{len(pr['doc_name'].unique())} OHR-Bench documents, text rendered then synthetically degraded "
                       f"at 3 severities + clean baseline (4 conditions)",
               sample_count=int(len(pr)),
               results={
                   "pearson_r_confidence_vs_cer": pearson_r, "pearson_p": pearson_p,
                   "mean_cer_clean": None, "mean_cer_mild": float(by_sev.loc["mild", "CER"]) if "mild" in by_sev.index else None,
                   "mean_cer_moderate": float(by_sev.loc["moderate", "CER"]) if "moderate" in by_sev.index else None,
                   "mean_cer_severe": float(by_sev.loc["severe", "CER"]) if "severe" in by_sev.index else None,
                   "retrieval_recall_at_3_by_condition": {k: v.get("Recall@3") for k, v in retrieval_results.items()},
                   "ear_ocr_confidence_weight_clean_only": old_weight.get("ocr_confidence") if old_weight else None,
                   "ear_ocr_confidence_weight_mixed": new_weight.get("ocr_confidence") if new_weight else None,
               },
               uncertainty=f"Pearson correlation p={pearson_p:.4g} (n={len(valid)}); small sample, see report for caveats.",
               limitations="Degradation is SYNTHETIC image corruption of real text, not genuine scanner noise. "
                           "Small sample (~18 documents) relative to the full OHR-Bench corpus, and restricted to pages "
                           "whose ground truth is prose-renderable (table/formula-markup pages were excluded -- rendering "
                           "literal LaTeX table syntax onto a page and OCR'ing it is not a meaningful OCR-noise simulation, "
                           "an issue found and fixed during this run; see the report). Retrieval engines here index one "
                           "page per document (not full multi-page documents) to isolate the OCR-condition effect.",
               reproduce_command=".venv/bin/python research/run_ocr_robustness.py",
               )
    print("Updated registry.json for gap: ocr_robustness")


if __name__ == "__main__":
    main()
