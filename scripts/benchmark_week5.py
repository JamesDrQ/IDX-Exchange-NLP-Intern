#!/usr/bin/env python3
"""Benchmark the existing MiniLM + FAISS search path on 10,000 MySQL listings."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LISTING_COUNT = 10_000
WARMUPS = 10
REPETITIONS = 100
TOP_K = 5
TARGET_MS = 100.0
QUERIES = [
    "modern home with a swimming pool",
    "quiet neighborhood with mountain views",
    "spacious backyard for family gatherings",
    "renovated kitchen with a large island",
    "single story house with a three car garage",
]
REPORT = ROOT / "docs/week5_evaluation.md"
SECTION_MARKER = "\n## Week 5 latency benchmark\n"


def replace_report_section(text: str) -> None:
    """Replace this benchmark's section without changing the evaluation above it."""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    existing = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    if SECTION_MARKER in existing:
        existing = existing.split(SECTION_MARKER, 1)[0].rstrip() + "\n"
    REPORT.write_text(existing + text, encoding="utf-8")


def mysql_connection():
    """Use project MySQL environment names with data_loading.py defaults."""
    import mysql.connector

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST") or os.getenv("DB_HOST") or "localhost",
        port=int(os.getenv("MYSQL_PORT") or os.getenv("DB_PORT") or "3306"),
        user=os.getenv("MYSQL_USER") or os.getenv("DB_USER") or "root",
        password=os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD") or "rootpass",
        database=os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME") or "real_estate",
        connection_timeout=5,
    )


def fetch_listings() -> pd.DataFrame:
    connection = mysql_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT L_ListingID, L_Remarks AS remarks "
                "FROM rets_property "
                "WHERE L_Remarks IS NOT NULL AND LENGTH(L_Remarks) > 50 "
                "ORDER BY RAND() LIMIT %s",
                (LISTING_COUNT,),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
    finally:
        connection.close()
    listings = pd.DataFrame(rows, columns=["L_ListingID", "remarks"])
    listings = listings.dropna(subset=["L_ListingID", "remarks"])
    listings["L_ListingID"] = listings["L_ListingID"].astype(str)
    listings["remarks"] = listings["remarks"].astype(str).str.strip()
    listings = listings[listings["remarks"] != ""].reset_index(drop=True)
    if len(listings) != LISTING_COUNT:
        raise RuntimeError(
            f"Database returned {len(listings)} usable listings; {LISTING_COUNT} required"
        )
    return listings


def summarize(samples_ns: list[int]) -> dict[str, float]:
    values = np.asarray(samples_ns, dtype=np.float64) / 1_000_000
    return {
        "median": float(np.median(values)),
        "mean": float(np.mean(values)),
        "p95": float(np.percentile(values, 95)),
    }


def run_benchmark() -> tuple[dict[str, dict[str, float]], int]:
    listings = fetch_listings()
    import faiss
    from scripts.semantic_searcher import SemanticSearcher

    # Reuse SemanticSearcher and its configured model; point it at this run's
    # database sample and a new, independent in-memory FAISS index.
    searcher = SemanticSearcher()
    searcher.df = listings
    texts = listings["remarks"].tolist()
    embeddings = searcher.model.encode(
        texts,
        batch_size=128,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)
    embeddings = np.ascontiguousarray(embeddings)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    searcher.index = index

    query_vectors = {
        query: np.ascontiguousarray(
            searcher.model.encode([query], normalize_embeddings=True).astype(np.float32)
        )
        for query in QUERIES
    }

    # Store the separate benchmark index in an isolated temporary directory;
    # it is removed at exit and cannot replace project indexes.
    with tempfile.TemporaryDirectory(prefix="week5_faiss_benchmark_") as temp_dir:
        index_path = Path(temp_dir) / "week5_10k_faiss.index"
        faiss.write_index(index, str(index_path))
        isolated_index = faiss.read_index(str(index_path))
        if isolated_index.ntotal != LISTING_COUNT:
            raise RuntimeError("Temporary FAISS index size verification failed")
        searcher.index = isolated_index

        # Warm both paths before collecting timed samples.
        for i in range(WARMUPS):
            query = QUERIES[i % len(QUERIES)]
            isolated_index.search(query_vectors[query], TOP_K)
            searcher.search(query, top_k=TOP_K)

        faiss_samples: list[int] = []
        end_to_end_samples: list[int] = []
        for i in range(REPETITIONS):
            query = QUERIES[i % len(QUERIES)]
            vector = query_vectors[query]

            start = time.perf_counter_ns()
            isolated_index.search(vector, TOP_K)
            faiss_samples.append(time.perf_counter_ns() - start)

            start = time.perf_counter_ns()
            searcher.search(query, top_k=TOP_K)
            end_to_end_samples.append(time.perf_counter_ns() - start)

    return {
        "FAISS-only retrieval": summarize(faiss_samples),
        "End-to-end search": summarize(end_to_end_samples),
    }, index.ntotal


