"""Model-free tests for common/rag.py: chunking, keyword scoring, BM25, rank fusion and Index.search.

Index.search normally calls an embedding model; here `embed_texts` is replaced with a tiny deterministic fake,
so these tests need no API key, no network and no LM Studio.
"""
import numpy as np
import pytest

from common import rag

TEXT = (
    "# Handbook\n\nIntro line.\n\n"
    "## Loans\n\nBooks are lent for 21 days.\n\nRenewals are allowed twice.\n\n"
    "## Fines\n\nA late book costs 0.50 per day.\n"
)


def test_fixed_size_overlaps_and_covers_text():
    text = "abcdefghij" * 10
    chunks = rag.fixed_size(text, size=30, overlap=10)
    assert all(len(c) <= 30 for c in chunks)
    assert chunks[0][-10:] == chunks[1][:10]
    assert chunks[-1].endswith(text[-5:])


def test_fixed_size_overlap_not_smaller_than_size_still_terminates():
    assert rag.fixed_size("abcdef", size=3, overlap=5)


def test_sections_split_on_h2_only():
    result = rag.sections(TEXT)
    assert [s.splitlines()[0] for s in result] == ["## Loans", "## Fines"]


def test_paragraphs_drop_headings():
    result = rag.paragraphs(TEXT)
    assert "Books are lent for 21 days." in result
    assert not any(p.startswith("#") for p in result)


def test_paragraphs_with_heading_prefix_the_section_title():
    result = rag.paragraphs_with_heading(TEXT)
    assert "Loans: Renewals are allowed twice." in result
    assert "Fines: A late book costs 0.50 per day." in result


def test_tokens_keep_codes_whole_and_drop_stopwords():
    assert rag.tokens("What is the fee for LB-204?") == {"fee", "lb-204"}


def test_keyword_overlap_bounds():
    assert rag.keyword_overlap("late fee", "the late fee is 5") == 1.0
    assert rag.keyword_overlap("late fee", "nothing here") == 0.0
    assert rag.keyword_overlap("the of", "anything") == 0.0  # only stop words


def test_bm25_prefers_the_chunk_with_the_rare_word():
    chunks = ["the form lb-204 renews a loan", "a loan lasts three weeks", "fines are paid at the desk"]
    scores = rag.BM25(chunks).scores("lb-204")
    assert rag.ranking(scores)[0] == 0
    assert scores[1] == scores[2] == 0.0


def test_ranking_is_stable_on_ties():
    assert rag.ranking([1.0, 3.0, 1.0]) == [1, 0, 2]


def test_rrf_rewards_agreement_between_rankings():
    # chunk 2 is 2nd in both lists; chunks 0 and 1 are 1st in only one list each
    assert rag.reciprocal_rank_fusion([[0, 2], [1, 2]])[0] == 2


def test_rrf_includes_chunks_seen_in_only_one_ranking():
    assert set(rag.reciprocal_rank_fusion([[0, 1], [2]])) == {0, 1, 2}


@pytest.fixture
def fake_embeddings(monkeypatch):
    """Bag-of-letters vectors (unit length), so similar words give similar vectors."""
    def embed(texts, kind="document"):
        vectors = np.zeros((len(texts), 26))
        for row, text in enumerate(texts):
            for ch in text.lower():
                if "a" <= ch <= "z":
                    vectors[row, ord(ch) - 97] += 1
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    monkeypatch.setattr(rag, "embed_texts", embed)


def test_index_search_returns_best_first_and_respects_k(fake_embeddings):
    index = rag.Index(["apple pie", "zzz qqq", "apple tart"])
    hits = index.search("apple", k=2)
    assert len(hits) == 2
    assert hits[0].score >= hits[1].score
    assert "zzz qqq" not in [h.text for h in hits]


def test_index_search_min_score_filters(fake_embeddings):
    index = rag.Index(["apple pie", "zzz qqq"])
    assert index.search("apple", k=2, min_score=0.99) == []


def test_index_search_keyword_weight_changes_score(fake_embeddings):
    index = rag.Index(["apple pie"])
    plain = index.search("apple pie", k=1)[0]
    boosted = index.search("apple pie", k=1, keyword_weight=1.0)[0]
    assert boosted.score == pytest.approx(plain.cosine + plain.keyword)
