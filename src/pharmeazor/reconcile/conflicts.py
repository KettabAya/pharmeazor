"""Detecting and arbitrating disagreements between sources.

When two documents state different things about the same field of the same
drug, the disagreement is *shown*, not hidden. The higher-ranked source wins,
and the system explains the arbitration. The losing source stays visible with
its own passage and date, so a pharmacist can judge for themselves.

A foreign source never overrides an Algerian official one, even when it ranks
higher on paper: each authority validates its own text, so a foreign leaflet is
a complement and is reported as such.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..schemas import Authority, Claim, Conflict

__all__ = ["ConflictPolicy", "group_claims", "detect", "arbitrate"]


@dataclass(frozen=True)
class ConflictPolicy:
    """How ties and cross-country disagreements are handled.

    Args:
        prefer_algerian: When the best foreign source outranks the best Algerian
            official source, keep the Algerian value and report the foreign one
            as a complement.
        prefer_recent_on_tie: When two claims share the same authority rank,
            keep the one collected most recently.
    """

    prefer_algerian: bool = True
    prefer_recent_on_tie: bool = True


def group_claims(claims: list[Claim]) -> dict[tuple[str, str], list[Claim]]:
    """Bucket claims by the (drug, field) pair they talk about."""
    grouped: dict[tuple[str, str], list[Claim]] = defaultdict(list)
    for claim in claims:
        grouped[(claim.drug_id, claim.field_name)].append(claim)
    return dict(grouped)


def _normalise(value: str) -> str:
    return " ".join(value.lower().split())


def _sort_key(claim: Claim, policy: ConflictPolicy) -> tuple:
    provenance = claim.citation.passage.provenance
    algerian_bonus = 1 if (policy.prefer_algerian and provenance.authority.is_algerian_official) else 0
    recency = provenance.collected_at.toordinal() if policy.prefer_recent_on_tie else 0
    return (algerian_bonus, int(provenance.authority), recency)


def arbitrate(claims: list[Claim], policy: ConflictPolicy | None = None) -> Claim:
    """Pick the claim the system will display, per the golden rule."""
    policy = policy or ConflictPolicy()
    usable = [c for c in claims if c.authority > Authority.DISCARDED]
    if not usable:
        raise ValueError("No usable claim: every source for this field was discarded.")
    return max(usable, key=lambda c: _sort_key(c, policy))


def detect(claims: list[Claim], policy: ConflictPolicy | None = None) -> list[Conflict]:
    """Find every (drug, field) where the sources do not agree.

    Args:
        claims: All claims extracted from the corpus.
        policy: Arbitration rules; the default follows the project's spec.

    Returns:
        One :class:`Conflict` per disagreeing field, with the retained claim and
        the divergent ones. Fields where every source agrees are not returned.
    """
    policy = policy or ConflictPolicy()
    conflicts: list[Conflict] = []

    for (drug_id, field_name), group in group_claims(claims).items():
        distinct_values = {_normalise(c.value) for c in group}
        if len(distinct_values) < 2:
            continue
        retained = arbitrate(group, policy)
        divergent = [
            c for c in group
            if _normalise(c.value) != _normalise(retained.value)
        ]
        conflicts.append(
            Conflict(
                drug_id=drug_id,
                field_name=field_name,
                retained=retained,
                divergent=divergent,
            )
        )

    return conflicts
