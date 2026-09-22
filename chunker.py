"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.

`split_documents` below is deliberately plain. It cuts every document into
fixed-size pieces with a fixed overlap and pays no attention to where sentences
or paragraphs end. It works, and it is not good.

On a corpus of short posts it may not cut anything at all: `campus_life` comes
out as 88 documents and 88 chunks, because almost nothing in it reaches 800
characters. That is the baseline, not a bug — Milestone 3 is where you decide
whether one post should stay one chunk.

Your job in Milestone 3 is to replace the *body* of `split_documents` with a
strategy that fits the documents you actually read in Milestone 1. Keep the
name and the shape of what it returns — the rest of the pipeline calls it, and
your README has to name the function that produced your chunks.

If you get stuck for 30 minutes, `fallback_split` is the original. Switch back
to it, write down what you saw, and move on. That's a real observation about
your pipeline, not giving up.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document

_REPLY_MARKER = re.compile(r"--- reply \d+ \(\d+ votes?\) ---")


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


def split_thread(doc: Document) -> list[Chunk]:
    """
    Split one advice_threads document into one chunk per reply.

    A whole thread isn't one thought — it's several people giving different,
    sometimes contradictory, answers to the question in the title. Chunking by
    character count lumps those answers into a single averaged embedding and
    buries the one reply that actually answers a given question. Chunking by
    reply keeps each answer distinct.

    Each reply is prefixed with the thread title, since a reply on its own
    ("Talk to the department adviser...") doesn't say what question it's
    answering. Vote counts are dropped — they're a ranking signal, not content
    for the model to reason over.
    """
    parts = _REPLY_MARKER.split(doc.text)
    title = parts[0].strip()
    replies = [r.strip() for r in parts[1:] if r.strip()]

    chunks: list[Chunk] = []
    for index, reply in enumerate(replies):
        chunks.append(
            Chunk(
                text=f"{title}\n\n{reply}",
                source=doc.source,
                index=index,
                produced_by="chunker.py::split_documents",
            )
        )
    return chunks


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    Split documents into chunks.

    advice_threads documents are split one reply per chunk (see
    `split_thread`) — the useful boundary there is who's speaking, not a
    character count. Every document in this corpus follows the
    "--- reply N (votes) ---" format, so any document without that marker
    falls back to the plain fixed-size splitter instead of silently
    producing a single giant chunk.
    """
    chunks: list[Chunk] = []
    for doc in documents:
        if _REPLY_MARKER.search(doc.text):
            chunks.extend(split_thread(doc))
        else:
            chunks.extend(fallback_split([doc]))
    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
