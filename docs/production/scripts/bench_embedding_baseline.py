"""Phase 1 baseline embedding benchmark: MPS vs CPU throughput for the exact
model/config the app already uses (all-MiniLM-L6-v2 via sentence-transformers).
Real measurement, not a placeholder -- run once now to seed
BASELINE_PERFORMANCE.md, and re-run after any optimization work in Phase 6.

Usage: HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python docs/production/scripts/bench_embedding_baseline.py
"""
import time

import numpy as np
from sentence_transformers import SentenceTransformer

SAMPLE_TEXTS = [
    f"This is sample document chunk number {i} discussing financial statements, "
    f"legal clauses, or technical manual instructions for evaluation purposes. "
    f"It contains enough tokens to resemble a realistic 950-character chunk from "
    f"the ingestion pipeline, repeated with slight variation index {i} to avoid "
    f"trivial caching effects during the throughput measurement run."
    for i in range(256)
]


def bench(device, batch_size, n_warmup=2, n_repeat=5):
    model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    # warm-up (model load, device transfer, kernel compile on MPS)
    for _ in range(n_warmup):
        model.encode(SAMPLE_TEXTS[:batch_size], batch_size=batch_size, show_progress_bar=False)
    latencies = []
    for _ in range(n_repeat):
        t0 = time.perf_counter()
        model.encode(SAMPLE_TEXTS[:batch_size], batch_size=batch_size, show_progress_bar=False)
        latencies.append(time.perf_counter() - t0)
    latencies = np.array(latencies)
    throughput = batch_size / latencies.mean()
    return {
        "device": device, "batch_size": batch_size,
        "mean_s": float(latencies.mean()), "std_s": float(latencies.std()),
        "p50_s": float(np.percentile(latencies, 50)), "p95_s": float(np.percentile(latencies, 95)),
        "throughput_docs_per_s": float(throughput),
    }


if __name__ == "__main__":
    results = []
    for device in ["cpu", "mps"]:
        for bs in [8, 32, 128]:
            r = bench(device, bs)
            results.append(r)
            print(f"[{device:>4}] batch={bs:>4}  mean={r['mean_s']*1000:7.1f}ms  "
                  f"p95={r['p95_s']*1000:7.1f}ms  throughput={r['throughput_docs_per_s']:7.1f} docs/s")
    import json, os
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "embedding_baseline_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {out}")
