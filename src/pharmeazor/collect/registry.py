"""The source registry: who we collect from, and under what conditions.

Terms of use and ``robots.txt`` are read and recorded *before* any automated
collection. A source that forbids crawling is used manually or dropped — never
worked around. :func:`assert_collectable` is the gate the collectors call, so
that rule is enforced in code rather than only promised in the report.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ..config import settings
from ..schemas import Authority

__all__ = ["SourceAccess", "SourceSpec", "SourceRegistry", "assert_collectable"]


class SourceAccess:
    """How a source may legitimately be gathered."""

    AUTOMATED = "automated"   # crawling allowed, with delays
    MANUAL = "manual"         # robots.txt or ToS forbid automation
    FORBIDDEN = "forbidden"   # not to be used at all


class CollectionNotPermitted(RuntimeError):
    """Raised when code tries to crawl a source that disallows it."""


@dataclass(frozen=True)
class SourceSpec:
    """One declared source and its compliance record."""

    source_id: str
    name: str
    base_url: str
    authority: Authority
    access: str
    robots_checked_on: _dt.date | None = None
    robots_note: str = ""
    terms_note: str = ""
    country: str = "DZ"
    language: str = "fr"

    @property
    def is_automatable(self) -> bool:
        return self.access == SourceAccess.AUTOMATED

    def describe(self) -> str:
        checked = (
            f"robots.txt lu le {self.robots_checked_on:%d/%m/%Y}"
            if self.robots_checked_on else "robots.txt NON VÉRIFIÉ"
        )
        return f"{self.name} [{self.authority.label_fr}] — accès {self.access}, {checked}"


def assert_collectable(spec: SourceSpec) -> None:
    """Refuse automated collection unless the source permits it.

    Raises:
        CollectionNotPermitted: if the source is manual-only or forbidden, or if
            nobody has recorded a robots.txt check for it yet.
    """
    if spec.access == SourceAccess.FORBIDDEN:
        raise CollectionNotPermitted(
            f"{spec.source_id}: source écartée du corpus, aucune collecte."
        )
    if spec.access == SourceAccess.MANUAL:
        raise CollectionNotPermitted(
            f"{spec.source_id}: téléchargement manuel uniquement "
            f"({spec.robots_note or 'robots.txt / CGU restrictifs'})."
        )
    if settings.respect_robots_txt and spec.robots_checked_on is None:
        raise CollectionNotPermitted(
            f"{spec.source_id}: robots.txt et conditions d'utilisation pas encore "
            "consignés. Documentez-les dans docs/DATA_SOURCES.md avant de collecter."
        )


@dataclass
class SourceRegistry:
    """All declared sources, loaded from ``data/reference/source_registry.yaml``."""

    specs: dict[str, SourceSpec]

    @classmethod
    def load(cls, path: Path | None = None) -> SourceRegistry:
        """Read the YAML registry.

        Requires PyYAML. Kept as a soft import so the core modules and their
        tests run with no third-party dependency installed.
        """
        import yaml  # local import on purpose

        path = path or (settings.reference_dir / "source_registry.yaml")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        specs: dict[str, SourceSpec] = {}
        for entry in raw.get("sources", []):
            checked = entry.get("robots_checked_on")
            specs[entry["source_id"]] = SourceSpec(
                source_id=entry["source_id"],
                name=entry["name"],
                base_url=entry.get("base_url", ""),
                authority=Authority[entry["authority"]],
                access=entry.get("access", SourceAccess.MANUAL),
                robots_checked_on=(
                    _dt.date.fromisoformat(checked) if checked else None
                ),
                robots_note=entry.get("robots_note", ""),
                terms_note=entry.get("terms_note", ""),
                country=entry.get("country", "DZ"),
                language=entry.get("language", "fr"),
            )
        return cls(specs=specs)

    def __getitem__(self, source_id: str) -> SourceSpec:
        return self.specs[source_id]

    def __iter__(self) -> Iterator[SourceSpec]:
        return iter(self.specs.values())

    def automatable(self) -> list[SourceSpec]:
        return [s for s in self if s.is_automatable]

    def by_authority(self) -> list[SourceSpec]:
        """Sources from most to least authoritative."""
        return sorted(self, key=lambda s: int(s.authority), reverse=True)
