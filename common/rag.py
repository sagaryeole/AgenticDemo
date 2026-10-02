"""The RAG pieces from labs 16-18, assembled so lab 19 and agent 20 can reuse them.

Chunking is lab 16, embedding is lab 17, cosine scoring is lab 18. The new part is `Index.search`, the retrieval
rules explained in lab 19 (top-k, minimum score, keyword boost).
"""
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from common.embeddings import embed_texts

HANDBOOK = Path(__file__).resolve().parent.parent / "data" / "handbook.md"


def load_handbook() -> str:
    return HANDBOOK.read_text()


# --- Lab 16: chunking -------------------------------------------------------------------------------

def fixed_size(text: str, size: int = 300, overlap: int = 60) -> list[str]:
    step = max(1, size - overlap)
    chunks = []
    for start in range(0, len(text), step):
        chunks.append(text[start:start + size])
        if start + size >= len(text):
            break
    return [c for c in chunks if c.strip()]


def sections(text: str) -> list[str]:
    blocks = re.split(r"(?m)^(?=## )", text)
    return [b.strip() for b in blocks if b.strip().startswith("## ")]


def paragraphs(text: str) -> list[str]:
    without_headings = re.sub(r"(?m)^#+ .*\n?", "", text)
    return [b.strip() for b in re.split(r"\n\s*\n", without_headings) if b.strip()]


def paragraphs_with_heading(text: str) -> list[str]:
    chunks = []
    for section in sections(text):
        title, _, body = section.partition("\n")
        for paragraph in re.split(r"\n\s*\n", body.strip()):
            if paragraph.strip():
                chunks.append(f"{title.lstrip('# ').strip()}: {paragraph.strip()}")
    return chunks


CHUNKERS = {
    "fixed+overlap": fixed_size,
    "paragraphs": paragraphs,
    "sections": sections,
    "paragraphs+heading": paragraphs_with_heading,
}


# --- Lab 19: retrieval rules ---------------------------------------------------------------------------

STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "does", "can", "i", "my", "me", "we", "you", "of", "to", "in", "on", "at",
    "for", "and", "or", "it", "how", "what", "when", "where", "which", "who", "much", "many", "there", "this", "that",
    "with", "be", "have", "has", "if", "about", "from", "by",
}


def tokens(text: str) -> set[str]:
    """Lower-case words, keeping codes like 'lb-204' whole. Stop words are dropped."""
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-]*", text.lower()) if w not in STOPWORDS}


def keyword_overlap(query: str, chunk: str) -> float:
    """The share of the question's words that appear exactly in the chunk (0 to 1)."""
    q = tokens(query)
    return len(q & tokens(chunk)) / len(q) if q else 0.0


@dataclass
class Hit:
    text: str
    score: float      # final score used for ranking
    cosine: float     # similarity from the embeddings
    keyword: float    # exact-word overlap


class Index:
    """A list of chunks plus their vectors. This is the whole 'vector database' of the tutorial."""

    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.vectors = embed_texts(chunks, kind="document")   # shape (number of chunks, dimensions)

    def search(self, query: str, k: int = 3, min_score: float = 0.0, keyword_weight: float = 0.0) -> list[Hit]:
        """Return up to k chunks, best first, dropping any whose final score is below min_score.

        final score = cosine + keyword_weight * keyword_overlap
        """
        q = embed_texts([query], kind="query")[0]
        cosines = self.vectors @ q          # unit-length vectors, so the dot product is the cosine
        hits = [
            Hit(text=chunk, cosine=float(c), keyword=keyword_overlap(query, chunk),
                score=float(c) + keyword_weight * keyword_overlap(query, chunk))
            for chunk, c in zip(self.chunks, cosines)
        ]
        hits.sort(key=lambda h: h.score, reverse=True)
        return [h for h in hits[:k] if h.score >= min_score]
