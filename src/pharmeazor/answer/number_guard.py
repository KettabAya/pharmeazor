"""Deterministic verification of every number an answer puts forward.

This is the project's signature control and it contains no model call at all.
Each numeric claim in a drafted answer is extracted with its unit, normalised,
and then looked for in the passages actually cited. A number that cannot be
found verbatim is *blocked*: it is never displayed as a fact.

The guard is intentionally strict and intentionally dumb. It does not reason
about whether 4 g and 4000 mg are the same quantity, because agreeing that they
are is a clinical judgement the system is not allowed to make on its own.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

__all__ = ["NumericClaim", "GuardReport", "extract_numbers", "verify"]

# Unit spellings that a French leaflet may use for the same unit. The guard
# compares canonical forms, so "24 heures", "24 h" and "24h" all match.
_UNIT_ALIASES: dict[str, str] = {
    "g": "g", "gramme": "g", "grammes": "g",
    "mg": "mg", "milligramme": "mg", "milligrammes": "mg",
    "mcg": "ug", "ug": "ug", "microgramme": "ug", "microgrammes": "ug",
    "ml": "ml", "millilitre": "ml", "millilitres": "ml",
    "l": "l", "litre": "l", "litres": "l",
    "h": "h", "heure": "h", "heures": "h",
    "min": "min", "minute": "min", "minutes": "min",
    "j": "j", "jour": "j", "jours": "j",
    "sem": "sem", "semaine": "sem", "semaines": "sem",
    "mois": "mois",
    "an": "an", "ans": "an", "annee": "an", "annees": "an",
    "kg": "kg", "kilogramme": "kg", "kilogrammes": "kg",
    "%": "%", "pour cent": "%", "pourcent": "%",
    "ui": "ui", "mmhg": "mmhg", "fois": "fois", "prise": "prise", "prises": "prise",
    "comprime": "comprime", "comprimes": "comprime",
}

_UNIT_PATTERN = "|".join(
    sorted((re.escape(u) for u in _UNIT_ALIASES), key=len, reverse=True)
)

# A number, optionally followed by a unit, optionally followed by "/ unit"
# (as in "4 g/24 h" or "500 mg / prise").
_NUMBER_RE = re.compile(
    r"(?P<value>\d{1,6}(?:[.,]\d{1,3})?)"
    r"\s*(?P<unit>" + _UNIT_PATTERN + r")?"
    r"(?:\s*/\s*(?P<per_value>\d{1,4})?\s*(?P<per_unit>" + _UNIT_PATTERN + r"))?",
    re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _canon_text(text: str) -> str:
    """Lowercase, de-accent, and flatten every kind of space and dash."""
    text = _strip_accents(text.lower())
    text = text.replace(" ", " ").replace(" ", " ")
    text = re.sub(r"[‐-―]", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def _canon_value(raw: str) -> str:
    """Normalise a decimal so that '4', '4.0' and '4,0' compare equal."""
    normalised = raw.replace(",", ".")
    try:
        number = float(normalised)
    except ValueError:
        return normalised
    if number.is_integer():
        return str(int(number))
    return f"{number:f}".rstrip("0").rstrip(".")


def _canon_unit(raw: str | None) -> str:
    if not raw:
        return ""
    return _UNIT_ALIASES.get(_canon_text(raw), _canon_text(raw))


@dataclass(frozen=True)
class NumericClaim:
    """One number lifted out of a drafted answer."""

    value: str
    unit: str = ""
    per_value: str = ""
    per_unit: str = ""
    raw: str = ""

    def key(self) -> tuple[str, str, str, str]:
        return (self.value, self.unit, self.per_value, self.per_unit)

    def __str__(self) -> str:
        head = f"{self.value}{(' ' + self.unit) if self.unit else ''}"
        if self.per_unit:
            per = f"{self.per_value} " if self.per_value else ""
            return f"{head} / {per}{self.per_unit}".strip()
        return head


@dataclass
class GuardReport:
    """Outcome of the check, and whether the answer may be displayed."""

    verified: list[NumericClaim] = field(default_factory=list)
    blocked: list[NumericClaim] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.verified) + len(self.blocked)

    @property
    def passed(self) -> bool:
        """An answer passes only when nothing was blocked."""
        return not self.blocked

    def summary_fr(self) -> str:
        if self.total == 0:
            return "Contrôle des chiffres : aucun chiffre à vérifier"
        if self.passed:
            return f"Contrôle des chiffres : {len(self.verified)}/{self.total} vérifiés"
        blocked = ", ".join(str(c) for c in self.blocked)
        return (
            f"Contrôle des chiffres : {len(self.verified)}/{self.total} vérifiés "
            f"— BLOQUÉ : {blocked} introuvable(s) dans les passages cités"
        )


def extract_numbers(text: str) -> list[NumericClaim]:
    """Pull every number, with its unit, out of ``text``.

    Duplicates are collapsed: an answer that states the same dose twice only
    needs that dose to be found once in the sources.
    """
    claims: dict[tuple[str, str, str, str], NumericClaim] = {}
    for match in _NUMBER_RE.finditer(_canon_text(text)):
        claim = NumericClaim(
            value=_canon_value(match.group("value")),
            unit=_canon_unit(match.group("unit")),
            per_value=_canon_value(match.group("per_value") or "") if match.group("per_value") else "",
            per_unit=_canon_unit(match.group("per_unit")),
            raw=match.group(0).strip(),
        )
        claims.setdefault(claim.key(), claim)
    return list(claims.values())


def _passage_claims(passages: list[str]) -> set[tuple[str, str, str, str]]:
    found: set[tuple[str, str, str, str]] = set()
    for passage in passages:
        for claim in extract_numbers(passage):
            found.add(claim.key())
            # A passage stating "4 g" also backs a bare "4" in the answer.
            found.add((claim.value, claim.unit, "", ""))
            found.add((claim.value, "", "", ""))
    return found


def verify(answer_text: str, cited_passages: list[str]) -> GuardReport:
    """Check that every number in ``answer_text`` appears in a cited passage.

    Args:
        answer_text: The drafted answer, before it is shown to anyone.
        cited_passages: The verbatim text of the passages the answer cites.

    Returns:
        A :class:`GuardReport`. When ``passed`` is False the answer must not be
        displayed as written; the blocked numbers have to be removed or the
        answer re-drafted against the sources.
    """
    available = _passage_claims(cited_passages)
    report = GuardReport()
    for claim in extract_numbers(answer_text):
        if claim.key() in available or (claim.value, claim.unit, "", "") in available:
            report.verified.append(claim)
        else:
            report.blocked.append(claim)
    return report
