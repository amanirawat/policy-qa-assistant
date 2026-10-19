"""Command line interface.

  policyqa ingest              build the chunk index from data/docs/
  policyqa ask "question"      answer one question with citations
  policyqa chat                interactive Q&A loop
  policyqa eval [--set holdout] score the assistant on a labeled question set
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .answer import Answer, answer_question
from .evaluate import run_eval
from .ingest import build_chunks, load_chunks, save_chunks
from .retriever import BM25Retriever

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "data" / "docs"
INDEX_PATH = ROOT / "data" / "index" / "chunks.json"
LOG_PATH = ROOT / "logs" / "answers.jsonl"
EVAL_SETS = {"dev": ROOT / "eval" / "questions.json", "holdout": ROOT / "eval" / "holdout.json"}


def get_retriever() -> BM25Retriever:
    if not INDEX_PATH.exists():
        print("No index found - building it from data/docs/ ...", file=sys.stderr)
        save_chunks(build_chunks(DOCS_DIR), INDEX_PATH)
    return BM25Retriever(load_chunks(INDEX_PATH))


def print_answer(ans: Answer, verbose: bool = False) -> None:
    print(f"\n{ans.text}\n")
    if ans.citations:
        print("Sources:")
        for c in ans.citations:
            where = f"p. {c.page}" if c.page else c.section
            link = f"  ({c.url})" if c.url else ""
            print(f"  [{c.number}] {c.title} - {where}{link}")
    if verbose:
        print(f"\nmode={ans.mode}  covered={ans.covered}  reason={ans.reason}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="policyqa", description="Cybersecurity Policy Q&A Assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="index the documents in data/docs/")

    ask = sub.add_parser("ask", help="ask a single question")
    ask.add_argument("question")
    ask.add_argument("--mode", choices=["extractive", "llm"], default=None)
    ask.add_argument("-v", "--verbose", action="store_true")

    chat = sub.add_parser("chat", help="interactive question loop")
    chat.add_argument("--mode", choices=["extractive", "llm"], default=None)

    ev = sub.add_parser("eval", help="run the evaluation question set")
    ev.add_argument("--mode", choices=["extractive", "llm"], default="extractive")
    ev.add_argument("--set", choices=["dev", "holdout"], default="dev",
                    help="dev = questions used while building; holdout = unseen questions")

    args = parser.parse_args(argv)

    if args.command == "ingest":
        chunks = build_chunks(DOCS_DIR)
        save_chunks(chunks, INDEX_PATH)
        docs = len({c.file for c in chunks})
        print(f"Indexed {len(chunks)} chunks from {docs} documents -> {INDEX_PATH.relative_to(ROOT)}")
        return 0

    retriever = get_retriever()

    if args.command == "ask":
        print_answer(answer_question(args.question, retriever, mode=args.mode, log_path=LOG_PATH), args.verbose)
    elif args.command == "chat":
        print("Cybersecurity Policy Q&A - type a question, or 'quit' to exit.")
        while True:
            try:
                q = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.lower() in {"quit", "exit", "q"}:
                break
            if q:
                print_answer(answer_question(q, retriever, mode=args.mode, log_path=LOG_PATH))
    elif args.command == "eval":
        out = ROOT / "eval" / f"results_{args.set}.json"
        s = run_eval(retriever, EVAL_SETS[args.set], out, mode=args.mode)["summary"]
        print(f"\n[{args.set} set] Evaluated {s['questions']} questions "
              f"({s['in_scope']} in scope, {s['out_of_scope']} out of scope)\n")
        print(f"  Retrieval hit@1      {s['retrieval_hit_at_1']:>5}%")
        print(f"  Retrieval hit@3      {s['retrieval_hit_at_3']:>5}%")
        print(f"  Answer rate          {s['answer_rate']:>5}%")
        print(f"  Refusal accuracy     {s['refusal_accuracy']:>5}%")
        print(f"  Citation precision   {s['citation_precision']:>5}%")
        print(f"\nFull results -> {out.relative_to(ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
