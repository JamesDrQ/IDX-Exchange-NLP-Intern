# Week 5 Search Evaluation

Evaluated **50** labeled query-result pairs across **5** queries.
**The relevance labels are AI-generated judgments**, assigned from each query and the full property remarks. They are not human-verified ground truth.
Labels were validated as 0, 1, or 2. Precision@5 counts only label 2 as relevant; NDCG@5 uses graded gain `2^relevance - 1`.
Metrics are calculated per query and averaged equally across five queries. This small, AI-labeled sample limits how broadly these results can be generalized.
The evaluation contains five queries and the top five results per method. These labels are a small sample of retrieved results, not relevance judgments over the full listing corpus.

| Method | Precision@5 | NDCG@5 |
|---|---:|---:|
| Semantic Search | 0.4800 | 0.9073 |
| BM25 | 0.6000 | 0.8772 |

**Comparison:** BM25 has higher Precision@5 by **0.1200**, while Semantic Search has higher NDCG@5 by **0.0301**.

## Week 5 latency benchmark

Status: completed using **10,000 real listings** from MySQL, the existing `SemanticSearcher` MiniLM model, and an isolated `IndexFlatIP` FAISS index. The index and generated vectors were kept in memory/temporary storage and did not overwrite project artifacts.
Measured 100 repeated searches after 10 warm-up searches. Both paths used top-5 retrieval and the same five Week 5 queries, cycled evenly. End-to-end time includes query embedding, FAISS retrieval, and result assembly. FAISS-only time uses precomputed query vectors. Median, mean, and p95 are computed over the 100 timed samples in milliseconds.

| Measurement | Median (ms) | Mean (ms) | p95 (ms) |
|---|---:|---:|---:|
| FAISS-only retrieval | 0.088 | 0.088 | 0.092 |
| End-to-end search | 4.343 | 4.275 | 4.693 |

**100 ms FAISS retrieval target:** MEETS (based on p95 FAISS-only latency of 0.092 ms).

### Latency methodology and limitations

- FAISS-only timing starts after each query vector has been encoded and measures `IndexFlatIP.search`; it excludes query embedding and result assembly. End-to-end timing calls `SemanticSearcher.search`, which includes those steps.
- This is one run on one machine. The report does not record CPU/GPU model, operating system, FAISS/thread settings, or database snapshot date, so the figures are not a controlled cross-machine comparison.
- The 100 timed requests cycle through five queries and reuse one in-memory index. The p95 therefore describes this workload and setup; it does not guarantee latency for other hardware, concurrency, index types, or query distributions.
