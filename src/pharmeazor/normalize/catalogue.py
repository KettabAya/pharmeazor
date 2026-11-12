"""The product catalogue built from the official nomenclature.

Turns the extracted CSV into three things the project needs:

* a **name dictionary** — every way of writing a product (brand name, INN, code,
  registration number) pointing at one product;
* **equivalence groups** — which boxes may replace which, by the rule the spec
  gives: same substance, same strength, same form;
* **answers with provenance** — every result carries the source version and the
  registration numbers it rests on, so nothing is displayed without its origin.

The catalogue answers *what exists*. It says nothing about indications,
posology or interactions: those live in the leaflets, not in the registry, and
claiming otherwise would be inventing.
"""

from __future__ import annotations

import csv
import datetime as _dt
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..schemas import Authority, Provenance
from .dosage import Packaging, Strength, parse_packaging, parse_strength
from .names import DrugEntry, normalize

__all__ = [
    "Product",
    "AliasKind",
    "NameAlias",
    "EquivalenceGroup",
    "Catalogue",
    "form_family",
]

# Galenic families. Two products are only interchangeable within one of these:
# a tablet does not replace a syrup, whatever the molecule.
_FORM_FAMILIES: tuple[str, ...] = (
    "COMPRIME", "GELULE", "CAPSULE", "SIROP", "SUSPENSION", "SOLUTION",
    "POUDRE", "GRANULE", "SACHET", "SUPPOSITOIRE", "OVULE", "CREME",
    "POMMADE", "GEL", "COLLYRE", "SPRAY", "AEROSOL", "PATCH", "AMPOULE",
    "INJECTABLE", "PERFUSION", "GOUTTES", "SIROP",
)


def form_family(form: str | None) -> str:
    """Reduce a FORME cell to its galenic family.

    ``COMPRIME PELLICULE SECABLE`` and ``COMPRIME`` are both ``COMPRIME``: the
    coating and the score line do not change what the product is. The full text
    is kept on the product so a pharmacist can still see the difference.

    >>> form_family("COMPRIME PELLICULE SECABLE")
    'COMPRIME'
    >>> form_family("POUDRE POUR SUSPENSSION BUVABLE")
    'POUDRE'
    """
    text = (form or "").upper()
    for family in _FORM_FAMILIES:
        if family in text:
            return family
    return text.split()[0] if text.split() else ""


class AliasKind:
    """Where a written name came from."""

    BRAND = "brand"
    INN = "inn"
    CODE = "code"
    REGISTRATION = "registration"


@dataclass(frozen=True)
class NameAlias:
    """One way of writing a product, pointing at that product."""

    alias: str
    alias_normalized: str
    kind: str
    drug_id: str


@dataclass
class Product:
    """One registered presentation — one box on a shelf."""

    drug_id: str
    therapeutic_class: str
    inn: str
    brand_name: str
    code: str
    registration_no: str
    form: str
    strength: Strength
    packaging: Packaging
    lab_name: str
    lab_country: str
    date_initial: str
    date_final: str
    status: str
    source_version: str

    @property
    def form_family(self) -> str:
        return form_family(self.form)

    @property
    def equivalence_key(self) -> tuple[str, str, str]:
        """Same substance, same strength, same galenic family."""
        return (normalize(self.inn), self.strength.canonical(), self.form_family)

    def label(self) -> str:
        return f"{self.brand_name} {self.strength} {self.form}".strip()

    def provenance(self, collected_at: _dt.date | None = None) -> Provenance:
        """Where this row came from. Required before anything is displayed."""
        year, _, month = self.source_version.partition("-")
        return Provenance(
            source_id=f"nomenclature_{self.source_version}",
            url="https://www.mip.gov.dz/",
            authority=Authority.NOMENCLATURE,
            collected_at=collected_at or _dt.date(int(year), int(month), 1),
            language="fr",
            country="DZ",
        )


@dataclass
class EquivalenceGroup:
    """Products the registry says are interchangeable."""

    inn: str
    strength: str
    form_family: str
    products: list[Product] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.products)

    def others_than(self, drug_id: str) -> list[Product]:
        return [p for p in self.products if p.drug_id != drug_id]

    def distinct_forms(self) -> list[str]:
        """The full forms inside the family — the pharmacist decides on these."""
        return sorted({p.form for p in self.products})


