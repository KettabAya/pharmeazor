"""Turn the extracted sections into retrievable passages, then index them.

Writes data/processed/passages.jsonl, which is what the API checks for before
it will answer anything at all.

Usage:
    python scripts/build_index.py --retriever bm25
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pharmeazor.config import settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the retrieval index.")
    parser.add_argument("--retriever", choices=["bm25", "dense"], default=settings.retriever)
    args = parser.parse_args()

    settings.ensure_dirs()
    raw_files = list(settings.raw_dir.rglob("*"))
    documents = [p for p in raw_files if p.is_file() and p.suffix != ".json"]

    if not documents:
        print("data/raw/ est vide. Lancez d'abord `python scripts/collect.py`.")
        return 1

    print(f"{len(documents)} document(s) a traiter, retriever = {args.retriever}")

    # TODO (semaine 2-3):
    #   1. convertir chaque document en texte (PyMuPDF / pdfplumber / OCR)
    #   2. split_sections() pour decouper en rubriques
    #   3. chunker en passages de settings.passage_chars avec recouvrement
    #   4. ecrire data/processed/passages.jsonl (texte + provenance)
    #   5. construire l'index BM25 ou l'index vectoriel
    raise NotImplementedError("Pipeline d'indexation : a implementer (semaine 2-3).")


if __name__ == "__main__":
    raise SystemExit(main())
