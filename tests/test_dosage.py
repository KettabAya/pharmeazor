"""Dosage and packaging parsing, on strings taken from the real nomenclature."""

import pytest

from pharmeazor.normalize.dosage import (
    normalize_unit,
    parse_packaging,
    parse_strength,
)


class TestUnits:
    def test_known_spellings_are_canonical(self):
        assert normalize_unit("MG") == "mg"
        assert normalize_unit("G") == "g"
        assert normalize_unit("ML") == "ml"

    def test_microgram_variants_agree(self):
        assert normalize_unit("MCG") == normalize_unit("UG") == "µg"

    def test_unknown_unit_passes_through(self):
        assert normalize_unit("DOSE") == "dose"

    def test_empty_unit_is_empty(self):
        assert normalize_unit(None) == ""


class TestSimpleStrength:
    def test_single_quantity(self):
        s = parse_strength("500MG")
        assert s.canonical() == "500mg"
        assert not s.is_combination
        assert s.parsed

    def test_gram(self):
        assert parse_strength("1G").canonical() == "1g"

    def test_french_decimal_comma(self):
        assert parse_strength("37,5MG").canonical() == "37.5mg"

    def test_value_without_unit_is_kept(self):
        # "0,03" appears in the paracetamol rows with no unit at all.
        s = parse_strength("0,03")
        assert s.parsed
        assert s.canonical() == "0.03"

    def test_raw_text_is_always_preserved(self):
        assert parse_strength("  500MG ").raw == "500MG"


class TestCombinations:
    def test_two_actives(self):
        s = parse_strength("325MG/37,5MG")
        assert s.is_combination
        assert s.canonical() == "325mg+37.5mg"

    def test_amoxicillin_clavulanate(self):
        assert parse_strength("1G/125MG").canonical() == "1g+125mg"

    def test_amlodipine_valsartan(self):
        assert parse_strength("5MG/160MG").canonical() == "5mg+160mg"

    def test_concentration_keeps_both_parts(self):
        s = parse_strength("250MG/5ML")
        assert [str(c) for c in s.components] == ["250mg", "5ml"]

    def test_ministry_footnote_asterisks_are_ignored(self):
        # "875MG*/125MG*" is amoxicillin + clavulanic acid; the stars are notes.
        s = parse_strength("875MG*/125MG*")
        assert s.canonical() == "875mg+125mg"
        assert s.raw == "875MG*/125MG*"

    def test_trailing_unit_is_recorded_not_dropped(self):
        s = parse_strength("100MG/12,5MG/ML")
        assert s.canonical() == "100mg+12.5mg"
        assert s.unparsed == ("ML",)


class TestUnparsableStrength:
    def test_text_only_is_not_invented(self):
        s = parse_strength("CF NOTICE")
        assert not s.parsed
        assert s.components == ()
        assert s.unparsed == ("CF NOTICE",)

    def test_empty_cell(self):
        s = parse_strength("")
        assert not s.parsed
        assert s.raw == ""

    def test_none_cell(self):
        assert not parse_strength(None).parsed


class TestPackaging:
    @pytest.mark.parametrize(
        "raw,expected",
        [("B/16", 16), ("B/10", 10), ("B/15", 15), ("B/20", 20), ("B/100", 100)],
    )
    def test_box_counts(self, raw, expected):
        assert parse_packaging(raw).count == expected

    def test_bottle_has_no_unit_count(self):
        # "B/FL 15 ML" is a 15 ml bottle, not 15 tablets. Returning 15 would lie.
        pack = parse_packaging("B/FL 15 ML")
        assert pack.count is None
        assert pack.container == "FL"
        assert str(pack.volume) == "15ml"

    def test_unrecognised_packaging_is_not_guessed(self):
        pack = parse_packaging("CONDITIONNEMENT HOSPITALIER")
        assert pack.count is None
        assert not pack.parsed
        assert pack.raw == "CONDITIONNEMENT HOSPITALIER"

    def test_empty_cell(self):
        assert not parse_packaging("").parsed