@dataclass
class Catalogue:
    """All products, plus the indexes built over them."""

    products: list[Product]

    _by_id: dict[str, Product] = field(default_factory=dict, repr=False)
    _by_alias: dict[str, list[Product]] = field(default_factory=dict, repr=False)
    _groups: dict[tuple[str, str, str], EquivalenceGroup] = field(
        default_factory=dict, repr=False
    )

    # ---------------------------------------------------------------- loading

    @classmethod
    def from_csv(cls, path: str | Path) -> Catalogue:
        """Load the extracted nomenclature CSV."""
        products: list[Product] = []
        with open(path, encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                products.append(
                    Product(
                        drug_id=row["drug_id"],
                        therapeutic_class=row["therapeutic_class"],
                        inn=row["inn"].strip(),
                        brand_name=row["brand_name"].strip(),
                        code=row["code"].strip(),
                        registration_no=row["registration_no"].strip(),
                        form=row["form"].strip(),
                        strength=parse_strength(row["strength_raw"]),
                        packaging=parse_packaging(row["packaging_raw"]),
                        lab_name=row["lab_name"].strip(),
                        lab_country=row["lab_country"].strip(),
                        date_initial=row["date_initial"].strip(),
                        date_final=row["date_final"].strip(),
                        status=row["status"].strip(),
                        source_version=row["source_version"].strip(),
                    )
                )
        return cls(products=products).build()

    def build(self) -> Catalogue:
        """Index by id, by alias, and by equivalence key."""
        self._by_id = {p.drug_id: p for p in self.products}

        by_alias: dict[str, list[Product]] = defaultdict(list)
        for alias in self.aliases():
            by_alias[alias.alias_normalized].append(self._by_id[alias.drug_id])
        self._by_alias = dict(by_alias)

        groups: dict[tuple[str, str, str], EquivalenceGroup] = {}
        for product in self.products:
            if not product.strength.parsed:
                continue  # no reliable strength -> never claim equivalence
            key = product.equivalence_key
            group = groups.get(key)
            if group is None:
                group = EquivalenceGroup(
                    inn=product.inn,
                    strength=product.strength.canonical(),
                    form_family=product.form_family,
                )
                groups[key] = group
            group.products.append(product)
        self._groups = groups
        return self

    # ---------------------------------------------------------------- indexes

    def aliases(self) -> list[NameAlias]:
        """Every written form that should resolve to a product."""
        out: list[NameAlias] = []
        seen: set[tuple[str, str]] = set()
        for product in self.products:
            candidates = (
                (product.brand_name, AliasKind.BRAND),
                (product.inn, AliasKind.INN),
                (product.code, AliasKind.CODE),
                (product.registration_no, AliasKind.REGISTRATION),
            )
            for raw, kind in candidates:
                if not raw:
                    continue
                key = (raw.upper(), product.drug_id)
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    NameAlias(
                        alias=raw,
                        alias_normalized=normalize(raw) or raw.upper(),
                        kind=kind,
                        drug_id=product.drug_id,
                    )
                )
        return out

    def drug_entries(self) -> list[DrugEntry]:
        """Feed :class:`~pharmeazor.normalize.names.NameResolver`.

        One entry per product, so a brand that exists in several strengths stays
        several entries — collapsing them would hide a real difference.
        """
        return [
            DrugEntry(
                drug_id=p.drug_id,
                inn=p.inn,
                brand_names=(p.brand_name,) if p.brand_name else (),
                atc_code=p.code,
                strength=p.strength.canonical() or p.strength.raw,
                form=p.form_family,
            )
            for p in self.products
        ]

    # ---------------------------------------------------------------- queries

    def get(self, drug_id: str) -> Product | None:
        return self._by_id.get(drug_id)

    def find_by_name(self, name: str) -> list[Product]:
        """Exact lookup after normalisation. Fuzzy matching is NameResolver's job."""
        return list(self._by_alias.get(normalize(name) or name.upper(), []))

    def groups(self) -> list[EquivalenceGroup]:
        return sorted(self._groups.values(), key=lambda g: (-g.size, g.inn))

    def group_for(self, product: Product) -> EquivalenceGroup | None:
        return self._groups.get(product.equivalence_key)

    def equivalents_of(self, name: str) -> dict:
        """Answer "X is out of stock, what can replace it?" — with its source.

        Returns a dict in the project's imposed answer shape. When the name is
        unknown or ambiguous the answer refuses rather than guessing, which is
        the behaviour the evaluation set tests for.
        """
        matches = self.find_by_name(name)
        if not matches:
            return {
                "found": False,
                "refused": True,
                "short": f"« {name} » est introuvable dans la nomenclature.",
                "limits": "Vérifiez l'orthographe ou saisissez la DCI.",
                "citations": [],
            }

        distinct = {m.equivalence_key for m in matches}
        if len(distinct) > 1:
            labels = sorted({m.label() for m in matches})
            return {
                "found": True,
                "refused": True,
                "short": f"« {name} » désigne plusieurs présentations.",
                "limits": "Précisez le dosage ou la forme : " + " · ".join(labels[:6]),
                "citations": [],
            }

        product = matches[0]
        group = self.group_for(product)
        others = group.others_than(product.drug_id) if group else []
        provenance = product.provenance()

        return {
            "found": True,
            "refused": False,
            "product": product,
            "equivalents": others,
            "short": (
                f"{len(others)} équivalent(s) enregistré(s) en Algérie pour "
                f"{product.brand_name} ({product.strength}, {product.form_family.lower()})."
                if others else
                f"Aucun équivalent enregistré pour {product.brand_name} "
                f"({product.strength}, {product.form_family.lower()}) dans cette version."
            ),
            "explanation": (
                "Même dénomination commune internationale, même dosage et même "
                "famille galénique, d'après la nomenclature nationale. Les formes "
                "exactes peuvent différer : la décision reste celle du pharmacien."
            ),
            "limits": (
                "La nomenclature indique ce qui est enregistré, pas la posologie "
                "ni les contre-indications : celles-ci doivent être lues dans le RCP."
            ),
            "citations": [
                {
                    "source": provenance.cite(),
                    "registration_no": p.registration_no,
                    "quote": (
                        f"{p.brand_name} | {p.inn} | {p.form} | {p.strength.raw} | "
                        f"{p.packaging.raw} | {p.lab_name}"
                    ),
                }
                for p in [product, *others]
            ],
        }
