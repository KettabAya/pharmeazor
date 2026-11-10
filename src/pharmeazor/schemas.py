"""Core data model for Pharmeazor.

Every object that travels through the pipeline carries its provenance. A value
without a :class:`Provenance` cannot be displayed to the user -- that rule is
enforced here by making provenance a required field rather than an optional one.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from enum import IntEnum


class Authority(IntEnum):
    """Authority ranking of a source, from the project's golden rule.

    Higher is more trustworthy. When two sources disagree, the higher rank wins
    and the system must be able to say why.
    """

    DISCARDED = 0       # forums, blogs, social media, advertising, prices, stock
    PROFESSIONAL = 1    # Pharm'Net, MEDAlgerie, dzair-pharma -- practical, unofficial
    INSTITUTIONAL = 2   # ANSM Thesaurus, DailyMed, EMA -- foreign, complement only
    NOMENCLATURE = 3    # official registry, Ministry of Pharmaceutical Industry
    OFFICIAL = 4        # RCP and patient leaflets validated by the ANPP

    @property
    def label_fr(self) -> str:
        return {
            Authority.DISCARDED: "Écartée",
            Authority.PROFESSIONAL: "Secondaire",
            Authority.INSTITUTIONAL: "Institutionnelle",
            Authority.NOMENCLATURE: "Officielle (nomenclature)",
            Authority.OFFICIAL: "Officielle (RCP / notice)",
        }[self]

    @property
    def is_algerian_official(self) -> bool:
        """Foreign sources complement the Algerian source; they never replace it."""
        return self in (Authority.OFFICIAL, Authority.NOMENCLATURE)


class Section(str):
    """Canonical section names extracted from a leaflet or RCP."""

    INDICATIONS = "indications"
    CONTRAINDICATIONS = "contre_indications"
    POSOLOGY = "posologie"
    INTERACTIONS = "interactions"
    ADVERSE = "effets_indesirables"


class InteractionLevel(IntEnum):
    """The four ANSM Thesaurus levels, from mildest to most serious.

    The system always states the level and its source, and never downgrades a
    level into reassurance. "No interaction found" is not "no risk".
    """

    TAKE_INTO_ACCOUNT = 1
    PRECAUTION = 2
    DISCOURAGED = 3
    CONTRAINDICATED = 4

    @property
    def label_fr(self) -> str:
        return {
            InteractionLevel.TAKE_INTO_ACCOUNT: "À prendre en compte",
            InteractionLevel.PRECAUTION: "Précaution d'emploi",
            InteractionLevel.DISCOURAGED: "Association déconseillée",
            InteractionLevel.CONTRAINDICATED: "Contre-indication",
        }[self]


@dataclass(frozen=True)
class Provenance:
    """Where a piece of text came from, and when we took it.

    Collected alongside every document so that a reader can always trace a claim
    back to its origin and judge how fresh it is.
    """

    source_id: str
    url: str
    authority: Authority
    collected_at: _dt.date
    language: str = "fr"
    country: str = "DZ"
    checksum: str | None = None

    def cite(self) -> str:
        return (
            f"{self.source_id} [{self.authority.label_fr}] "
            f"— collecté le {self.collected_at:%d/%m/%Y}"
        )


@dataclass
class Document:
    """A raw document (leaflet, RCP, interaction table) converted to text."""

    doc_id: str
    title: str
    text: str
    provenance: Provenance
    drug_ids: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)


@dataclass
class Passage:
    """A contiguous span of a document, the unit that retrieval returns."""

    passage_id: str
    doc_id: str
    text: str
    provenance: Provenance
    section: str | None = None
    char_start: int = 0
    char_end: int = 0


@dataclass
class Citation:
    """A passage put forward as evidence for part of an answer."""

    passage: Passage
    quote: str

    def __post_init__(self) -> None:
        if self.quote not in self.passage.text:
            raise ValueError(
                "A citation quote must appear verbatim in the cited passage. "
                "Refusing to build a citation the system cannot back up."
            )


@dataclass
class Claim:
    """One atomic statement about one drug, attached to its evidence."""

    drug_id: str
    field_name: str
    value: str
    citation: Citation

    @property
    def authority(self) -> Authority:
        return self.citation.passage.provenance.authority


@dataclass
class Conflict:
    """Two or more sources disagreeing on the same field of the same drug."""

    drug_id: str
    field_name: str
    retained: Claim
    divergent: list[Claim]

    @property
    def reason_fr(self) -> str:
        losing = ", ".join(
            f"{c.citation.passage.provenance.source_id} ({c.authority.label_fr})"
            for c in self.divergent
        )
        return (
            f"Valeur retenue : {self.retained.value} "
            f"({self.retained.citation.passage.provenance.source_id}, "
            f"{self.retained.authority.label_fr}). "
            f"Source(s) divergente(s) signalée(s) : {losing}."
        )


@dataclass
class Answer:
    """The imposed answer format: short answer, explanation, sources, limits."""

    short: str
    explanation: str
    citations: list[Citation]
    confidence: float
    limits: str
    conflicts: list[Conflict] = field(default_factory=list)
    refused: bool = False
    refusal_reason: str = ""

    def is_displayable(self) -> bool:
        """An answer with no citation is never shown, refusals excepted."""
        return self.refused or bool(self.citations)
