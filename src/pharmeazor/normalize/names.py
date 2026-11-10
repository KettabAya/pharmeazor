"""Resolving the many ways a single drug gets written.

For a machine, "Doliprane 1000", "doliprane 1g", "dolipran" and "paracétamol"
are four different strings. For a pharmacist they are often one product. This
module closes that gap, and — just as importantly — refuses to close it when
two candidates are genuinely too close to call.

Ambiguity is surfaced, never silently resolved: two drugs with similar names is
exactly the trap the evaluation set is built to catch.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

__all__ = [
    "DrugEntry",
    "Match",
    "Ambiguity",
    "normalize",
    "levenshtein",
    "trigram_similarity",
    "score",
    "NameResolver",
]

# Dosage, galenic form and packaging tokens carry no identity on their own.
_NOISE = {
    "comprime", "comprimes", "cp", "gelule", "gelules", "sachet", "sachets",
    "sirop", "solution", "suspension", "injectable", "pommade", "creme",
    "effervescent", "effervescents", "lp", "mg", "g", "ml", "ui", "pour",
    "boite", "de", "du", "la", "le", "les", "a", "au", "aux", "et",
}


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize(name: str) -> str:
    """Reduce a written name to its identifying core.

    Lowercases, strips accents, drops dosage/form/packaging noise and bare
    numbers, and collapses whitespace.

    >>> normalize("Doliprane 1000 mg comprimé")
    'doliprane'
    """
    text = _strip_accents(name.lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in _NOISE and not t.isdigit()]
    tokens = [re.sub(r"\d+", "", t) for t in tokens]
    return " ".join(t for t in tokens if t).strip()


def levenshtein(a: str, b: str) -> int:
    """Edit distance between two strings, iterative two-row implementation."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(
                previous[j] + 1,          # deletion
                current[j - 1] + 1,       # insertion
                previous[j - 1] + (ca != cb),  # substitution
            ))
        previous = current
    return previous[-1]


def _trigrams(text: str) -> set[str]:
    padded = f"  {text} "
    return {padded[i:i + 3] for i in range(len(padded) - 2)}


def trigram_similarity(a: str, b: str) -> float:
    """Jaccard similarity over character trigrams, in [0, 1].

    Robust to transposed or inserted letters in a way edit distance is not,
    which matters for the typos a hurried pharmacist actually makes.
    """
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def score(query: str, candidate: str) -> float:
    """Blend edit distance and trigram overlap into a single score in [0, 1]."""
    q, c = normalize(query), normalize(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    distance = levenshtein(q, c)
    edit_score = 1.0 - distance / max(len(q), len(c))
    return max(0.0, 0.6 * edit_score + 0.4 * trigram_similarity(q, c))


@dataclass(frozen=True)
class DrugEntry:
    """One product in the reference dictionary built by the team."""

    drug_id: str
    inn: str                       # DCI, e.g. "paracétamol"
    brand_names: tuple[str, ...] = ()
    atc_code: str = ""
    strength: str = ""
    form: str = ""

    def aliases(self) -> tuple[str, ...]:
        return (self.inn,) + self.brand_names

    def is_equivalent_to(self, other: DrugEntry) -> bool:
        """Same substance, same strength, same form — a registered equivalent."""
        return (
            normalize(self.inn) == normalize(other.inn)
            and self.strength.lower() == other.strength.lower()
            and self.form.lower() == other.form.lower()
            and self.drug_id != other.drug_id
        )


@dataclass(frozen=True)
class Match:
    """A confident resolution of a written name to one entry."""

    entry: DrugEntry
    matched_alias: str
    confidence: float


@dataclass(frozen=True)
class Ambiguity:
    """Two or more candidates too close to separate. Ask, do not guess."""

    query: str
    candidates: tuple[Match, ...]

    def message_fr(self) -> str:
        names = ", ".join(f"{m.entry.inn} ({m.entry.drug_id})" for m in self.candidates)
        return (
            f"« {self.query} » peut désigner plusieurs produits : {names}. "
            "Précisez le dosage ou la forme — le système ne tranche pas seul."
        )


class NameResolver:
    """Resolve written names against the team's reference dictionary.

    Args:
        entries: The reference drug list.
        threshold: Minimum score for a candidate to be considered at all.
        margin: If the two best candidates are within this distance of each
            other, the result is an :class:`Ambiguity` rather than a match.
    """

    def __init__(
        self,
        entries: list[DrugEntry],
        threshold: float = 0.62,
        margin: float = 0.08,
    ) -> None:
        self.entries = entries
        self.threshold = threshold
        self.margin = margin

    def rank(self, query: str) -> list[Match]:
        """All candidates above the threshold, best first."""
        matches: list[Match] = []
        for entry in self.entries:
            best_alias, best_score = "", 0.0
            for alias in entry.aliases():
                s = score(query, alias)
                if s > best_score:
                    best_alias, best_score = alias, s
            if best_score >= self.threshold:
                matches.append(Match(entry, best_alias, round(best_score, 4)))
        return sorted(matches, key=lambda m: m.confidence, reverse=True)

    def resolve(self, query: str) -> Match | Ambiguity | None:
        """Resolve one name, flagging ambiguity instead of guessing."""
        ranked = self.rank(query)
        if not ranked:
            return None
        if len(ranked) > 1 and ranked[0].confidence - ranked[1].confidence < self.margin:
            close = tuple(
                m for m in ranked
                if ranked[0].confidence - m.confidence < self.margin
            )
            return Ambiguity(query=query, candidates=close)
        return ranked[0]

    def equivalents(self, entry: DrugEntry) -> list[DrugEntry]:
        """Registered equivalents — what to suggest when a product is out of stock."""
        return [e for e in self.entries if entry.is_equivalent_to(e)]