def write_unavailable(reason: str) -> None:
    existing = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    if SECTION_MARKER in existing:
        current_section = existing.split(SECTION_MARKER, 1)[1]
        if "Status: completed" in current_section:
            print(
                "A completed benchmark report already exists; preserving it because "
                "this run could not produce a replacement."
            )
            return
    text = (
        SECTION_MARKER + "\n"
        "**Status: Not run.** No latency results are reported because the benchmark "
        "could not obtain and index 10,000 real database listings.\n\n"
        f"Reason: {reason}\n\n"
        "The benchmark requires the project's MySQL connection settings "
        "(`MYSQL_HOST`/`DB_HOST`, `MYSQL_PORT`/`DB_PORT`, `MYSQL_USER`/`DB_USER`, "
        "`MYSQL_PASSWORD`/`DB_PASSWORD`, and optionally `MYSQL_DATABASE`/`DB_NAME`). "
        "When omitted, it uses the defaults in `scripts/data_loading.py`.\n"
    )
    replace_report_section(text)


def write_results(metrics: dict[str, dict[str, float]], count: int) -> None:
    faiss_stats = metrics["FAISS-only retrieval"]
    target = "MEETS" if faiss_stats["p95"] < TARGET_MS else "DOES NOT MEET"
    lines = [
        SECTION_MARKER,
        f"Status: completed using **{count:,} real listings** from MySQL, the existing `SemanticSearcher` MiniLM model, and an isolated `IndexFlatIP` FAISS index. The index and generated vectors were kept in memory/temporary storage and did not overwrite project artifacts.",
        f"Measured {REPETITIONS} repeated searches after {WARMUPS} warm-up searches. Both paths used top-{TOP_K} retrieval and the same five Week 5 queries, cycled evenly. End-to-end time includes query embedding, FAISS retrieval, and result assembly. FAISS-only time uses precomputed query vectors.",
        "",
        "| Measurement | Median (ms) | Mean (ms) | p95 (ms) |",
        "|---|---:|---:|---:|",
    ]
    for name, stats in metrics.items():
        lines.append(
            f"| {name} | {stats['median']:.3f} | {stats['mean']:.3f} | {stats['p95']:.3f} |"
        )
    lines.extend([
        "",
        f"**100 ms FAISS retrieval target:** {target} (based on p95 FAISS-only latency of {faiss_stats['p95']:.3f} ms).",
        "",
    ])
    replace_report_section("\n".join(lines))


def main() -> int:
    try:
        metrics, count = run_benchmark()
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        write_unavailable(reason)
        print(f"Benchmark unavailable: {reason}", file=sys.stderr)
        print(f"Updated report: {REPORT.relative_to(ROOT)}")
        return 1

    write_results(metrics, count)
    print(f"Listings indexed: {count:,}")
    print(f"Warm-ups: {WARMUPS}; timed repeated queries: {REPETITIONS}; top_k: {TOP_K}")
    print("Measurement              Median (ms)  Mean (ms)  p95 (ms)")
    for name, stats in metrics.items():
        print(
            f"{name:<26} {stats['median']:>10.3f}  "
            f"{stats['mean']:>9.3f}  {stats['p95']:>8.3f}"
        )
    print(
        f"100 ms FAISS retrieval target: "
        f"{'MEETS' if metrics['FAISS-only retrieval']['p95'] < TARGET_MS else 'DOES NOT MEET'}"
    )
    print(f"Saved results to {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
