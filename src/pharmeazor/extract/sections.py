
"""Splitting a leaflet or RCP into the rubriques the project needs."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from ..schemas import Section

__all__ = ["SectionSplit", "split_sections", "HEADING_PATTERNS"]

# Accept section numbers followed by a dot, a dash, or a space.
_NUMBER = r"(?:\d+(?:\.\d+)*[.)]?\s*[-–]?\s*)?"

HEADING_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (Section.CONTRAINDICATIONS, re.compile(
        r"^\s*" + _NUMBER + r"(?:contre[-\s]?indications?"
        r"|ne (?:prenez|utilisez) jamais"
        r"|quand ne (?:faut|doit)[- ]il pas)", re.I)),
    (Section.INTERACTIONS, re.compile(
        r"^\s*" + _NUMBER + r"(?:interactions?"
        r"|associations? (?:medicamenteuses?|deconseillees?)"
        r"|autres medicaments et)", re.I)),
    (Section.POSOLOGY, re.compile(
        r"^\s*" + _NUMBER + r"(?:posologie"
        r"|mode (?:et voie )?d.administration"
        r"|comment (?:prendre|utiliser)"
        r"|dose|doses|dosage)", re.I)),
    (Section.INDICATIONS, re.compile(
        r"^\s*" + _NUMBER + r"(?:indications?(?: therapeutiques?)?"
        r"|dans quels? cas"
        r"|qu.est[- ]ce que .* et dans quels? cas)", re.I)),
    (Section.ADVERSE, re.compile(
        r"^\s*" + _NUMBER + r"(?:effets? indesirables?"
        r"|quels? sont les effets"
        r"|effets? secondaires?)", re.I)),
]

_HEADING_SHAPE = re.compile(r"^\s*(?:\d[\d.]*\s*[-–.)]?\s*)?[^\n]{3,180}$")


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _looks_like_heading(line: str) -> bool:
    """Heuristics for a heading: short, no sentence-ending period, not a list item."""
    stripped = line.strip()
    if not stripped or len(stripped) > 180:
        return False
    if stripped.endswith((".", ";", ",")):
        return False
    if stripped.startswith(("-", "•", "*")):
        return False
    return bool(_HEADING_SHAPE.match(stripped))


def classify_heading(line: str) -> str | None:
    """Map one heading line to a canonical section name, or None."""
    probe = _strip_accents(line)
    for section, pattern in HEADING_PATTERNS:
        if pattern.match(probe):
            return section
    return None


@dataclass
class SectionSplit:
    """The outcome of splitting one document."""

    sections: dict[str, str] = field(default_factory=dict)
    unmapped: dict[str, str] = field(default_factory=dict)

    @property
    def coverage(self) -> float:
        """Share of the four required rubriques that were found, in [0, 1]."""
        required = {
            Section.INDICATIONS, Section.CONTRAINDICATIONS,
            Section.POSOLOGY, Section.INTERACTIONS,
        }
        return len(required & set(self.sections)) / len(required)

    def missing(self) -> list[str]:
        required = [
            Section.INDICATIONS, Section.CONTRAINDICATIONS,
            Section.POSOLOGY, Section.INTERACTIONS,
        ]
        return [s for s in required if s not in self.sections]


def split_sections(text: str) -> SectionSplit:
    """Split a plain-text leaflet into rubriques."""
    split = SectionSplit()
    current_key: str | None = None
    current_bucket: dict[str, str] | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current_key is None or current_bucket is None:
            return
        body = "\n".join(buffer).strip()
        existing = current_bucket.get(current_key)
        current_bucket[current_key] = (
            (existing + "\n" + body).strip() if existing else body
        )

    for line in text.splitlines():
        if _looks_like_heading(line):
            section = classify_heading(line)
            if section is not None:
                flush()
                current_key, current_bucket, buffer = section, split.sections, []
                continue
            if current_key is not None and re.match(
                r"^\s*\d+(?:\.\d+)*[.)]?\s*[-–]?\s+\S", line
            ):
                flush()
                current_key, current_bucket, buffer = line.strip(), split.unmapped, []
                continue
        buffer.append(line)

    flush()
    return split
