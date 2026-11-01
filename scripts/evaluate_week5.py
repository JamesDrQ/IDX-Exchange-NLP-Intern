#!/usr/bin/env python3
"""Evaluate Week 5 Semantic Search and BM25 against labeled relevance judgments."""

from pathlib import Path
import math
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/week5_relevance.csv"
OUTPUT = ROOT / "docs/week5_evaluation.md"
LATENCY_HEADING = "## Week 5 latency benchmark"
EXPECTED_ROWS = 50
METHODS = ("semantic", "bm25")
K = 5


def dcg(relevances: list[int]) -> float:
    """Compute DCG with graded gain 2**relevance - 1."""
    return sum((2**rel - 1) / math.log2(position + 2)
               for position, rel in enumerate(relevances))


def evaluate_group(group: pd.DataFrame) -> tuple[float, float]:
    ranked = group.sort_values("rank", kind="stable").head(K)
    precision = float((ranked["relevance"] == 2).sum()) / K
    actual = ranked["relevance"].astype(int).tolist()
    ideal = sorted(group["relevance"].astype(int).tolist(), reverse=True)[:K]
    ideal_dcg = dcg(ideal)
    ndcg = dcg(actual) / ideal_dcg if ideal_dcg else 0.0
    return precision, ndcg


def main() -> int:
    if not INPUT.exists():
        print(f"Input file not found: {INPUT}", file=sys.stderr)
        return 1

    data = pd.read_csv(INPUT)
    required = {"query", "method", "rank", "relevance"}
    missing = required - set(data.columns)
    if missing:
        print(f"Missing required columns: {', '.join(sorted(missing))}", file=sys.stderr)
        return 1
    if len(data) != EXPECTED_ROWS:
        print(f"Expected {EXPECTED_ROWS} rows, found {len(data)}", file=sys.stderr)
        return 1
    if data["relevance"].isna().any() or not data["relevance"].isin([0, 1, 2]).all():
        invalid = data.loc[data["relevance"].isna() | ~data["relevance"].isin([0, 1, 2]), "relevance"]
        print(f"Invalid relevance labels: {invalid.tolist()}", file=sys.stderr)
        return 1
    if not data["method"].isin(METHODS).all():
        invalid = sorted(data.loc[~data["method"].isin(METHODS), "method"].unique())
        print(f"Unexpected methods: {invalid}", file=sys.stderr)
        return 1

    query_names = list(dict.fromkeys(data["query"].tolist()))
    metrics: dict[str, list[tuple[float, float]]] = {method: [] for method in METHODS}
    for query in query_names:
        for method in METHODS:
            group = data[(data["query"] == query) & (data["method"] == method)]
            if len(group) != K or set(group["rank"].astype(int)) != set(range(1, K + 1)):
                print(f"Expected ranks 1-{K} for query {query!r}, method {method}; found {group['rank'].tolist()}", file=sys.stderr)
                return 1
            metrics[method].append(evaluate_group(group))

    averages = {
        method: (
            sum(p for p, _ in values) / len(values),
            sum(n for _, n in values) / len(values),
        )
        for method, values in metrics.items()
    }
    p_delta = averages["semantic"][0] - averages["bm25"][0]
    n_delta = averages["semantic"][1] - averages["bm25"][1]
    if p_delta > 1e-12 and n_delta > 1e-12:
        comparison_summary = "Semantic Search leads on both metrics"
    elif p_delta < -1e-12 and n_delta < -1e-12:
        comparison_summary = "BM25 leads on both metrics"
    elif p_delta < -1e-12 and n_delta > 1e-12:
        comparison_summary = "Split: BM25 leads Precision@5; Semantic Search leads NDCG@5"
    elif p_delta > 1e-12 and n_delta < -1e-12:
        comparison_summary = "Split: Semantic Search leads Precision@5; BM25 leads NDCG@5"
    else:
        comparison_summary = "Tied on one or both metrics"

    lines = [
        "# Week 5 Search Evaluation",
        "",
        f"Evaluated **{len(data)}** labeled query-result pairs across **{len(query_names)}** queries.",
        "**The relevance labels are AI-generated judgments**, assigned from each query and the full property remarks. They are not human-verified ground truth.",
        "Labels were validated as 0, 1, or 2. Precision@5 counts only label 2 as relevant; NDCG@5 uses graded gain `2^relevance - 1`.",
        "Metrics are calculated per query and averaged equally across five queries. This small, AI-labeled sample limits how broadly these results can be generalized.",
        "The evaluation contains five queries and the top five results per method. These labels are a small sample of retrieved results, not relevance judgments over the full listing corpus.",
        "",
        "| Method | Precision@5 | NDCG@5 |",
        "|---|---:|---:|",
    ]
    for method, display in (("semantic", "Semantic Search"), ("bm25", "BM25")):
        p, n = averages[method]
        lines.append(f"| {display} | {p:.4f} | {n:.4f} |")
    if comparison_summary.startswith("Split:") and p_delta < 0:
        comparison = (
            f"**Comparison:** BM25 has higher Precision@5 by **{-p_delta:.4f}**, "
            f"while Semantic Search has higher NDCG@5 by **{n_delta:.4f}**."
        )
    elif comparison_summary.startswith("Split:"):
        comparison = (
            f"**Comparison:** Semantic Search has higher Precision@5 by **{p_delta:.4f}**, "
            f"while BM25 has higher NDCG@5 by **{-n_delta:.4f}**."
        )
    elif comparison_summary.startswith("Tied"):
        comparison = (
            f"**Comparison:** The methods are tied or split across the metrics. "
            f"Semantic Search minus BM25 is **{p_delta:+.4f}** Precision@5 and **{n_delta:+.4f}** NDCG@5."
        )
    else:
        comparison = (
            f"**Comparison:** {comparison_summary.removesuffix(' leads on both metrics')} performs better on both averages. "
            f"Semantic Search minus BM25 is **{p_delta:+.4f}** Precision@5 and **{n_delta:+.4f}** NDCG@5."
        )
    lines.extend(["", comparison, ""])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    existing = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    latency_section = ""
    if LATENCY_HEADING in existing:
        latency_section = LATENCY_HEADING + existing.split(LATENCY_HEADING, 1)[1]
    OUTPUT.write_text("\n".join(lines) + ("\n" + latency_section if latency_section else ""), encoding="utf-8")
    print("Validation passed: 50 rows, all relevance labels in {0, 1, 2}.")
    print(f"Queries: {len(query_names)}; metrics averaged equally across queries.")
    print("Method            Precision@5  NDCG@5")
    for method, display in (("semantic", "Semantic Search"), ("bm25", "BM25")):
        p, n = averages[method]
        print(f"{display:<17} {p:>11.4f}  {n:.4f}")
    print(f"Comparison: {comparison_summary}; Semantic Search minus BM25: P@5 {p_delta:+.4f}, NDCG@5 {n_delta:+.4f}")
    try:
        output_label = OUTPUT.relative_to(ROOT)
    except ValueError:
        output_label = OUTPUT
    print(f"Saved report: {output_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
