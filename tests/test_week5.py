"""Focused Week 5 tests using tiny deterministic substitutes for heavy backends."""

import importlib
import math
import sys
import types

import numpy as np
import pandas as pd
import pytest


class FakeIndexFlatIP:
    def __init__(self, dimension):
        self.dimension = dimension
        self.vectors = np.empty((0, dimension), dtype=np.float32)
        self.ntotal = 0

    def add(self, vectors):
        assert vectors.shape[1] == self.dimension
        self.vectors = np.concatenate((self.vectors, vectors.copy()), axis=0)
        self.ntotal = len(self.vectors)

    def search(self, queries, k):
        scores = queries @ self.vectors.T
        indices = np.argsort(-scores, axis=1, kind="stable")[:, :k]
        return np.take_along_axis(scores, indices, axis=1), indices


class FakeSentenceTransformer:
    def __init__(self, *_args, **_kwargs):
        pass

    def encode(self, values, **kwargs):
        vectors = []
        for value in values:
            tokens = value.lower().split()
            vectors.append([
                float("pool" in tokens),
                float("modern" in tokens),
            ])
        vectors = np.asarray(vectors, dtype=np.float32)
        if kwargs.get("normalize_embeddings"):
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / np.where(norms == 0, 1, norms)
        return vectors


@pytest.fixture
def searcher_module(monkeypatch):
    faiss_stub = types.ModuleType("faiss")
    faiss_stub.IndexFlatIP = FakeIndexFlatIP
    faiss_stub.normalize_L2 = lambda vectors: vectors.__itruediv__(
        np.linalg.norm(vectors, axis=1, keepdims=True)
    )
    stored = {}
    faiss_stub.write_index = lambda index, path: stored.__setitem__(path, index)
    faiss_stub.read_index = lambda path: stored[path]
    st_stub = types.ModuleType("sentence_transformers")
    st_stub.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "faiss", faiss_stub)
    monkeypatch.setitem(sys.modules, "sentence_transformers", st_stub)
    sys.modules.pop("scripts.semantic_searcher", None)
    module = importlib.import_module("scripts.semantic_searcher")
    yield module, stored
    sys.modules.pop("scripts.semantic_searcher", None)


def test_semantic_search_returns_ranked_listing_results(searcher_module):
    module, _ = searcher_module
    searcher = module.SemanticSearcher.__new__(module.SemanticSearcher)
    searcher.model = FakeSentenceTransformer()
    searcher.df = pd.DataFrame({
        "L_ListingID": ["a", "b"],
        "remarks": ["modern home pool", "quiet cabin"],
    })
    searcher.index = FakeIndexFlatIP(2)
    searcher.index.add(np.asarray([[1, 0], [0, 1]], dtype=np.float32))

    results = searcher.search("modern pool", top_k=1)

    assert results == [{
        "listing_id": "a", "remarks": "modern home pool", "similarity": pytest.approx(1 / math.sqrt(2)),
    }]
    with pytest.raises(ValueError, match="Invalid"):
        searcher.search("  ")
    with pytest.raises(RuntimeError, match="not loaded"):
        searcher.index = None
        searcher.search("pool")


def test_faiss_index_build_normalizes_vectors_and_checks_listing_count(
    searcher_module, monkeypatch
):
    module, stored = searcher_module
    searcher = module.SemanticSearcher.__new__(module.SemanticSearcher)
    searcher.df = pd.DataFrame({"L_ListingID": ["a", "b"]})
    monkeypatch.setattr(module.np, "load", lambda _path: np.asarray([[3, 0], [0, 4]]))

    searcher.build_index()

    assert searcher.index.ntotal == 2
    assert np.allclose(np.linalg.norm(searcher.index.vectors, axis=1), [1, 1])
    assert next(iter(stored.values())).ntotal == 2
    searcher.df = searcher.df.iloc[:1]
    with pytest.raises(ValueError, match="Listing count mismatch"):
        searcher.build_index()


