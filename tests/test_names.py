"""Name normalisation, and the refusal to guess between close candidates."""

import pytest

from pharmeazor.normalize.names import (
    Ambiguity,
    DrugEntry,
    Match,
    NameResolver,
    levenshtein,
    normalize,
    trigram_similarity,
)


@pytest.fixture
def catalogue() -> list[DrugEntry]:
    return [
        DrugEntry("DZ-001", "paracétamol", ("Doliprane", "Efferalgan"), "N02BE01", "1000 mg", "comprimé"),
        DrugEntry("DZ-002", "ibuprofène", ("Nurofen", "Advil"), "M01AE01", "400 mg", "comprimé"),
        DrugEntry("DZ-003", "amoxicilline", ("Clamoxyl",), "J01CA04", "500 mg", "gélule"),
        DrugEntry("DZ-004", "paracétamol", ("Panadol",), "N02BE01", "1000 mg", "comprimé"),
    ]


class TestNormalize:
    def test_drops_dosage_and_form(self):
        assert normalize("Doliprane 1000 mg comprimé") == "doliprane"

    def test_strips_accents_and_case(self):
        assert normalize("Ibuprofène") == normalize("IBUPROFENE")

    def test_empty_input_is_empty(self):
        assert normalize("500 mg") == ""


class TestDistances:
    def test_levenshtein_identity_is_zero(self):
        assert levenshtein("doliprane", "doliprane") == 0

    def test_levenshtein_counts_single_edit(self):
        assert levenshtein("dolipran", "doliprane") == 1

    def test_trigram_similarity_is_bounded(self):
        assert 0.0 <= trigram_similarity("doliprane", "dolipran") <= 1.0

    def test_unrelated_names_score_low(self):
        assert trigram_similarity("doliprane", "amoxicilline") < 0.2


class TestResolver:
    def test_brand_name_resolves(self, catalogue):
        result = NameResolver(catalogue).resolve("Nurofen")
        assert isinstance(result, Match)
        assert result.entry.drug_id == "DZ-002"

    def test_inn_resolves(self, catalogue):
        result = NameResolver(catalogue).resolve("ibuprofène")
        assert isinstance(result, Match)
        assert result.entry.drug_id == "DZ-002"

    def test_typo_resolves(self, catalogue):
        result = NameResolver(catalogue).resolve("ibuprofen")
        assert isinstance(result, Match)
        assert result.entry.drug_id == "DZ-002"

    def test_unknown_name_returns_none(self, catalogue):
        assert NameResolver(catalogue).resolve("zzzqwerty") is None

    def test_two_products_sharing_an_inn_are_ambiguous(self, catalogue):
        result = NameResolver(catalogue).resolve("paracétamol")
        assert isinstance(result, Ambiguity)
        assert len(result.candidates) == 2
        assert "ne tranche pas seul" in result.message_fr()

    def test_equivalents_share_substance_strength_and_form(self, catalogue):
        resolver = NameResolver(catalogue)
        doliprane = catalogue[0]
        equivalents = resolver.equivalents(doliprane)
        assert [e.drug_id for e in equivalents] == ["DZ-004"]

    def test_a_drug_is_not_its_own_equivalent(self, catalogue):
        assert catalogue[0] not in NameResolver(catalogue).equivalents(catalogue[0])
