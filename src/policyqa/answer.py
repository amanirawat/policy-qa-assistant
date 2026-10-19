"""Turn retrieved chunks into a grounded, cited answer - or refuse.

Two answer modes:
  * extractive (default, free, offline): picks the most relevant sentences
    straight from the approved documents and cites each one.
  * llm (optional): if ANTHROPIC_API_KEY is set, Claude writes a short answer
    using ONLY the retrieved passages, citing them as [1], [2], ...

Guardrails, applied in both modes:
  1. Coverage gate - if the best passage doesn't match enough of the question,
     the assistant says the approved documents don't cover it.
  2. Citation check - an LLM answer with no valid [n] citation is rejected.
  3. Audit log - every question, the chunks used and their scores are written
     to logs/answers.jsonl so any answer can be traced afterwards.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .retriever import BM25Retriever, Hit, tokenize

MIN_COVERAGE = 0.5      # IDF-weighted share of question words the top passages must contain
MIN_SCORE = 3.0         # minimum BM25 score for the best passage
NOT_COVERED_MSG = (
    "The approved policy documents don't cover this question, so I can't answer it. "
    "Please contact your IT or security team."
)

DEFAULT_MODEL = os.environ.get("POLICYQA_MODEL", "claude-haiku-5-5")


@dataclass
class Citation:
    number: int
    title: str
    file: str
    section: str
    page: int | None
    url: str | None
    chunk_id: str
    score: float
    excerpt: str


@dataclass
class Answer:
    question: str
    text: str
    covered: bool
    mode: str
    citations: list[Citation] = field(default_factory=list)
    reason: str = ""


def is_covered(hits: list[Hit], min_coverage: float = MIN_COVERAGE,
               min_score: float = MIN_SCORE, question: str | None = None,
               retriever: BM25Retriever | None = None) -> tuple[bool, str]:
    """Covered only if the top passage scores well AND the top passages together
    contain enough of the question's meaningful words. Measuring coverage across
    the top 3 lets multi-part questions ("clear vs purge vs destroy") pass while
    generic matches ("company vacation policy") still fail."""
    if not hits:
        return False, "no matching passages"
    top = hits[0]
    if top.score < min_score:
        return False, f"top score {top.score:.2f} below {min_score}"
    if question is not None:
        q_terms = set(tokenize(question))
        matched = set().union(*(h.matched_terms for h in hits[:3]))
        if retriever is not None:
            # Weighted coverage: matching rare, specific words counts for more
            # than matching common ones like "information" or "program".
            total = sum(retriever.term_weight(t) for t in q_terms)
            coverage = sum(retriever.term_weight(t) for t in matched) / total if total else 0.0
        else:
            coverage = len(matched) / len(q_terms) if q_terms else 0.0
        if len(matched) < min(2, len(q_terms)):
            return False, f"only {len(matched)} question term(s) matched"
    else:
        coverage = top.coverage
    if coverage < min_coverage:
        return False, f"question coverage {coverage:.0%} below {min_coverage:.0%}"
    return True, f"ok (coverage {coverage:.0%}, top score {top.score:.1f})"


def _citations(hits: list[Hit]) -> list[Citation]:
    return [
        Citation(
            number=i,
            title=h.chunk.title,
            file=h.chunk.file,
            section=h.chunk.section,
            page=h.chunk.page,
            url=h.chunk.url,
            chunk_id=h.chunk.id,
            score=round(h.score, 3),
            excerpt=h.chunk.text,
        )
        for i, h in enumerate(hits, start=1)
    ]


# --------------------------------------------------------------------------
# Extractive mode
# --------------------------------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def extractive_answer(question: str, hits: list[Hit], max_sentences: int = 3) -> tuple[str, list[int]]:
    q_terms = set(tokenize(question, expand=True))
    candidates = []
    for rank, hit in enumerate(hits, start=1):
        for position, sentence in enumerate(_SENT_SPLIT.split(hit.chunk.text)):
            overlap = len(q_terms & set(tokenize(sentence)))
            if overlap:
                # Prefer high-overlap sentences from higher-ranked passages
                candidates.append((overlap - 0.15 * (rank - 1), rank, position, sentence.strip()))
    candidates.sort(key=lambda c: c[0], reverse=True)
    if candidates:
        best = candidates[0][0]
        candidates = [c for c in candidates if c[0] >= 0.5 * best]
    chosen = candidates[:max_sentences]
    # Keep the chosen sentences in reading order for readability
    chosen.sort(key=lambda c: (c[1], c[2]))
    used = sorted({c[1] for c in chosen})
    text = " ".join(f"{c[3]} [{c[1]}]" for c in chosen)
    return text, used


# --------------------------------------------------------------------------
# LLM mode
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an internal cybersecurity policy assistant.
Answer the employee's question using ONLY the numbered source passages provided.
Rules:
- Cite every claim with the passage number in square brackets, e.g. [1] or [2][3].
- Do not use outside knowledge. Do not guess.
- If the passages do not contain the answer, reply with exactly: NOT_COVERED
- Keep the answer under 120 words, plain language, practical for a non-technical employee."""


def llm_answer(question: str, hits: list[Hit], model: str = DEFAULT_MODEL) -> tuple[str, list[int]]:
    import anthropic  # optional dependency

    context = "\n\n".join(
        f"[{i}] {h.chunk.title} - {h.chunk.section}\n{h.chunk.text}"
        for i, h in enumerate(hits, start=1)
    )
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Sources:\n{context}\n\nQuestion: {question}"}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text) if 1 <= int(n) <= len(hits)})
    return text, cited


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def answer_question(question: str, retriever: BM25Retriever, k: int = 4,
                    mode: str | None = None, log_path: Path | None = None) -> Answer:
    if mode is None:
        mode = "llm" if os.environ.get("ANTHROPIC_API_KEY") else "extractive"

    hits = retriever.search(question, k=k)
    covered, reason = is_covered(hits, question=question, retriever=retriever)

    if not covered:
        result = Answer(question, NOT_COVERED_MSG, False, mode, reason=reason)
    else:
        if mode == "llm":
            text, used = llm_answer(question, hits)
            if text.strip() == "NOT_COVERED":
                result = Answer(question, NOT_COVERED_MSG, False, mode, reason="model reported not covered")
            elif not used:
                result = Answer(question, NOT_COVERED_MSG, False, mode, reason="model answer had no valid citation")
            else:
                result = Answer(question, text, True, mode, reason=reason)
        else:
            text, used = extractive_answer(question, hits)
            result = Answer(question, text, bool(used), mode, reason=reason)
            if not used:
                result.text, result.reason = NOT_COVERED_MSG, "no relevant sentence found"

        if result.covered:
            all_cites = _citations(hits)
            result.citations = [c for c in all_cites if c.number in used]

    if log_path:
        _log(result, hits, log_path)
    return result


def _log(result: Answer, hits: list[Hit], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": result.question,
        "covered": result.covered,
        "mode": result.mode,
        "reason": result.reason,
        "retrieved": [
            {"chunk_id": h.chunk.id, "score": round(h.score, 3), "coverage": round(h.coverage, 3)}
            for h in hits
        ],
        "cited_chunks": [c.chunk_id for c in result.citations],
        "answer": result.text,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
