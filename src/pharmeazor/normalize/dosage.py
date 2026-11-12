"""Reading the DOSAGE and CONDITIONNEMENT columns of the nomenclature.

Both columns are free text written by hand over many years, so they carry every
spelling the ministry has ever used: ``500MG``, ``325MG/37,5MG``, ``1G/125MG``,
``250MG/5ML``, ``0,03``, ``B/16``, ``B/FL 15 ML``.

Two rules run through this module:

1. **The original text is never thrown away.** Every result keeps its ``raw``
   value, so a citation can always quote exactly what the source said.
2. **Nothing is invented.** A dosage that cannot be parsed yields an empty
   component list rather than a guess, and the caller can see that it failed.
   A wrong dose is far worse than a missing one.

No unit conversion happens here. Deciding that ``1G`` and ``1000MG`` are the
same quantity is a pharmaceutical judgement, and the project's rules forbid the
system from making it alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = [
    "Component",
    "Strength",
    "Packaging",
    "parse_strength",
    "parse_packaging",
    "normalize_unit",
]

# Spellings met in the nomenclature, mapped to one canonical form.
_UNITS: dict[str, str] = {
    "MG": "mg", "G": "g", "GR": "g", "KG": "kg",
    "MCG": "µg", "UG": "µg", "µG": "µg", "MICROGRAMME": "µg",
    "ML": "ml", "L": "l", "CL": "cl",
    "UI": "UI", "U": "UI", "MUI": "MUI",
    "%": "%", "POURCENT": "%",
    "MEQ": "mEq", "MMOL": "mmol",
}

_NUMBER = r"\d+(?:[.,]\d+)?"
# A trailing '*' is a footnote marker used by the ministry (e.g. "875MG*/125MG*"),
# not part of the quantity. It is stripped, and the raw text keeps it.
_COMPONENT_RE = re.compile(
    rf"^\s*(?P<value>{_NUMBER})\s*(?P<unit>[A-Za-zµ%]+)?\s*\**\s*$"
)

# "B/16", "BTE/20", "B /10"
_PACK_COUNT_RE = re.compile(r"^\s*B\s*(?:TE|OITE)?\s*/\s*(?P<count>\d+)\s*$", re.I)
# "B/FL 15 ML", "B/ FL. 60ML"
_PACK_VOLUME_RE = re.compile(
    r"^\s*B\s*(?:TE|OITE)?\s*/\s*(?P<container>FL|FLACON|TUBE|SACHET|AMP|AMPOULE)\.?\s*"
    rf"(?P<value>{_NUMBER})\s*(?P<unit>ML|L|G|MG)\s*$",
    re.I,
)


def _to_float(text: str) -> float:
    """French decimals use a comma: '37,5' is 37.5."""
    return float(text.replace(",", "."))


def normalize_unit(raw: str | None) -> str:
    """Map a unit spelling to its canonical form; unknown units pass through."""
    if not raw:
        return ""
    key = raw.strip().upper()
    return _UNITS.get(key, raw.strip().lower())


@dataclass(frozen=True)
class Component:
    """One quantity inside a dosage, e.g. the 125MG of ``1G/125MG``."""

    value: float
    unit: str

    def __str__(self) -> str:
        number = int(self.value) if float(self.value).is_integer() else self.value
        return f"{number}{self.unit}" if self.unit else str(number)


@dataclass(frozen=True)
class Strength:
    """A parsed DOSAGE cell."""

    raw: str
    components: tuple[Component, ...] = ()
    unparsed: tuple[str, ...] = field(default=())

    @property
    def is_combination(self) -> bool:
        """True when the product holds more than one active quantity."""
        return len(self.components) > 1

    @property
    def parsed(self) -> bool:
        """False when nothing could be read — the caller must not invent a value."""
        return bool(self.components)

    def canonical(self) -> str:
        """A stable key for grouping equivalents: '500mg', '1g+125mg'."""
        return "+".join(str(c) for c in self.components)

    def __str__(self) -> str:
        return self.canonical() or self.raw


@dataclass(frozen=True)
class Packaging:
    """A parsed CONDITIONNEMENT cell."""

    raw: str
    count: int | None = None
    container: str = ""
    volume: Component | None = None

    @property
    def parsed(self) -> bool:
        return self.count is not None or self.volume is not None


def parse_strength(raw: str | None) -> Strength:
    """Read a DOSAGE cell into its quantities.

    Components are separated by ``/``. A fragment that holds no number (the
    trailing ``ML`` of ``100MG/12,5MG/ML``) is kept in ``unparsed`` rather than
    discarded, so nothing from the source silently disappears.

    >>> parse_strength("325MG/37,5MG").canonical()
    '325mg+37.5mg'
    >>> parse_strength("0,03").parsed
    True
    >>> parse_strength("CF NOTICE").parsed
    False
    """
    text = (raw or "").strip()
    if not text:
        return Strength(raw="")

    components: list[Component] = []
    unparsed: list[str] = []

    for fragment in text.split("/"):
        fragment = fragment.strip()
        if not fragment:
            continue
        match = _COMPONENT_RE.match(fragment)
        if match:
            components.append(
                Component(
                    value=_to_float(match.group("value")),
                    unit=normalize_unit(match.group("unit")),
                )
            )
        else:
            unparsed.append(fragment)

    return Strength(raw=text, components=tuple(components), unparsed=tuple(unparsed))


def parse_packaging(raw: str | None) -> Packaging:
    """Read a CONDITIONNEMENT cell.

    ``B/16`` is sixteen units in the box. ``B/FL 15 ML`` is a 15 ml bottle and
    has no unit count at all — returning 15 there would be a lie, so ``count``
    stays None and the volume is recorded separately.

    >>> parse_packaging("B/16").count
    16
    >>> parse_packaging("B/FL 15 ML").count is None
    True
    """
    text = (raw or "").strip()
    if not text:
        return Packaging(raw="")

    count_match = _PACK_COUNT_RE.match(text)
    if count_match:
        return Packaging(raw=text, count=int(count_match.group("count")))

    volume_match = _PACK_VOLUME_RE.match(text)
    if volume_match:
        return Packaging(
            raw=text,
            container=volume_match.group("container").upper(),
            volume=Component(
                value=_to_float(volume_match.group("value")),
                unit=normalize_unit(volume_match.group("unit")),
            ),
        )

    return Packaging(raw=text)
