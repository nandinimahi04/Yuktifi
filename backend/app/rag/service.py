from __future__ import annotations

import logging
import re

from app.ai.gemini_client import GeminiClient
from .store import search

logger = logging.getLogger(__name__)

#: Citations look like [SOURCE 2]. This matches the ones the prompt asks for.
CITATION_RE = re.compile(r"\[SOURCE\s+(\d+)\]", re.IGNORECASE)

#: A grounded answer has to actually point at the evidence it claims to use. An
#: answer that cites nothing may still be fine, but it cannot be asserted as
#: supported without saying so. Required to claim full grounding.
_MIN_CITED_SOURCES = 1


def _format_context(hits: list[dict]) -> str:
    return "\n\n".join(
        f"[SOURCE {i + 1}] {h['title']} | {h.get('source_url') or h.get('source')}\n{h['content']}"
        for i, h in enumerate(hits)
    )


def _no_evidence(query: str) -> dict:
    return {
        "answer": "No indexed source supports this question yet.",
        "grounded": False,
        "llm_used": False,
        "sources": [],
        "answer_basis": "no_retrieval_match",
        "note": (
            "Nothing in the indexed corpus matched this question, so no answer is given. "
            "This is not a judgement about the answer - the required source was not found."
        ),
    }


def _extract_citations(text: str, n_sources: int) -> list[int]:
    """Citation numbers that actually refer to a retrieved source (1-based)."""
    out = set()
    for m in CITATION_RE.finditer(text or ""):
        n = int(m.group(1))
        if 1 <= n <= n_sources:
            out.add(n)
    return sorted(out)


def answer(query: str, top_k: int = 5, use_llm: bool = True) -> dict:
    """
    Answer a question from the indexed corpus.

    `grounded` is not a synonym for "we returned some text". It means the answer
    is supported by the retrieved sources, and it is only claimed when the
    citation indices in the answer refer to sources that were actually
    retrieved.

    Two things were wrong here before. When the LLM was unavailable the raw
    concatenated chunks were returned *as the answer* with `grounded: True`,
    which presented a dump of source text as a considered response and asserted
    support the system had not checked. And when the LLM did answer, grounding
    was asserted unconditionally, so a fabricated answer citing nothing - or
    citing [SOURCE 9] out of a five-source retrieval - was reported as grounded.
    """
    hits = search(query, top_k)
    if not hits:
        return _no_evidence(query)

    context = _format_context(hits)

    if not use_llm:
        # Retrieval mode: return the evidence itself and say that is what this is.
        return {
            "answer": context,
            "grounded": True,
            "llm_used": False,
            "sources": hits,
            "answer_basis": "retrieval_only_no_llm",
            "note": (
                "Raw retrieved source text, not a generated answer. The LLM was not called, so "
                "nothing has been synthesised or checked for support."
            ),
        }

    prompt = (
        "You are YUKTI's grounded government-information assistant. Answer ONLY from the retrieved "
        "source excerpts below. Do not invent facts or numbers. If the excerpts do not answer the "
        "question, say that the indexed evidence is insufficient. Cite sources as [SOURCE 1], "
        "[SOURCE 2], etc.\n\nQUESTION:\n"
        f"{query}\n\nRETRIEVED SOURCES:\n{context}"
    )

    result = GeminiClient().generate_json(prompt, schema=None)

    if result is None:
        # The LLM is unavailable. Report the evidence and the fact that no
        # answer was generated. Do not present the source dump as the answer.
        logger.info("RAG: LLM unavailable; returning retrieved context without a generated answer.")
        return {
            "answer": None,
            "grounded": False,
            "llm_used": False,
            "sources": hits,
            "answer_basis": "llm_unavailable",
            "note": (
                "The language model was unavailable, so no answer was generated. The retrieved "
                "source excerpts are included for reference and are not an answer. Groundwork was "
                "retrieved but not synthesised or verified."
            ),
        }

    text = result if isinstance(result, str) else str(result)
    cited = _extract_citations(text, len(hits))
    grounded = len(cited) >= _MIN_CITED_SOURCES

    if not grounded:
        logger.info("RAG: answer made no valid citation; not reported as grounded.")

    return {
        "answer": text,
        "grounded": grounded,
        "llm_used": True,
        "sources": hits,
        "answer_basis": "llm_cited" if grounded else "llm_uncited",
        "cited_sources": cited,
        "note": (
            None
            if grounded
            else (
                "The answer did not cite any of the retrieved sources, so it is not reported as "
                "grounded. Treat it as unverified. The excerpts are in `sources`."
            )
        ),
    }
