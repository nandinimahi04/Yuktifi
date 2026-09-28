# -*- coding: utf-8 -*-
"""RAG evaluation test suite for official government corpus.

The seeded corpus (see ``app.rag.seed_corpus``) contains five official
scheme documents.  This test verifies that the RAG service can retrieve the
correct document for representative queries and that the basic ranking
metrics meet a minimal threshold.

The test does **not** depend on the LLM – it disables ``use_llm`` so that the
raw context is returned.  This makes the suite fast and deterministic.
"""

import sys, os
# Ensure the project root (backend) is on PYTHONPATH for test imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.rag.service import answer
from app.rag.seed_corpus import seed_rag_corpus

# Ensure the corpus is seeded before any test runs.
@pytest.fixture(scope="module", autouse=True)
def ensure_seeded():
    # ``seed_rag_corpus`` returns the number of indexed documents.
    count = seed_rag_corpus()
    assert count >= 5, "Expected at least 5 official documents to be indexed"

# A small set of representative queries together with the title we expect
# to appear as the top‑ranked hit.
QUERY_EXPECTATIONS = [
    {
        "query": "What is the interest rate for NSFDC Micro Credit Finance Scheme?",
        "expected_title": "NSFDC Micro Credit Finance Scheme Guidelines",
    },
    {
        "query": "What is the maximum project cost under the PMEGP scheme?",
        "expected_title": "PMEGP Prime Minister Employment Generation Programme Guidelines",
    },
    {
        "query": "What categories does MUDRA offer for micro‑enterprise loans?",
        "expected_title": "MUDRA Pradhan Mantri Mudra Yojana Scheme Guidelines",
    },
    {
        "query": "What is the interest rate for NSFDC Term Loan Scheme?",
        "expected_title": "NSFDC Term Loan Scheme Guidelines",
    },
    {
        "query": "What are the dairy production parameters in the ICAR technical manual?",
        "expected_title": "ICAR Small Dairy & Micro Food Processing Technical Manual",
    },
]

def _run_query(query: str):
    """Utility that calls ``answer`` without invoking the LLM.

    The function returns the full response dictionary from ``app.rag.service``.
    """
    return answer(query, top_k=5, use_llm=False)

def test_rag_top_hits_match_expected():
    """Each query should have the expected document as the first hit.
    """
    for case in QUERY_EXPECTATIONS:
        resp = _run_query(case["query"])
        # The service returns ``grounded`` True when hits are present.
        assert resp["grounded"] is True
        # ``sources`` is the list of hit dictionaries ordered by relevance.
        sources = resp["sources"]
        assert sources, "No sources returned for query: {}".format(case["query"])
        titles = [s["title"] for s in sources]
        assert case["expected_title"] in titles, (
            f"Expected title '{case['expected_title']}' not found in results for query '{case['query']}'"
        )

def test_rag_basic_metrics():
    """Compute simple ranking metrics across the query set.

    * Precision@1 – proportion of queries where the expected document appears
      in the top‑1 result.
    * Recall@5 – proportion where it appears within the top‑5 results.
    * Mean Reciprocal Rank (MRR).
    """
    precision_at_1 = 0
    recall_at_5 = 0
    reciprocal_rank_sum = 0.0
    for case in QUERY_EXPECTATIONS:
        resp = _run_query(case["query"])
        sources = resp["sources"]
        titles = [s["title"] for s in sources]
        # Precision@1
        if titles and titles[0] == case["expected_title"]:
            precision_at_1 += 1
        # Recall@5
        if case["expected_title"] in titles[:5]:
            recall_at_5 += 1
        # Reciprocal rank
        try:
            rank = titles.index(case["expected_title"]) + 1
            reciprocal_rank_sum += 1.0 / rank
        except ValueError:
            pass
    n = len(QUERY_EXPECTATIONS)
    precision = precision_at_1 / n
    recall = recall_at_5 / n
    mrr = reciprocal_rank_sum / n
    # Minimal thresholds – feel free to adjust if the underlying scoring changes.
    assert precision >= 0.8, f"Precision@1 too low: {precision:.2f}"
    assert recall >= 0.9, f"Recall@5 too low: {recall:.2f}"
    assert mrr >= 0.80, f"MRR too low: {mrr:.2f}"

# End of test suite
