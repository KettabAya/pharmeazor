"""Build the week-1 deliverables from the extracted nomenclature.

Produces, from ``data/reference/drugs_semaine1.csv``:

* ``data/reference/name_index.csv``        — every written form -> a product
* ``data/reference/equivalents_semaine1.csv`` — interchangeable boxes
* a worked answer, with its citations, printed at the end

Usage::

    python scripts/build_week1.py
    python scripts/build_week1.py --question ZYTREX
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmeazor.normalize.catalogue import Catalogue  # noqa: E402

SOURCE = ROOT / "data" / "reference" / "drugs_semaine1.csv"
NAME_INDEX = ROOT / "data" / "reference" / "name_index.csv"
EQUIVALENTS = ROOT / "data" / "reference" / "equivalents_semaine1.csv"


def write_name_index(catalogue: Catalogue) -> int:
    aliases = catalogue.aliases()
    with open(NAME_INDEX, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["alias", "alias_normalized", "kind", "drug_id", "inn"])
        for a in sorted(aliases, key=lambda x: (x.kind, x.alias)):
            product = catalogue.get(a.drug_id)
            writer.writerow([a.alias, a.alias_normalized, a.kind, a.drug_id,
                             product.inn if product else ""])
    return len(aliases)


def write_equivalents(catalogue: Catalogue) -> int:
    groups = [g for g in catalogue.groups() if g.size > 1]
    with open(EQUIVALENTS, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "group_id", "inn", "strength", "form_family", "group_size",
            "drug_id", "brand_name", "form", "packaging", "lab_name",
            "registration_no", "status",
        ])
        for i, group in enumerate(groups, 1):
            for p in group.products:
                writer.writerow([
                    f"EQ-{i:04d}", group.inn, group.strength, group.form_family,
                    group.size, p.drug_id, p.brand_name, p.form,
                    p.packaging.raw, p.lab_name, p.registration_no, p.status,
                ])
    return len(groups)


def pick_demo(catalogue: Catalogue, requested: str | None) -> str | None:
    """A brand that resolves to exactly one presentation, for the worked example."""
    if requested:
        return requested
    for group in catalogue.groups():
        for product in group.products:
            if not catalogue.equivalents_of(product.brand_name)["refused"]:
                return product.brand_name
    return None


def show_answer(catalogue: Catalogue, name: str) -> None:
    answer = catalogue.equivalents_of(name)
    print("\n" + "=" * 74)
    print(f"QUESTION : « {name} est en rupture, quels équivalents enregistrés ? »")
    print("=" * 74)

    if answer["refused"]:
        print(f"\nRÉPONSE   : {answer['short']}")
        print(f"LIMITES   : {answer['limits']}")
        print("\n(Le système refuse plutôt que de deviner — c'est le comportement attendu.)")
        return

    print(f"\nRÉPONSE   : {answer['short']}")
    print(f"\nEXPLICATION : {answer['explanation']}")
    print(f"\nSOURCES CITÉES ({len(answer['citations'])}) :")
    print(f"  {answer['citations'][0]['source']}")
    for c in answer["citations"]:
        print(f"    [{c['registration_no']}] {c['quote']}")
    print(f"\nLIMITES   : {answer['limits']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Construit les livrables de la semaine 1.")
    parser.add_argument("--question", help="Nom de marque pour l'exemple travaillé.")
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"Fichier source introuvable : {SOURCE}")
        return 1

    catalogue = Catalogue.from_csv(SOURCE)
    products = catalogue.products

    print(f"Catalogue : {len(products)} produits")
    for klass in sorted({p.therapeutic_class for p in products}):
        n = sum(1 for p in products if p.therapeutic_class == klass)
        inns = len({p.inn for p in products if p.therapeutic_class == klass})
        print(f"  {klass:<20} {n:>4} produits, {inns:>3} DCI")

    unparsed = [p for p in products if not p.strength.parsed]
    print(f"\nDosages lus      : {len(products) - len(unparsed)}/{len(products)}")
    if unparsed:
        print(f"  non lus ({len(unparsed)}) : {[p.strength.raw for p in unparsed][:6]}")

    n_aliases = write_name_index(catalogue)
    print(f"\nDictionnaire des noms : {n_aliases} entrées -> {NAME_INDEX.name}")

    n_groups = write_equivalents(catalogue)
    grouped = sum(g.size for g in catalogue.groups() if g.size > 1)
    print(f"Groupes d'équivalents : {n_groups} groupes, {grouped} produits -> {EQUIVALENTS.name}")

    print("\nLes 5 plus grands groupes :")
    for g in catalogue.groups()[:5]:
        print(f"  {g.size:>3} produits   {g.inn[:34]:<34} {g.strength:<14} {g.form_family}")

    demo = pick_demo(catalogue, args.question)
    if demo:
        show_answer(catalogue, demo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
