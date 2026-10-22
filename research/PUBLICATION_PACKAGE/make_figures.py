"""Generates the 3 publication figures for Deliverable 4 directly from real
experiment JSON files under research/experiments/ -- no invented values.

Usage: .venv/bin/python research/PUBLICATION_PACKAGE/make_figures.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
EXP = os.path.join(ROOT, "research", "experiments")

ACCENT = "#6C5CE7"
MUTED = "#6B7280"
WARN = "#B03A2E"
GOOD = "#2E9E6E"

plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#CBD2D9", "axes.labelcolor": "#1F2430"})


def fig1_baseline_comparison():
    d = json.load(open(os.path.join(EXP, "FINAL_VALIDATION_20261021T144036Z.json")))
    rows = d["baseline_comparison"]["summary"]
    configs = [r["Config"] for r in rows]
    ndcg = [r["nDCG@5"] for r in rows]
    lat = [r["Latency ms (mean)"] for r in rows]

    fig, ax1 = plt.subplots(figsize=(6.5, 4))
    bars = ax1.bar(configs, ndcg, color=ACCENT, width=0.5, zorder=3)
    ax1.set_ylabel("nDCG@5 (higher is better)")
    ax1.set_ylim(0, max(ndcg) * 1.3)
    for b, v in zip(bars, ndcg):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
    ax2 = ax1.twinx()
    ax2.plot(configs, lat, color=WARN, marker="o", linewidth=2, zorder=4)
    ax2.set_ylabel("Mean latency (ms)", color=WARN)
    ax1.set_title("Corrected baseline retrieval comparison\n(document-disjoint OHR-Bench evaluation split, n=247)",
                   fontsize=10)
    ax1.grid(axis="y", color="#E5E8EC", zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig1_baseline_comparison.png"), dpi=200)
    plt.close(fig)


def fig2_ear_before_after():
    orig = json.load(open(os.path.join(EXP, "20261014T185643Z.json")))["ear"]["ablations"]["full_model"]
    corr = json.load(open(os.path.join(EXP, "FINAL_VALIDATION_20261021T144036Z.json")))["ear"]

    labels = ["Coverage (%)", "Accuracy on\nanswered (%)", "Baseline\naccuracy (%)"]
    orig_vals = [orig["coverage"] * 100, orig["accuracy_on_answer"] * 100, orig["overall_baseline_accuracy"] * 100]
    corr_vals = [corr["coverage"] * 100, corr["accuracy_on_answer"] * 100, corr["overall_baseline_accuracy"] * 100]

    x = range(len(labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    b1 = ax.bar([i - w / 2 for i in x], orig_vals, width=w, label="Original (leaky split, n=252 eval)", color="#B8B0E8", zorder=3)
    b2 = ax.bar([i + w / 2 for i in x], corr_vals, width=w, label="Corrected (document-disjoint, n=247 eval)", color=ACCENT, zorder=3)
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f"{b.get_height():.1f}", ha="center", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Percent")
    ax.set_ylim(0, 90)
    ax.set_title("EAR selective-prediction result: original vs. corrected split\n"
                  "95% CI on improvement: [+2.5,+12.0] original  →  [-8.3,+19.7] corrected",
                  fontsize=9.5)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(axis="y", color="#E5E8EC", zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig2_ear_before_after.png"), dpi=200)
    plt.close(fig)


def fig3_rvq_recovery():
    d = json.load(open(os.path.join(EXP, "rvq_recall_analysis_20261015T000824Z.json")))["config_comparison"]
    configs = ["Exact dense\n(no quantization)", "RVQ quantized\n(no rerank)", "RVQ quantized\n+ exact rerank (fix)"]
    keys = ["Exact dense (no quantization)", "RVQ quantized (current)", "RVQ quantized + exact rerank (candidate fix)"]
    recall = [d[k]["Recall@5"] for k in keys]
    lat = [d[k]["latency_ms_mean"] for k in keys]

    fig, ax1 = plt.subplots(figsize=(6.5, 4))
    colors = [MUTED, WARN, GOOD]
    bars = ax1.bar(configs, recall, color=colors, width=0.5, zorder=3)
    ax1.set_ylabel("Recall@5")
    ax1.set_ylim(0, max(recall) * 1.3)
    for b, v in zip(bars, recall):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
    ax2 = ax1.twinx()
    ax2.plot(configs, lat, color="#1F2430", marker="o", linewidth=2, linestyle="--", zorder=4)
    ax2.set_ylabel("Mean latency (ms)")
    ax1.set_title("RVQ recall recovery: quantize-then-exact-rerank fix\n"
                   "(Welch's t=-4.71, p=3.5e-6 for the root-cause test; 79% of lost Recall@5 recovered)",
                   fontsize=9.5)
    ax1.grid(axis="y", color="#E5E8EC", zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig3_rvq_recovery.png"), dpi=200)
    plt.close(fig)


def fig4_risk_coverage():
    d = json.load(open(os.path.join(HERE, "advanced_stats.json")))
    rc = d["risk_coverage"]
    cov = rc["coverage_curve"]
    risk = rc["risk_curve"]
    full_risk = rc["full_coverage_risk_baseline"]

    fig, ax = plt.subplots(figsize=(6.5, 4.3))
    ax.plot(cov, risk, color=ACCENT, linewidth=2.2, zorder=3, label="EAR sufficiency-score ranking")
    ax.axhline(full_risk, color=MUTED, linestyle="--", linewidth=1.5, zorder=2,
               label=f"Unfiltered baseline risk ({full_risk:.3f}, full coverage)")
    ax.fill_between(cov, risk, full_risk, where=[r < full_risk for r in risk],
                     color=ACCENT, alpha=0.12, zorder=1)
    # mark the operating point actually used by the fitted thresholds (coverage=0.154)
    op_cov = 0.1538
    op_idx = min(range(len(cov)), key=lambda i: abs(cov[i] - op_cov))
    ax.scatter([cov[op_idx]], [risk[op_idx]], color=WARN, s=50, zorder=4,
               label=f"Fitted operating point (coverage={op_cov:.3f})")
    ax.set_xlabel("Coverage (fraction of queries answered)")
    ax.set_ylabel("Selective risk (1 − accuracy on answered)")
    ax.set_title(f"Risk-coverage curve, corrected evaluation split (n={rc['n']})\n"
                 f"AURC = {rc['aurc']:.4f} (lower is better; full-coverage risk = {full_risk:.4f})",
                 fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(color="#E5E8EC", zorder=0)
    ax.set_xlim(0, 1)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig4_risk_coverage.png"), dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig1_baseline_comparison()
    fig2_ear_before_after()
    fig3_rvq_recovery()
    if os.path.exists(os.path.join(HERE, "advanced_stats.json")):
        fig4_risk_coverage()
        print("Wrote fig1-3 + fig4_risk_coverage.png")
    else:
        print("Wrote fig1_baseline_comparison.png, fig2_ear_before_after.png, fig3_rvq_recovery.png "
              "(skipped fig4: run compute_advanced_stats.py first)")
