"""Residual Vector Quantization (RVQ) over the chunk embedding matrix: a
2-stage quantizer (k-means on the raw vectors, then k-means on the stage-1
residuals) that approximates each embedding with two small integer codes
instead of a 384-dim float32 vector. Closes the RVQ item on the project's
own roadmap (PROJECT_SCOPE.md). This is an educational-grade implementation
(plain sklearn KMeans, not a production ANN library) -- see
research/BASELINE_COMPARISON.md for the measured compression/reconstruction/
recall tradeoffs on our actual corpus, not assumed ones."""
import math

import numpy as np


class RVQIndex:
    def __init__(self, n_stages=2, n_centroids=256, seed=0):
        self.n_stages = n_stages
        self.n_centroids = n_centroids
        self.seed = seed
        self.codebooks = []  # one (n_centroids_used, dim) array per stage
        self.codes = None  # (n_chunks, n_stages) int array

    def fit(self, matrix):
        from sklearn.cluster import KMeans
        X = np.asarray(matrix, dtype=np.float64)
        residual = X.copy()
        self.codebooks = []
        codes = []
        for s in range(self.n_stages):
            k = max(1, min(self.n_centroids, len(residual)))
            km = KMeans(n_clusters=k, random_state=self.seed + s, n_init=4).fit(residual)
            self.codebooks.append(km.cluster_centers_)
            codes.append(km.labels_)
            residual = residual - km.cluster_centers_[km.labels_]
        self.codes = np.stack(codes, axis=1)
        return self

    def reconstruct(self):
        """-> (n_chunks, dim) approximate embeddings: sum of each stage's assigned centroid."""
        dim = self.codebooks[0].shape[1]
        out = np.zeros((self.codes.shape[0], dim))
        for s in range(self.n_stages):
            out += self.codebooks[s][self.codes[:, s]]
        return out

    def compression_ratio(self, dim):
        """Raw: dim*4 bytes (float32) per vector. Quantized: n_stages codes,
        each ceil(log2(n_centroids)) bits."""
        bits_per_code = max(1, math.ceil(math.log2(max(2, self.n_centroids))))
        raw_bytes = dim * 4
        q_bytes = self.n_stages * bits_per_code / 8
        return raw_bytes / q_bytes


def evaluate_rvq(matrix, n_stages=2, n_centroids=256, seed=0):
    """Fits an RVQIndex and reports reconstruction MSE, mean cosine similarity
    between original and reconstructed vectors, and compression ratio --
    all measured directly, not assumed."""
    X = np.asarray(matrix, dtype=np.float64)
    idx = RVQIndex(n_stages, n_centroids, seed).fit(X)
    recon = idx.reconstruct()
    mse = float(np.mean((X - recon) ** 2))
    norms_x = np.linalg.norm(X, axis=1)
    norms_r = np.linalg.norm(recon, axis=1)
    denom = np.where((norms_x * norms_r) == 0, 1.0, norms_x * norms_r)
    cos = (X * recon).sum(axis=1) / denom
    return {
        "mse": mse,
        "mean_cosine_to_original": float(cos.mean()),
        "compression_ratio": idx.compression_ratio(X.shape[1]),
        "n_stages": n_stages, "n_centroids": n_centroids,
    }, idx


def _embed_query(engine, q):
    if engine.model:
        qv = engine.model.encode([q], normalize_embeddings=True)
    else:
        qv = engine.vectorizer.transform([q]).toarray()
    return np.asarray(qv, dtype=np.float64)[0]


def _cosine_scores(qv, matrix):
    denom = np.linalg.norm(qv) * np.linalg.norm(matrix, axis=1)
    denom = np.where(denom == 0, 1.0, denom)
    return (matrix @ qv) / denom


def make_quantized_retriever(engine, idx):
    """Returns f(query, k) -> list[dict] (same shape as engine.retrieve()'s
    output) that ranks by cosine similarity against RVQ-RECONSTRUCTED corpus
    vectors instead of the raw float32 matrix -- the realistic ANN use case
    (corpus compressed for storage, query embedded fresh, full precision)."""
    recon = idx.reconstruct()

    def f(q, k):
        qv = _embed_query(engine, q)
        scores = _cosine_scores(qv, recon)
        ids = np.argsort(-scores)[:k]
        return [dict(engine.chunks[i], score=float(scores[i]), method="RVQ quantized dense") for i in ids]

    return f


def make_quantized_rerank_retriever(engine, idx, candidate_pool=50):
    """Two-stage retriever: cheap quantized-score narrowing to `candidate_pool`
    candidates, then EXACT cosine rerank of just that candidate pool using the
    raw float32 matrix. This is the standard coarse-quantize-then-exact-rerank
    pattern (as in FAISS IVF-PQ + reranking) -- it requires keeping exact
    vectors on hand for reranking, so it is a latency/accuracy tradeoff
    against the pure quantized retriever above, not a free win; see
    research/RVQ_RECALL_ANALYSIS.md for the measured tradeoff."""
    recon = idx.reconstruct()
    exact = np.asarray(engine.matrix, dtype=np.float64)

    def f(q, k):
        qv = _embed_query(engine, q)
        approx_scores = _cosine_scores(qv, recon)
        pool = np.argsort(-approx_scores)[:max(candidate_pool, k)]
        exact_scores_pool = _cosine_scores(qv, exact[pool])
        order = np.argsort(-exact_scores_pool)[:k]
        ids = pool[order]
        return [dict(engine.chunks[i], score=float(exact_scores_pool[j]), method="RVQ quantized + exact rerank")
                for j, i in zip(order, ids)]

    return f
