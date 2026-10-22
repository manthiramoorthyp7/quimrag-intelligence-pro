"""Generates every figure used in Research_Paper.docx / Final_Project_Report.docx
from real, logged project data only. Every number here is either read directly
from research/experiments/*.{json,csv} or copy-checked against
research/BASELINE_COMPARISON.md / research/experiments/registry.json -- see the
inline source comment on each constant. No value in this script is invented.

Run with the project's own virtualenv (already has matplotlib/pandas/numpy):
    .venv/bin/python3 deliverables/scripts/make_charts.py
Outputs PNGs to deliverables/figures/.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)

ACCENT = "#6C5CE7"
GOOD = "#1E8E5A"
BAD = "#C0392B"
NEUTRAL = "#6B7280"
BLUE = "#2563EB"

plt.rcParams.update({
    "font.size": 11,
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "#1F2430",
    "text.color": "#1F2430",
    "xtick.color": "#1F2430",
    "ytick.color": "#1F2430",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


def save(fig, name, caption_note=""):
    path = os.path.join(FIG, name)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"wrote {path} {caption_note}")


# ---------------------------------------------------------------------------
# Fig A: Baseline retrieval comparison (nDCG@5), from
# research/BASELINE_COMPARISON.md Table 1 (n=252 evaluation-split queries)
# ---------------------------------------------------------------------------
configs = ["Dense\nonly", "BM25\n(real)", "Hybrid\n(RRF)", "Hybrid +\nrerank",
           "Hybrid +\nrewriting", "Hybrid + rewriting\n+ rerank"]
ndcg5 = [0.477, 0.528, 0.515, 0.574, 0.453, 0.573]
latency = [47.4, 47.5, 52.7, 202.1, 164.8, 327.0]

fig, ax1 = plt.subplots(figsize=(8.5, 4.6))
x = np.arange(len(configs))
bars = ax1.bar(x, ndcg5, color=ACCENT, width=0.55, zorder=3)
ax1.set_ylabel("nDCG@5 (higher is better)")
ax1.set_ylim(0, 0.65)
ax1.set_xticks(x)
ax1.set_xticklabels(configs, fontsize=9.5)
ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
for b, v in zip(bars, ndcg5):
    ax1.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.3f}", ha="center", fontsize=9, fontweight="bold")
ax2 = ax1.twinx()
ax2.plot(x, latency, color=BAD, marker="o", linewidth=2, zorder=4, label="Mean latency (ms)")
ax2.set_ylabel("Mean retrieval latency (ms)", color=BAD)
ax2.tick_params(axis="y", colors=BAD)
ax1.set_title("Retrieval configuration comparison -- OHR-Bench evaluation split, n=252\n(research/BASELINE_COMPARISON.md Table 1)", fontsize=10.5)
save(fig, "fig_baseline_retrieval_comparison.png")

# ---------------------------------------------------------------------------
# Fig B: EAR selective-prediction accuracy by decision group
# research/BASELINE_COMPARISON.md Section 2 table, n=252
# ---------------------------------------------------------------------------
groups = ["answer\n(n=157)", "expand_retrieval\n(n=44)", "abstain\n(n=49)", "all queries\n(unfiltered, n=252)"]
acc = [78.3, 70.5, 49.0, 71.2]
colors = [GOOD, NEUTRAL, BAD, "#374151"]
fig, ax = plt.subplots(figsize=(7.2, 4.6))
bars = ax.bar(groups, acc, color=colors, width=0.55, zorder=3)
ax.axhline(71.2, color="#374151", linestyle=":", linewidth=1.2, zorder=2)
ax.set_ylabel("Top-1 retrieval accuracy (%)")
ax.set_ylim(0, 95)
ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
for b, v in zip(bars, acc):
    ax.text(b.get_x() + b.get_width() / 2, v + 1.3, f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold")
ax.set_title("EAR selective prediction: accuracy by decision group\n(OHR-Bench eval split, n=252; 95% CI on answer-vs-baseline: [+2.5, +12.0] pts)", fontsize=10.5)
save(fig, "fig_ear_selective_accuracy.png")

# ---------------------------------------------------------------------------
# Fig C: RAGAS Faithfulness, baseline vs EAR-gated
# research/experiments/registry.json -> gaps[generation_quality].results
# ---------------------------------------------------------------------------
metrics_names = ["Faithfulness", "Answer\nRelevancy", "Context\nPrecision", "Context\nRecall"]
baseline_vals = [0.5140, 0.6998, 0.7210, 0.4098]
proposed_vals = [0.6189, None, None, None]  # only Faithfulness measured for the EAR-gated condition
fig, ax = plt.subplots(figsize=(7.5, 4.6))
xw = 0.33
xi = np.arange(len(metrics_names))
b1 = ax.bar(xi - xw / 2, baseline_vals, width=xw, color=NEUTRAL, label="Baseline (always generate)", zorder=3)
b2_vals = [proposed_vals[0], 0, 0, 0]
b2 = ax.bar(xi[:1] + xw / 2, [proposed_vals[0]], width=xw, color=GOOD, label="EAR-gated (generate only if not abstained)", zorder=3)
ax.set_xticks(xi)
ax.set_xticklabels(metrics_names)
ax.set_ylabel("RAGAS score (0-1, higher is better)")
ax.set_ylim(0, 0.85)
ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
for b, v in zip(b1, baseline_vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.3f}", ha="center", fontsize=8.5)
ax.text(b2[0].get_x() + b2[0].get_width() / 2, proposed_vals[0] + 0.015, f"{proposed_vals[0]:.3f}", ha="center", fontsize=8.5, fontweight="bold")
ax.legend(fontsize=8.5, loc="upper right")
ax.set_title("RAGAS metrics on this project's own generated answers\n(llama3.2:latest via Ollama, local judge; 60-query sample, no API key used)\nresearch/experiments/registry.json -> generation_quality", fontsize=9.5)
save(fig, "fig_ragas_faithfulness.png")

# ---------------------------------------------------------------------------
# Fig D: RVQ compression vs Recall@5 trade-off
# research/BASELINE_COMPARISON.md Section 3 table
# ---------------------------------------------------------------------------
rvq_labels = ["Exact dense\n(no quantization)", "2-stage,\n256 centroids", "2-stage,\n512 centroids", "4-stage,\n256 centroids", "4-stage,\n512 centroids"]
rvq_recall = [0.378, 0.161, 0.224, 0.261, 0.283]
rvq_compress = [1.0, 768.0, 682.7, 384.0, 341.3]
fig, ax1 = plt.subplots(figsize=(8, 4.8))
xi = np.arange(len(rvq_labels))
bars = ax1.bar(xi, rvq_recall, color=ACCENT, width=0.5, zorder=3)
ax1.set_ylabel("Recall@5 (higher is better)")
ax1.set_ylim(0, 0.45)
ax1.set_xticks(xi)
ax1.set_xticklabels(rvq_labels, fontsize=8.8)
ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
for b, v in zip(bars, rvq_recall):
    ax1.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=9, fontweight="bold")
ax2 = ax1.twinx()
ax2.plot(xi[1:], rvq_compress[1:], color=BAD, marker="D", linewidth=2, label="Compression ratio (x)")
ax2.set_ylabel("Compression ratio (x, log scale)", color=BAD)
ax2.set_yscale("log")
ax2.tick_params(axis="y", colors=BAD)
ax1.set_title("Residual Vector Quantization: compression vs. Recall@5 trade-off\n(OHR-Bench evaluation engine, 16,076 vectors; research/BASELINE_COMPARISON.md Table 3)", fontsize=10)
save(fig, "fig_rvq_tradeoff.png")

# ---------------------------------------------------------------------------
# Fig E: OCR confidence vs CER -- REAL scatter from the 1,589-row per-page log
# research/experiments/ocr_robustness_per_page.csv
# ---------------------------------------------------------------------------
csv_path = os.path.join(ROOT, "research", "experiments", "ocr_robustness_per_page.csv")
df = pd.read_csv(csv_path)
df = df.dropna(subset=["ocr_confidence", "CER"])
fig, ax = plt.subplots(figsize=(7, 5.2))
sev_colors = {"mild": "#2E86DE", "moderate": "#E67E22", "severe": "#C0392B", "clean": "#1E8E5A"}
for sev, g in df.groupby("severity"):
    ax.scatter(g["ocr_confidence"], g["CER"], s=16, alpha=0.55, label=f"{sev} (n={len(g)})",
               color=sev_colors.get(sev, NEUTRAL), edgecolors="none")
# overall Pearson r on the pooled sample actually plotted
r = np.corrcoef(df["ocr_confidence"], df["CER"])[0, 1]
ax.set_xlabel("Tesseract OCR confidence (normalized, 0-1)")
ax.set_ylabel("Character Error Rate (CER)")
ax.set_title(f"OCR confidence vs. measured CER -- real per-page data (n={len(df)})\nPooled Pearson r={r:.3f} (paper reports r=-0.983 on a per-document aggregate)\nresearch/experiments/ocr_robustness_per_page.csv", fontsize=9.5)
ax.legend(fontsize=8.5)
ax.grid(linestyle="--", alpha=0.3)
save(fig, "fig_ocr_confidence_vs_cer.png")

# ---------------------------------------------------------------------------
# Fig F: NDSU substitute-data reproduction -- Recall@5 by method
# research/experiments/registry.json -> gaps[ndsu_reproduction].results
# ---------------------------------------------------------------------------
methods = ["Traditional RAG\n(dense cosine)", "QuIM-style\n(question-indexed)", "This project's\nHybrid (RRF)"]
recall5 = [0.7100, 0.3442, 0.7047]
fig, ax = plt.subplots(figsize=(6.8, 4.6))
bars = ax.bar(methods, recall5, color=[NEUTRAL, BAD, GOOD], width=0.5, zorder=3)
ax.set_ylabel("Recall@5")
ax.set_ylim(0, 0.85)
ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
for b, v in zip(bars, recall5):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.3f}", ha="center", fontsize=10, fontweight="bold")
ax.set_title("Substitute-data reproduction on a disjoint 70-QA-pair sample\n(OHR-Bench manual+textbook domains; research/NDSU_REPRODUCTION_REPORT.md)", fontsize=10)
save(fig, "fig_ndsu_substitute_reproduction.png")

print("\nAll charts generated from real logged data in research/experiments/ and research/*.md.")
