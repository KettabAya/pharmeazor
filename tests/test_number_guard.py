"""The number guard is the control the whole project leans on. Test it hard."""

from pharmeazor.answer.number_guard import extract_numbers, verify


class TestExtraction:
    def test_pulls_value_and_unit(self):
        claims = extract_numbers("La dose maximale est de 4 g par 24 h.")
        rendered = {str(c) for c in claims}
        assert "4 g" in rendered
        assert "24 h" in rendered

    def test_handles_compound_rate(self):
        claims = extract_numbers("Ne pas dépasser 3 g/24 h.")
        assert any(c.value == "3" and c.unit == "g" and c.per_unit == "h" for c in claims)

    def test_french_decimal_comma_equals_point(self):
        assert extract_numbers("2,5 mg")[0].value == extract_numbers("2.5 mg")[0].value

    def test_deduplicates_repeated_values(self):
        claims = extract_numbers("500 mg le matin et 500 mg le soir")
        assert len([c for c in claims if c.unit == "mg"]) == 1


class TestVerification:
    def test_number_present_in_passage_passes(self):
        report = verify(
            "La dose maximale est de 4 g par 24 h.",
            ["Posologie : ne pas dépasser 4 g de paracétamol par 24 h chez l'adulte."],
        )
        assert report.passed
        assert report.blocked == []

    def test_number_absent_from_passage_is_blocked(self):
        report = verify(
            "La dose maximale est de 6 g par 24 h.",
            ["Posologie : ne pas dépasser 4 g par 24 h."],
        )
        assert not report.passed
        assert any(c.value == "6" for c in report.blocked)

    def test_unit_spelling_variants_still_match(self):
        report = verify("à renouveler après 6 heures", ["intervalle minimal de 6 h"])
        assert report.passed

    def test_spacing_variants_still_match(self):
        report = verify("500mg par prise", ["chaque comprimé contient 500 mg"])
        assert report.passed

    def test_answer_with_no_numbers_passes_trivially(self):
        report = verify("La DCI est le paracétamol.", ["substance active : paracétamol"])
        assert report.passed
        assert report.total == 0
        assert "aucun chiffre" in report.summary_fr()

    def test_empty_sources_block_every_number(self):
        report = verify("Dose de 4 g.", [])
        assert not report.passed
        assert len(report.blocked) == 1

    def test_summary_names_the_blocked_value(self):
        report = verify("jusqu'à 8 g par jour", ["maximum 4 g par jour"])
        assert "BLOQUÉ" in report.summary_fr()
        assert "8 g" in report.summary_fr()
