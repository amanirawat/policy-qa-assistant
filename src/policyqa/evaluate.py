"""Measure the assistant against a labeled question set (eval/questions.json).

Metrics:
  * Retrieval hit@1 / hit@3 - is the correct source document the top result /
    in the top 3, for questions the documents DO cover?
  * Answer rate - share of in-scope questions that got a cited answer.
  * Refusal accuracy - share of out-of-scope questions correctly refused.
  * Citation precision - share of answers whose citations include the
    expected source document.
"""

from __future__ import annotations

import json
from pathlib import Path

from .answer import answer_question
from .retriever import BM25Retriever


def run_eval(retriever: BM25Retriever, questions_path: Path, out_path: Path | None = None,
             mode: str = "extractive") -> dict:
    items = json.loads(Path(questions_path).read_text(encoding="utf-8"))
    rows = []
    for item in items:
        q, expected = item["question"], item.get("expected_source")
        hits = retriever.search(q, k=3)
        files = [h.chunk.file for h in hits]
        ans = answer_question(q, retriever, mode=mode)
        cited_files = {c.file for c in ans.citations}
        rows.append({
            "question": q,
            "expected_source": expected,
            "in_scope": expected is not None,
            "top_source": files[0] if files else None,
            "hit_at_1": bool(expected and files[:1] == [expected]),
            "hit_at_3": bool(expected and expected in files),
            "answered": ans.covered,
            "citation_correct": bool(expected and expected in cited_files),
            "reason": ans.reason,
        })

    in_scope = [r for r in rows if r["in_scope"]]
    out_scope = [r for r in rows if not r["in_scope"]]
    answered = [r for r in in_scope if r["answered"]]

    def pct(n: int, d: int) -> float:
        return round(100 * n / d, 1) if d else 0.0

    summary = {
        "questions": len(rows),
        "in_scope": len(in_scope),
        "out_of_scope": len(out_scope),
        "retrieval_hit_at_1": pct(sum(r["hit_at_1"] for r in in_scope), len(in_scope)),
        "retrieval_hit_at_3": pct(sum(r["hit_at_3"] for r in in_scope), len(in_scope)),
        "answer_rate": pct(len(answered), len(in_scope)),
        "refusal_accuracy": pct(sum(not r["answered"] for r in out_scope), len(out_scope)),
        "citation_precision": pct(sum(r["citation_correct"] for r in answered), len(answered)),
    }
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    return {"summary": summary, "rows": rows}
