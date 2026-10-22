"""Accurate architecture + EAR decision-flow diagrams, drawn directly from
the real implementation (quimrag/core.py, bm25.py, adaptive.py) and
research/paper/draft.md Section 6 -- NOT from the pre-existing
hybrid_quim_rag_architecture.png, which describes components (NV-Embed-v2,
FAISS, Llama-3-8B via NIM API) that this codebase does not actually use.

Run: .venv/bin/python3 deliverables/scripts/make_diagrams.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)

COLORS = {
    "input": "#F1F0FA", "process": "#E8E4FB", "decision": "#FFF3DC",
    "answer": "#E3F6E8", "abstain": "#FBE4E4", "border": "#4B3F8F",
}


def box(ax, xy, w, h, text, fc, fontsize=9.2, ec="#4B3F8F", lw=1.3, bold=False):
    x, y = xy
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                            linewidth=lw, edgecolor=ec, facecolor=fc, zorder=3)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
             fontweight="bold" if bold else "normal", zorder=4, wrap=True)
    return (x + w / 2, y), (x + w / 2, y + h), (x, y + h / 2), (x + w, y + h / 2)


def arrow(ax, p1, p2, color="#555555", style="-|>", lw=1.4, connectionstyle="arc3,rad=0.0"):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=12, linewidth=lw,
                         color=color, zorder=2, connectionstyle=connectionstyle)
    ax.add_patch(a)


# ===========================================================================
# Diagram 1: End-to-end system architecture (offline indexing + online query)
# ===========================================================================
fig, ax = plt.subplots(figsize=(12.5, 9.2))
ax.set_xlim(0, 12.8)
ax.set_ylim(6.3, 23)
ax.axis("off")
ax.set_title("System architecture: offline document indexing + online query processing\n"
              "(drawn from quimrag/core.py, bm25.py, adaptive.py, rvq.py -- real implementation, not a concept sketch)",
              fontsize=11, fontweight="bold", pad=14)

# -- Offline indexing column --
ax.text(2.6, 22.3, "OFFLINE DOCUMENT INDEXING", ha="center", fontsize=10.5, fontweight="bold", color="#4B3F8F")
b_in = box(ax, (0.6, 20.6), 4, 1.1, "PDF / scanned document", COLORS["input"])
b_ocr = box(ax, (0.6, 18.9), 4, 1.3, "PyMuPDF text layer\nelse Tesseract OCR\n(+ real per-word confidence)", COLORS["process"])
b_chunk = box(ax, (0.6, 17.2), 4, 1.1, "Paragraph/sentence chunking\n(950 chars, 100 overlap)", COLORS["process"])
b_embed = box(ax, (0.6, 15.3), 4, 1.3, "MiniLM embeddings\n(TF-IDF fallback) + real BM25\nindex (rank_bm25.BM25Okapi)", COLORS["process"])
b_rvq = box(ax, (0.6, 13.4), 4, 1.3, "Residual Vector Quantization\n(2-stage k-means, optional)\n341x-768x compression", COLORS["process"])
b_idx = box(ax, (0.6, 11.7), 4, 1.1, "Indexed document store", COLORS["answer"], bold=True)

for a_, b_ in [(b_in, b_ocr), (b_ocr, b_chunk), (b_chunk, b_embed), (b_embed, b_rvq), (b_rvq, b_idx)]:
    arrow(ax, a_[0], b_[1])

# -- Online query column --
ax.text(8.2, 22.3, "ONLINE QUERY PROCESSING", ha="center", fontsize=10.5, fontweight="bold", color="#4B3F8F")
b_q = box(ax, (6.2, 20.6), 4, 1.0, "User query", COLORS["input"])
b_rw = box(ax, (6.2, 19.0), 4, 1.0, "Query rewriting\n(heuristic / optional LLM)", COLORS["process"])
b_ret = box(ax, (6.2, 16.7), 4, 1.7, "Hybrid retrieval\nDense | BM25 | RRF fusion (k=60)\n+ optional cross-encoder rerank", COLORS["process"])
b_ear = box(ax, (6.2, 14.4), 4, 1.7, "Evidence-Adaptive Retrieval &\nVerification (EAR)\n4 signals -> sufficiency score p", COLORS["decision"], bold=True)

arrow(ax, b_q[0], b_rw[1])
arrow(ax, b_rw[0], b_ret[1])
arrow(ax, b_ret[0], b_ear[1])
arrow(ax, b_idx[3], b_ret[2], connectionstyle="arc3,rad=-0.15")

# decision branches -- laid out left-to-right, clear of the offline column (x<4.6)
dy = 12.6
b_abstain = box(ax, (5.3, dy), 1.9, 1.0, "abstain", COLORS["abstain"], fontsize=9, bold=True)
b_answer = box(ax, (7.5, dy), 1.9, 1.0, "answer", COLORS["answer"], fontsize=9, bold=True)
b_expand = box(ax, (9.7, dy), 2.5, 1.0, "expand_retrieval", COLORS["decision"], fontsize=8.6)
b_inspect = box(ax, (9.7, dy - 1.5), 2.9, 1.0, "inspect_structure", COLORS["decision"], fontsize=8.2)

arrow(ax, (b_ear[0][0] - 1.1, dy + 1.0), b_abstain[1], connectionstyle="arc3,rad=0.25")
arrow(ax, (b_ear[0][0] - 0.2, dy + 1.0), b_answer[1], connectionstyle="arc3,rad=0.08")
arrow(ax, (b_ear[0][0] + 0.9, dy + 1.0), b_expand[1], connectionstyle="arc3,rad=-0.15")
arrow(ax, b_expand[0], b_inspect[1], connectionstyle="arc3,rad=0.0")

b_gen = box(ax, (5.2, dy - 2.9), 4.4, 1.3, "LLM (Ollama local, or Anthropic API)\n/ extractive answer + groundedness\npre-check", COLORS["process"])
arrow(ax, b_answer[0], b_gen[1], connectionstyle="arc3,rad=-0.1")
arrow(ax, b_expand[0], (b_ret[0][0]+0.8, 16.7), connectionstyle="arc3,rad=0.35")

b_out = box(ax, (5.2, dy - 4.6), 4.4, 1.1, "Grounded answer with source\ncitations (or abstention notice)", COLORS["answer"], bold=True)
arrow(ax, b_gen[0], b_out[1])

# legend
legend_elems = [
    plt.Rectangle((0,0),1,1, fc=COLORS["input"], ec=COLORS["border"], label="Input"),
    plt.Rectangle((0,0),1,1, fc=COLORS["process"], ec=COLORS["border"], label="Processing stage"),
    plt.Rectangle((0,0),1,1, fc=COLORS["decision"], ec=COLORS["border"], label="EAR decision / branch"),
    plt.Rectangle((0,0),1,1, fc=COLORS["answer"], ec=COLORS["border"], label="Answer path"),
    plt.Rectangle((0,0),1,1, fc=COLORS["abstain"], ec=COLORS["border"], label="Abstain path"),
]
ax.legend(handles=legend_elems, loc="lower center", bbox_to_anchor=(0.5, -0.04), ncol=3, fontsize=8.5, frameon=False)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_system_architecture.png"), dpi=200)
plt.close(fig)
print("wrote fig_system_architecture.png")

# ===========================================================================
# Diagram 2: EAR decision-flow detail (quimrag/adaptive.py::EARModel.decide)
# ===========================================================================
fig, ax = plt.subplots(figsize=(10, 7.5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")
ax.set_title("Evidence-Adaptive Retrieval & Verification (EAR) -- signal computation and decision logic\n(quimrag/adaptive.py, exact implementation)", fontsize=11, fontweight="bold", pad=12)

sig_y = 8.0
sig_w, sig_h = 2.15, 1.3
sig_defs = [
    (0.3, "Agreement a\nJaccard(Dense top-K,\nBM25 top-K)\ncost: 2 retrieve() calls"),
    (2.65, "OCR confidence o\nmean Tesseract word\nconfidence of evidence\ncost: 0 (cached)"),
    (5.0, "Contradiction x\nfraction of evidence pairs:\nsame topic, disjoint numbers\ncost: O(K-sq) regex"),
    (7.35, "Complexity c\nlength / wh-words /\nconjunctions, normalized\ncost: O(query length)"),
]
sig_boxes = []
for x, label in sig_defs:
    b = box(ax, (x, sig_y), sig_w, sig_h, label, COLORS["process"], fontsize=8.0)
    sig_boxes.append(b)

b_logit = box(ax, (2.6, 6.0), 4.8, 1.0, "p = sigmoid(w0 + w1*a + w2*o + w3*x + w4*c)\nweights fit by logistic regression on calibration split", COLORS["decision"], fontsize=9, bold=True)
for b in sig_boxes:
    arrow(ax, b[0], b_logit[1], connectionstyle="arc3,rad=0.0")

b_thresh = box(ax, (2.6, 4.5), 4.8, 1.0, "Compare p to threshold_abstain (20th pct.)\nand threshold_answer (precision >= 0.8)", COLORS["decision"], fontsize=8.8)
arrow(ax, b_logit[0], b_thresh[1])

dy2 = 1.0
dxs = [(0.3, "p < thr_abstain\n-> ABSTAIN\n(no answer)", COLORS["abstain"]),
       (2.7, "thr_abstain <= p < thr_answer,\nweakest=contradiction\n-> INSPECT_STRUCTURE", COLORS["decision"]),
       (5.1, "thr_abstain <= p < thr_answer,\nweakest=other\n-> EXPAND_RETRIEVAL", COLORS["decision"]),
       (7.5, "p >= thr_answer\n-> ANSWER\n(generate + cite)", COLORS["answer"])]
for x, label, c in dxs:
    bb = box(ax, (x, dy2), 2.1, 1.6, label, c, fontsize=8.0, bold=True)
    arrow(ax, (b_thresh[0][0], b_thresh[0][1]), (x + 1.05, dy2 + 1.6), connectionstyle="arc3,rad=0.0")

fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_ear_decision_flow.png"), dpi=200)
plt.close(fig)
print("wrote fig_ear_decision_flow.png")
