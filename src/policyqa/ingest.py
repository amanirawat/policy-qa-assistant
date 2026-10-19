"""Load approved policy documents and split them into citable chunks.

Supported inputs (put them in data/docs/):
  * .md  - optional front matter (title, publisher, url); headings become sections
  * .pdf - one section per page, so citations can point to a page number
  * .txt - treated as a single section

Every chunk keeps its source title, file, section and page so an answer can
always be traced back to the exact passage it came from.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

DEFAULT_MAX_WORDS = 160
DEFAULT_OVERLAP = 40


@dataclass
class Section:
    heading: str
    text: str
    page: int | None = None


@dataclass
class Document:
    title: str
    file: str
    url: str | None
    publisher: str | None
    sections: list[Section]


@dataclass
class Chunk:
    id: str
    text: str
    title: str
    file: str
    section: str
    page: int | None
    url: str | None
    publisher: str | None

    def citation(self) -> str:
        where = f"p. {self.page}" if self.page else self.section
        return f"{self.title} - {where}"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

_FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def _parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    match = _FRONT_MATTER.match(raw)
    if not match:
        return {}, raw
    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip().lower()] = value.strip()
    return meta, raw[match.end():]


def load_markdown(path: Path) -> Document:
    meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
    sections: list[Section] = []
    stack: list[str] = []          # heading hierarchy, e.g. ["Doc", "Sub"]
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            # Skip the top-level document title in the section path
            label = " > ".join(stack[1:]) if len(stack) > 1 else (stack[0] if stack else "Overview")
            sections.append(Section(heading=label, text=text))
        buffer.clear()

    for line in body.splitlines():
        m = _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            stack[:] = stack[: level - 1] + [m.group(2).strip()]
        else:
            buffer.append(line)
    flush()

    return Document(
        title=meta.get("title", path.stem.replace("-", " ").title()),
        file=path.name,
        url=meta.get("url"),
        publisher=meta.get("publisher"),
        sections=sections,
    )


def load_pdf(path: Path) -> Document:
    from pypdf import PdfReader  # imported lazily so .md-only users don't need it

    reader = PdfReader(str(path))
    title = (reader.metadata.title if reader.metadata and reader.metadata.title else None)
    sections = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            sections.append(Section(heading=f"Page {number}", text=text, page=number))
    return Document(
        title=title or path.stem.replace("-", " ").replace("_", " "),
        file=path.name,
        url=None,
        publisher=None,
        sections=sections,
    )


def load_text(path: Path) -> Document:
    return Document(
        title=path.stem.replace("-", " ").title(),
        file=path.name,
        url=None,
        publisher=None,
        sections=[Section(heading="Full text", text=path.read_text(encoding="utf-8"))],
    )


LOADERS = {".md": load_markdown, ".pdf": load_pdf, ".txt": load_text}


def load_documents(docs_dir: Path) -> list[Document]:
    docs = []
    for path in sorted(Path(docs_dir).iterdir()):
        loader = LOADERS.get(path.suffix.lower())
        if loader:
            docs.append(loader(path))
    return docs


# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------

def _windows(words: list[str], max_words: int, overlap: int) -> Iterator[list[str]]:
    """Sliding word windows. Overlap keeps sentences that straddle a boundary
    retrievable from either side."""
    if len(words) <= max_words:
        yield words
        return
    step = max(1, max_words - overlap)
    for start in range(0, len(words), step):
        window = words[start:start + max_words]
        if window:
            yield window
        if start + max_words >= len(words):
            break


def chunk_document(doc: Document, max_words: int = DEFAULT_MAX_WORDS,
                   overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    chunks = []
    for s_idx, section in enumerate(doc.sections):
        words = section.text.split()
        for w_idx, window in enumerate(_windows(words, max_words, overlap)):
            chunks.append(Chunk(
                id=f"{Path(doc.file).stem}::{s_idx}.{w_idx}",
                text=" ".join(window),
                title=doc.title,
                file=doc.file,
                section=section.heading,
                page=section.page,
                url=doc.url,
                publisher=doc.publisher,
            ))
    return chunks


def build_chunks(docs_dir: Path, max_words: int = DEFAULT_MAX_WORDS,
                 overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in load_documents(docs_dir):
        chunks.extend(chunk_document(doc, max_words, overlap))
    return chunks


def save_chunks(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(c) for c in chunks], indent=2), encoding="utf-8")


def load_chunks(path: Path) -> list[Chunk]:
    return [Chunk(**item) for item in json.loads(Path(path).read_text(encoding="utf-8"))]
