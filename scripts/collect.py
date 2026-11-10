"""Fetch the corpus, one source at a time, and record where each file came from.

Every fetch goes through the source registry, which refuses sources that forbid
automated collection. Re-running is safe: a document already on disk with the
same checksum is skipped rather than duplicated.

Usage:
    python scripts/collect.py --dry-run
    python scripts/collect.py --source anpp_rcp
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pharmeazor.collect.registry import (  # noqa: E402
    CollectionNotPermitted,
    SourceRegistry,
    assert_collectable,
)
from pharmeazor.config import settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect the Pharmeazor corpus.")
    parser.add_argument("--source", help="Collect a single source by id.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be collected and stop.")
    args = parser.parse_args()

    settings.ensure_dirs()
    registry = SourceRegistry.load()
    specs = [registry[args.source]] if args.source else list(registry.by_authority())

    print(f"{len(specs)} source(s) declarees\n")
    permitted = []
    for spec in specs:
        try:
            assert_collectable(spec)
        except CollectionNotPermitted as exc:
            print(f"  SKIP  {spec.source_id:<16} {exc}")
            continue
        permitted.append(spec)
        print(f"  OK    {spec.source_id:<16} {spec.describe()}")

    if args.dry_run or not permitted:
        print("\nRien n'a ete telecharge.")
        if not permitted:
            print("Aucune source n'autorise encore la collecte automatique.")
            print("Consignez robots.txt et les CGU dans docs/DATA_SOURCES.md,")
            print("puis passez `access: automated` dans le registre.")
        return 0

    # TODO (semaine 1-2): per-source fetchers writing into data/raw/<source_id>/
    # with a provenance sidecar (url, collected_at, language, authority, checksum).
    raise NotImplementedError("Fetchers par source : a implementer (semaine 1-2).")


if __name__ == "__main__":
    raise SystemExit(main())
