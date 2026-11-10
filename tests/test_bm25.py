"""The keyword baseline the dense retriever has to beat."""

import pytest

from pharmeazor.retrieve.bm25 import BM25Index, tokenize


@pytest.fixture
def index() -> BM25Index:
    idx = BM25Index()
    idx.add("p1", "Posologie : ne pas dépasser 4 g de paracétamol par 24 heures.")
    idx.add("p2", "Contre-indications : hypersensibilité connue à l'ibuprofène.")
    idx.add("p3", "Interactions : association déconseillée avec les anticoagulants oraux.")
    idx.add("p4", "Indications : traitement symptomatique de la douleur et de la fièvre.")
    return idx.finalize()


class TestTokenize:
    def test_strips_accents_and_case(self):
        assert tokenize("Déconseillée") == tokenize("DECONSEILLEE")

    def test_drops_stopwords(self):
        assert "les" not in tokenize("les anticoagulants")

    def test_keeps_numbers(self):
        assert "500" in tokenize("500 mg par prise")


class TestSearch:
    def test_ranks_the_relevant_passage_first(self, index):
        assert index.search("dose maximale de paracétamol")[0].passage_id == "p1"

    def test_interaction_query_finds_interaction_passage(self, index):
        assert index.search("anticoagulants oraux association")[0].passage_id == "p3"

    def test_respects_top_k(self, index):
        assert len(index.search("paracétamol douleur interactions", top_k=2)) <= 2

    def test_query_with_no_overlap_returns_nothing(self, index):
        assert index.search("radiographie thoracique") == []

    def test_empty_index_returns_nothing(self):
        assert BM25Index().finalize().search("paracétamol") == []

    def test_scores_are_descending(self, index):
        scores = [r.score for r in index.search("paracétamol douleur")]
        assert scores == sorted(scores, reverse=True)

    def test_len_counts_indexed_passages(self, index):
        assert len(index) == 4