def test_faiss_load_checks_index_listing_count(searcher_module):
    module, stored = searcher_module
    searcher = module.SemanticSearcher.__new__(module.SemanticSearcher)
    searcher.df = pd.DataFrame({"L_ListingID": ["a"]})
    index = FakeIndexFlatIP(2)
    index.add(np.asarray([[1, 0], [0, 1]], dtype=np.float32))
    path = str(module.ROOT / "data/models/week5_faiss.index")
    stored[path] = index

    with pytest.raises(ValueError, match="Index and CSV size mismatch"):
        searcher.load_index()


def test_bm25_search_tokenization_ranking_and_validation():
    from scripts.compare_week5_search import bm25_search, tokenize

    class Scores:
        def get_scores(self, tokens):
            assert tokens == ["modern", "pool"]
            return np.asarray([0.1, 2.0, 1.0])

    df = pd.DataFrame({
        "L_ListingID": ["a", "b", "c"],
        "remarks": ["A", "B", "C"],
    })
    assert tokenize("Modern home, 3-car!") == ["modern", "home", "3", "car"]
    assert [row["listing_id"] for row in bm25_search(df, Scores(), "MODERN pool", 2)] == ["b", "c"]
    with pytest.raises(ValueError, match="Invalid"):
        bm25_search(df, Scores(), "", 2)


def test_precision_and_ndcg_metrics():
    from scripts.evaluate_week5 import dcg, evaluate_group

    group = pd.DataFrame({"rank": [1, 2, 3, 4, 5], "relevance": [2, 1, 2, 0, 0]})
    precision, ndcg = evaluate_group(group)
    expected_ideal_dcg = dcg([2, 2, 1, 0, 0])
    expected_actual_dcg = (3 / math.log2(2) + 1 / math.log2(3) + 3 / math.log2(4))
    assert precision == pytest.approx(0.4)
    assert ndcg == pytest.approx(expected_actual_dcg / expected_ideal_dcg)
    assert dcg([0, 0, 0]) == 0


def test_evaluator_preserves_latency_report_and_identifies_ai_labels(tmp_path, monkeypatch):
    import scripts.evaluate_week5 as evaluator

    rows = []
    for query in ("q1", "q2", "q3", "q4", "q5"):
        for method in ("semantic", "bm25"):
            for rank, relevance in enumerate((2, 1, 0, 0, 0), 1):
                rows.append({"query": query, "method": method, "rank": rank, "relevance": relevance})
    input_path = tmp_path / "labels.csv"
    pd.DataFrame(rows).to_csv(input_path, index=False)
    report_path = tmp_path / "report.md"
    report_path.write_text(
        "Previous results\n\n## Week 5 latency benchmark\n\nFAISS p95 = 0.092 ms.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(evaluator, "INPUT", input_path)
    monkeypatch.setattr(evaluator, "OUTPUT", report_path)

    assert evaluator.main() == 0
    report = report_path.read_text(encoding="utf-8")
    assert "AI-generated judgments" in report
    assert "FAISS p95 = 0.092 ms." in report


def test_latency_summary_reports_milliseconds():
    from scripts.benchmark_week5 import summarize

    summary = summarize([1_000_000, 2_000_000, 9_000_000])
    assert summary["median"] == pytest.approx(2.0)
    assert summary["mean"] == pytest.approx(4.0)
    assert summary["p95"] == pytest.approx(8.3)


def test_failed_benchmark_rerun_preserves_completed_report(tmp_path, monkeypatch):
    import scripts.benchmark_week5 as benchmark

    report = tmp_path / "evaluation.md"
    completed = (
        "Evaluation results\n\n## Week 5 latency benchmark\n\n"
        "Status: completed\n\np95: 0.092 ms\n"
    )
    report.write_text(completed, encoding="utf-8")
    monkeypatch.setattr(benchmark, "REPORT", report)

    benchmark.write_unavailable("simulated missing dependency")

    assert report.read_text(encoding="utf-8") == completed
