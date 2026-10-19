# Cybersecurity Policy Q&A Assistant

An assistant that answers employee security questions (passwords, phishing, incident reporting, data handling) **using only approved NIST and CISA guidance**. It retrieves the most relevant passages, cites the source behind every answer, and **refuses questions the documents don't cover** instead of guessing.

```
$ policyqa ask "How often do I need to change my password?"

Do not force users to change passwords on a fixed schedule, such as every 90 days. [1]
A password change should be required only when there is evidence that the password
has been compromised, for example after a breach or a phishing incident. [1]

Sources:
  [1] NIST SP 800-63B - Password Guidance - Password expiration and periodic changes

$ policyqa ask "What is the company's vacation policy?"

The approved policy documents don't cover this question, so I can't answer it.
Please contact your IT or security team.
```

## Why this exists

General-purpose chatbots answer security questions confidently even when they're wrong or out of date. For policy questions, a wrong answer is worse than no answer. This project shows how to build an assistant that is **source-grounded**: every answer is traceable to an approved document, and anything outside that scope is refused.

## How it works

```
data/docs/*.md|pdf|txt
        │  1. Ingest: parse documents, split by section, then into ~160-word
        │     overlapping chunks that keep title / section / page metadata
        ▼
  chunk index (data/index/chunks.json)
        │  2. Retrieve: BM25 ranking (implemented from scratch) over chunk
        │     text + section headings, with a small security synonym map
        ▼
  top-k passages + scores
        │  3. Coverage gate: refuse unless the top passages contain enough of
        │     the question's meaningful words (IDF-weighted)
        ▼
  4. Answer
     • extractive (default, free, offline): best-matching sentences, each cited
     • llm (optional): Claude writes a short answer from the passages only;
       answers without a valid [n] citation are rejected
        │
        ▼
  5. Audit log: logs/answers.jsonl records the question, retrieved chunk IDs,
     scores, cited chunks and final answer for every query
```

| Component | File |
|---|---|
| Document loading & chunking | `src/policyqa/ingest.py` |
| BM25 retrieval & coverage | `src/policyqa/retriever.py` |
| Grounded answering, refusal, audit log | `src/policyqa/answer.py` |
| Evaluation metrics | `src/policyqa/evaluate.py` |
| CLI | `src/policyqa/cli.py` |
| Web UI | `app.py` (Streamlit) |

## Results

Measured with `policyqa eval`. The **dev set** was used while building and tuning; the **holdout set** contains questions the system was not tuned on, so it is the more honest number.

| Metric | Dev (38 q) | Holdout (20 q) |
|---|---|---|
| Retrieval hit@1 (correct document ranked first) | 100% | 93.3% |
| Retrieval hit@3 | 100% | 93.3% |
| Answer rate (in-scope questions answered) | 96.4% | 100% |
| Refusal accuracy (out-of-scope questions refused) | 100% | 80% |
| Citation precision (answers citing the right document) | 100% | 93.3% |

Known weaknesses, visible in `eval/results_holdout.json`:
- Keyword retrieval can be fooled by generic overlap ("best programming language to **learn**" matches "lessons **learned**").
- Questions that use words absent from the documents need the synonym map in `retriever.py`.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[ui,dev]"

policyqa ingest                    # build the index
policyqa ask "What should I do with a suspicious email?" -v
policyqa chat                      # interactive mode
policyqa eval                      # dev metrics
policyqa eval --set holdout        # holdout metrics
pytest                             # 9 tests

streamlit run app.py               # web UI at http://localhost:8501
```

### Optional: LLM answers with Claude

```bash
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=your-key    # Windows PowerShell: $env:ANTHROPIC_API_KEY="your-key"
policyqa ask "Are SMS codes a good second factor?" --mode llm
```

Retrieval and refusal still run first, so the model only ever sees approved passages.

## The document set

`data/docs/` ships with six **plain-language starter summaries** written for this project, each linking to its official source:

| File | Source |
|---|---|
| `nist-sp-800-63b-passwords.md` | NIST SP 800-63B, password and authenticator guidance |
| `nist-sp-800-61-incident-response.md` | NIST SP 800-61 Rev. 3, incident response |
| `nist-csf-2.md` | NIST Cybersecurity Framework 2.0 |
| `cisa-secure-our-world.md` | CISA Secure Our World |
| `nist-sp-800-122-pii.md` | NIST SP 800-122, protecting PII |
| `nist-sp-800-88-media-sanitization.md` | NIST SP 800-88, media sanitization |

To use the official publications instead, download the PDFs from the links in each file's header, drop them into `data/docs/`, and run `policyqa ingest`. PDFs are cited by page number. NIST and CISA publications are U.S. government works.

> This is a portfolio project, not legal or compliance advice. Always confirm against the official publications.

## Roadmap

- [ ] Hybrid retrieval (BM25 + embeddings) to catch paraphrased questions
- [ ] Use the official NIST/CISA PDFs as the default corpus
- [ ] Larger holdout set written by people who didn't build the system
- [ ] Dashboard over `logs/answers.jsonl` (most-asked topics, refusal rate)

## License

MIT
