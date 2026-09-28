"""
Grounding claims in the RAG service.

`grounded: True` is the field a reader trusts. These tests pin the cases where
it used to be asserted without anything having checked it.
"""
from app.rag import service as rag_service


def _hits(n: int = 2) -> list[dict]:
    return [
        {"title": f"Doc {i}", "source": "official", "source_url": "", "content": f"body {i}"}
        for i in range(1, n + 1)
    ]


def test_no_retrieval_match_is_not_grounded(monkeypatch):
    monkeypatch.setattr(rag_service, "search", lambda *_a, **_kw: [])
    out = rag_service.answer("anything")
    assert out["grounded"] is False
    assert out["answer_basis"] == "no_retrieval_match"
    assert out["sources"] == []


def test_unavailable_llm_does_not_return_the_source_dump_as_the_answer(monkeypatch):
    """
    When Gemini was unavailable this returned the raw concatenated chunks as
    `answer` with grounded=True, presenting a dump of source text as a response.
    """
    monkeypatch.setattr(rag_service, "search", lambda *_a, **_kw: _hits())
    monkeypatch.setattr(
        rag_service.GeminiClient, "generate_json", lambda *_a, **_kw: None
    )

    out = rag_service.answer("eligibility")

    assert out["answer"] is None
    assert out["grounded"] is False
    assert out["llm_used"] is False
    assert out["answer_basis"] == "llm_unavailable"
    # Evidence is still returned, just not as the answer.
    assert len(out["sources"]) == 2


def test_answer_without_citations_is_not_grounded(monkeypatch):
    """An answer that points at no source cannot be asserted as supported."""
    monkeypatch.setattr(rag_service, "search", lambda *_a, **_kw: _hits())
    monkeypatch.setattr(
        rag_service.GeminiClient,
        "generate_json",
        lambda *_a, **_kw: "The subsidy is 50 percent for all applicants.",
    )

    out = rag_service.answer("what is the subsidy")

    assert out["llm_used"] is True
    assert out["grounded"] is False
    assert out["answer_basis"] == "llm_uncited"
    assert out["note"] and "unverified" in out["note"]


def test_citation_beyond_the_retrieved_set_is_not_grounded(monkeypatch):
    """Citing [SOURCE 9] out of a two-source retrieval is a fabricated citation."""
    monkeypatch.setattr(rag_service, "search", lambda *_a, **_kw: _hits(n=2))
    monkeypatch.setattr(
        rag_service.GeminiClient,
        "generate_json",
        lambda *_a, **_kw: "Eligible applicants get 25 percent [SOURCE 9].",
    )

    out = rag_service.answer("what is the subsidy")

    assert out["grounded"] is False
    assert out["cited_sources"] == []


def test_valid_citation_is_grounded(monkeypatch):
    monkeypatch.setattr(rag_service, "search", lambda *_a, **_kw: _hits(n=2))
    monkeypatch.setattr(
        rag_service.GeminiClient,
        "generate_json",
        lambda *_a, **_kw: "Eligible applicants get 25 percent [SOURCE 1].",
    )

    out = rag_service.answer("what is the subsidy")

    assert out["grounded"] is True
    assert out["answer_basis"] == "llm_cited"
    assert out["cited_sources"] == [1]
    assert out["note"] is None


def test_retrieval_only_mode_is_labelled_as_evidence_not_an_answer(monkeypatch):
    monkeypatch.setattr(rag_service, "search", lambda *_a, **_kw: _hits())
    out = rag_service.answer("eligibility", use_llm=False)
    assert out["grounded"] is True
    assert out["llm_used"] is False
    assert out["answer_basis"] == "retrieval_only_no_llm"
    assert "not a generated answer" in out["note"]


def test_citation_extraction_ignores_out_of_range_and_junk():
    assert rag_service._extract_citations("[SOURCE 1] and [SOURCE 3]", 2) == [1]
    assert rag_service._extract_citations("[SOURCE 0]", 2) == []
    assert rag_service._extract_citations("[SOURCE -1]", 2) == []
    assert rag_service._extract_citations("no citations here", 2) == []
