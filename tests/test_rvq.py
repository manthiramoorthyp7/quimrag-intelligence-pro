import numpy as np

from quimrag.rvq import RVQIndex, evaluate_rvq


def _synthetic_embeddings(n=200, dim=16, n_clusters=8, seed=0):
    rng = np.random.default_rng(seed)
    centers = rng.normal(scale=3.0, size=(n_clusters, dim))
    assign = rng.integers(0, n_clusters, n)
    return centers[assign] + rng.normal(scale=0.1, size=(n, dim))


def test_reconstruction_improves_with_more_stages():
    X = _synthetic_embeddings()
    stats1, _ = evaluate_rvq(X, n_stages=1, n_centroids=16)
    stats2, _ = evaluate_rvq(X, n_stages=3, n_centroids=16)
    assert stats2["mse"] < stats1["mse"]
    assert stats2["mean_cosine_to_original"] > stats1["mean_cosine_to_original"]


def test_compression_ratio_decreases_with_more_stages():
    X = _synthetic_embeddings()
    idx1 = RVQIndex(n_stages=1, n_centroids=256).fit(X)
    idx2 = RVQIndex(n_stages=4, n_centroids=256).fit(X)
    assert idx1.compression_ratio(X.shape[1]) > idx2.compression_ratio(X.shape[1])


def test_reconstruct_shape_matches_input():
    X = _synthetic_embeddings(n=50, dim=12)
    idx = RVQIndex(n_stages=2, n_centroids=8).fit(X)
    recon = idx.reconstruct()
    assert recon.shape == X.shape


def test_handles_more_centroids_than_points():
    X = _synthetic_embeddings(n=5, dim=4, n_clusters=2)
    idx = RVQIndex(n_stages=2, n_centroids=256).fit(X)  # should clamp to n points, not crash
    recon = idx.reconstruct()
    assert recon.shape == X.shape
