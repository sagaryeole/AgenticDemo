"""The RAG pieces from labs 16-18, assembled so lab 19 and agent 20 can reuse them.

Chunking is lab 16, embedding is lab 17, cosine scoring is lab 18. The new part is `Index.search`, the retrieval
rules explained in lab 19 (top-k, minimum score, keyword boost).
"""
import math
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


# --- Lab 35: keyword search (BM25), rank fusion and reranking -------------------------------------------

def bm25_words(text: str) -> list[str]:
    """Lower-case words as a LIST (repeats count), codes like 'lb-204' kept whole, stop words dropped."""
    return [w for w in re.findall(r"[a-z0-9][a-z0-9\-]*", text.lower()) if w not in STOPWORDS]


class BM25:
    """Keyword search, the classic way. A chunk scores high when it contains the question's words, and rare words
    (a form code, a name) count for much more than common ones. No embeddings and no model: just counting.

    score(chunk) = sum over the question's words of  idf(word) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / average length))
    where tf = how often the word appears in the chunk and idf = how rare the word is among all chunks.
    """

    def __init__(self, chunks: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [bm25_words(c) for c in chunks]
        self.avg_len = sum(len(d) for d in self.docs) / len(self.docs)
        n = len(self.docs)
        document_frequency: dict[str, int] = {}
        for doc in self.docs:
            for word in set(doc):
                document_frequency[word] = document_frequency.get(word, 0) + 1
        self.idf = {w: math.log(1 + (n - df + 0.5) / (df + 0.5)) for w, df in document_frequency.items()}

    def scores(self, query: str) -> list[float]:
        """One score per chunk, in the order of the chunks."""
        result = []
        for doc in self.docs:
            score = 0.0
            for word in set(bm25_words(query)):
                tf = doc.count(word)
                if tf:
                    norm = tf + self.k1 * (1 - self.b + self.b * len(doc) / self.avg_len)
                    score += self.idf[word] * tf * (self.k1 + 1) / norm
            result.append(score)
        return result


def ranking(scores: list[float]) -> list[int]:
    """Chunk numbers, best score first. Ties keep the original order."""
    return sorted(range(len(scores)), key=lambda i: -scores[i])


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[int]:
    """Merge several rankings into one. A chunk earns 1 / (k + position) from each ranking, so one that is near the top
    in BOTH lists wins. Only positions are used, never the scores, so cosine and BM25 (which have different scales)
    can be combined without any weight to tune."""
    total: dict[int, float] = {}
    for ranked in rankings:
        for position, chunk_number in enumerate(ranked, start=1):
            total[chunk_number] = total.get(chunk_number, 0.0) + 1.0 / (k + position)
    return sorted(total, key=lambda i: -total[i])


def llm_rerank(query: str, chunks: list[str]) -> list[int]:
    """Ask a model to read the question and each candidate chunk together and give every chunk a 0-10 score.
    Returns the positions (0-based, within `chunks`) best first. Slow and costly compared with vectors, so it is
    used only on the few candidates the cheap search already found."""
    from common.llm import ask  # imported here so labs that never rerank do not need a model

    listing = "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(chunks))
    reply = ask(
        f"Question: {query}\n\nCandidate passages:\n\n{listing}\n\n"
        "For each passage, give a score from 0 to 10 for how directly it ANSWERS the question "
        "(10 = contains the answer, 0 = unrelated). Reply with exactly one line per passage, like `1: 7`, and nothing else.",
        system="You are a strict relevance judge for a search engine.",
    )
    scores = [0.0] * len(chunks)
    for number, score in re.findall(r"(\d+)\s*[:=]\s*(\d+(?:\.\d+)?)", reply.text):
        if 1 <= int(number) <= len(chunks):
            scores[int(number) - 1] = float(score)
    return ranking(scores)
