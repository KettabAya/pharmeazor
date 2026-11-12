"""The catalogue, the name dictionary and the equivalence rule."""

from pathlib import Path

import pytest

from pharmeazor.normalize.catalogue import Catalogue, form_family

CSV = Path(__file__).resolve().parents[1] / "data" / "reference" / "drugs_semaine1.csv"

pytestmark = pytest.mark.skipif(
    not CSV.exists(), reason="drugs_semaine1.csv not extracted yet"
)


@pytest.fixture(scope="module")
def catalogue() -> Catalogue:
    return Catalogue.from_csv(CSV)


class TestFormFamily:
    def test_coating_and_score_do_not_change_the_family(self):
        assert form_family("COMPRIME PELLICULE SECABLE") == "COMPRIME"
        assert form_family("COMPRIME") == "COMPRIME"

    def test_powder_for_suspension_is_a_powder(self):
        # The source misspells it "SUSPENSSION"; the family must survive that.
        assert form_family("POUDRE POUR SUSPENSSION BUVABLE") == "POUDRE"

    def test_capsule_family(self):
        assert form_family("GELULE") == "GELULE"

    def test_empty_form(self):
        assert form_family("") == ""


class TestLoading:
    def test_loads_every_row(self, catalogue):
        assert len(catalogue.products) == 284

    def test_the_three_classes_are_present(self, catalogue):
        classes = {p.therapeutic_class for p in catalogue.products}
        assert classes == {"antalgique_ains", "antibiotique", "antihypertenseur"}

    def test_strengths_were_parsed_for_the_vast_majority(self, catalogue):
        parsed = sum(1 for p in catalogue.products if p.strength.parsed)
        assert parsed / len(catalogue.products) > 0.95

    def test_every_product_can_cite_its_source(self, catalogue):
        prov = catalogue.products[0].provenance()
        assert "nomenclature" in prov.source_id
        assert "2026" in prov.cite()


class TestNameIndex:
    def test_brand_name_resolves(self, catalogue):
        assert catalogue.find_by_name("EFFERALGAN")

    def test_inn_resolves_to_many_products(self, catalogue):
        assert len(catalogue.find_by_name("PARACETAMOL")) > 50

    def test_lookup_ignores_case_and_accents(self, catalogue):
        assert catalogue.find_by_name("efferalgan") == catalogue.find_by_name("EFFERALGAN")

    def test_unknown_name_returns_nothing(self, catalogue):
        assert catalogue.find_by_name("ZZZ-INEXISTANT") == []

    def test_aliases_cover_all_four_kinds(self, catalogue):
        kinds = {a.kind for a in catalogue.aliases()}
        assert kinds == {"brand", "inn", "code", "registration"}

    def test_drug_entries_feed_the_resolver(self, catalogue):
        from pharmeazor.normalize.names import NameResolver

        entries = catalogue.drug_entries()
        assert len(entries) == len(catalogue.products)
        # A typo on a brand name must still reach a product.
        result = NameResolver(entries[:60]).resolve("EFERALGAN")
        assert result is not None


class TestEquivalence:
    def test_products_group_by_substance_strength_and_form(self, catalogue):
        groups = catalogue.groups()
        assert groups
        biggest = groups[0]
        assert biggest.size > 1
        assert len({p.inn for p in biggest.products}) == 1
        assert len({p.strength.canonical() for p in biggest.products}) == 1

    def test_a_tablet_never_groups_with_a_syrup(self, catalogue):
        for group in catalogue.groups():
            assert len({p.form_family for p in group.products}) == 1

    def test_products_without_a_readable_strength_are_excluded(self, catalogue):
        grouped = {p.drug_id for g in catalogue.groups() for p in g.products}
        for product in catalogue.products:
            if not product.strength.parsed:
                assert product.drug_id not in grouped


class TestEquivalentsAnswer:
    def test_unknown_name_is_refused_not_guessed(self, catalogue):
        answer = catalogue.equivalents_of("ZZZ-INEXISTANT")
        assert answer["refused"]
        assert answer["citations"] == []

    def test_ambiguous_name_asks_instead_of_choosing(self, catalogue):
        # A brand sold in several strengths must not be resolved silently.
        ambiguous = None
        for product in catalogue.products:
            same = catalogue.find_by_name(product.brand_name)
            if len({m.equivalence_key for m in same}) > 1:
                ambiguous = product.brand_name
                break
        if ambiguous is None:
            pytest.skip("no ambiguous brand in this extract")
        answer = catalogue.equivalents_of(ambiguous)
        assert answer["refused"]
        assert "Précisez" in answer["limits"]

    def test_a_resolved_answer_carries_a_citation_per_product(self, catalogue):
        answer = None
        for group in catalogue.groups():
            if group.size < 2:
                continue
            candidate = group.products[0]
            trial = catalogue.equivalents_of(candidate.brand_name)
            if not trial["refused"]:
                answer = trial
                break
        assert answer is not None, "expected at least one unambiguous product"
        assert answer["equivalents"]
        assert len(answer["citations"]) == len(answer["equivalents"]) + 1
        assert all(c["registration_no"] for c in answer["citations"])

    def test_answer_states_its_limits(self, catalogue):
        for group in catalogue.groups():
            trial = catalogue.equivalents_of(group.products[0].brand_name)
            if not trial["refused"]:
                assert "posologie" in trial["limits"]
                return
        pytest.skip("no unambiguous product found")
