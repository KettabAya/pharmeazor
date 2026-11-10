"""Source reconciliation: the higher-ranked source wins, and we say why."""

import datetime as dt

import pytest

from pharmeazor.reconcile.conflicts import ConflictPolicy, arbitrate, detect
from pharmeazor.schemas import Authority, Citation, Claim, Passage, Provenance


def make_claim(
    source_id: str,
    authority: Authority,
    value: str,
    *,
    day: int = 1,
    country: str = "DZ",
    field_name: str = "dose_max_24h",
) -> Claim:
    provenance = Provenance(
        source_id=source_id,
        url=f"https://example.test/{source_id}",
        authority=authority,
        collected_at=dt.date(2026, 3, day),
        country=country,
    )
    text = f"Posologie : ne pas dépasser {value} par 24 h."
    passage = Passage(f"p-{source_id}", f"d-{source_id}", text, provenance)
    return Claim("DZ-001", field_name, value, Citation(passage, f"{value} par 24 h"))


class TestCitationIntegrity:
    def test_quote_must_appear_in_passage(self):
        provenance = Provenance("x", "https://e.test", Authority.OFFICIAL, dt.date(2026, 3, 1))
        passage = Passage("p1", "d1", "texte réel", provenance)
        with pytest.raises(ValueError):
            Citation(passage, "texte inventé")


class TestArbitration:
    def test_official_beats_professional(self):
        claims = [
            make_claim("pharmnet", Authority.PROFESSIONAL, "3 g"),
            make_claim("anpp", Authority.OFFICIAL, "4 g"),
        ]
        assert arbitrate(claims).value == "4 g"

    def test_discarded_sources_are_never_retained(self):
        claims = [
            make_claim("forum", Authority.DISCARDED, "10 g"),
            make_claim("pharmnet", Authority.PROFESSIONAL, "3 g"),
        ]
        assert arbitrate(claims).value == "3 g"

    def test_all_discarded_raises(self):
        with pytest.raises(ValueError):
            arbitrate([make_claim("forum", Authority.DISCARDED, "10 g")])

    def test_algerian_official_beats_foreign_institutional(self):
        claims = [
            make_claim("ansm", Authority.INSTITUTIONAL, "3 g", country="FR"),
            make_claim("anpp", Authority.NOMENCLATURE, "4 g"),
        ]
        assert arbitrate(claims).value == "4 g"

    def test_same_rank_prefers_the_fresher_collection(self):
        claims = [
            make_claim("anpp-old", Authority.OFFICIAL, "3 g", day=1),
            make_claim("anpp-new", Authority.OFFICIAL, "4 g", day=20),
        ]
        assert arbitrate(claims).value == "4 g"

    def test_recency_preference_can_be_switched_off(self):
        claims = [
            make_claim("anpp-old", Authority.OFFICIAL, "3 g", day=1),
            make_claim("anpp-new", Authority.OFFICIAL, "4 g", day=20),
        ]
        policy = ConflictPolicy(prefer_recent_on_tie=False)
        assert arbitrate(claims, policy).value in {"3 g", "4 g"}


class TestDetection:
    def test_agreement_produces_no_conflict(self):
        claims = [
            make_claim("anpp", Authority.OFFICIAL, "4 g"),
            make_claim("pharmnet", Authority.PROFESSIONAL, "4 g"),
        ]
        assert detect(claims) == []

    def test_disagreement_is_reported_with_both_sides(self):
        claims = [
            make_claim("anpp", Authority.OFFICIAL, "4 g"),
            make_claim("pharmnet", Authority.PROFESSIONAL, "3 g"),
        ]
        conflicts = detect(claims)
        assert len(conflicts) == 1
        assert conflicts[0].retained.value == "4 g"
        assert [c.value for c in conflicts[0].divergent] == ["3 g"]

    def test_reason_names_the_losing_source(self):
        claims = [
            make_claim("anpp", Authority.OFFICIAL, "4 g"),
            make_claim("pharmnet", Authority.PROFESSIONAL, "3 g"),
        ]
        reason = detect(claims)[0].reason_fr
        assert "pharmnet" in reason
        assert "4 g" in reason

    def test_conflicts_are_detected_per_field(self):
        claims = [
            make_claim("anpp", Authority.OFFICIAL, "4 g", field_name="dose_max_24h"),
            make_claim("pharmnet", Authority.PROFESSIONAL, "3 g", field_name="dose_max_24h"),
            make_claim("anpp", Authority.OFFICIAL, "6 h", field_name="intervalle_min"),
            make_claim("pharmnet", Authority.PROFESSIONAL, "6 h", field_name="intervalle_min"),
        ]
        conflicts = detect(claims)
        assert {c.field_name for c in conflicts} == {"dose_max_24h"}
