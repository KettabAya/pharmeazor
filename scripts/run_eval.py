"""Replay the evaluation set and print the figures the report is graded on.

Results are cached so a run costs no model calls when nothing changed; the
number of calls actually used is reported, as the module requires.

Usage:
    python scripts/run_eval.py
    python scripts/run_eval.py --retriever dense --compare bm25
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pharmeazor.config import ROOT, settings  # noqa: E402

QUESTIONS = ROOT / "eval" / "questions.yaml"


def load_questions() -> list[dict]:
    import yaml

    data = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8")) or {}
    return data.get("questions", [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay the evaluation set.")
    parser.add_argument("--retriever", choices=["bm25", "dense"], default=settings.retriever)
    parser.add_argument("--compare", choices=["bm25", "dense"],
                        help="Run a second retriever and print both side by side.")
    args = parser.parse_args()

    questions = load_questions()
    todo = [q for q in questions if "TODO" in str(q.get("expected_answer", ""))]

    print(f"Jeu de test : {len(questions)} question(s)")
    print(f"  dont {len(todo)} encore a annoter")
    print(f"Objectif du cahier des charges : au moins 30 questions annotees\n")

    by_level: dict[str, int] = {}
    for q in questions:
        key = str(q.get("level"))
        by_level[key] = by_level.get(key, 0) + 1
    for level, count in sorted(by_level.items()):
        print(f"  niveau {level:<8} {count}")

    print(f"\nRetriever : {args.retriever}" + (f" vs {args.compare}" if args.compare else ""))

    # TODO (semaine 3-4): pour chaque question, lancer la chaine complete et mesurer
    #   - exactitude de la citation (le passage cite contient-il l'information ?)
    #   - rappel du retriever @k
    #   - taux de chiffres bloques par le number guard
    #   - taux de refus corrects sur les questions hors perimetre
    #   - nombre d'appels au modele (cache compris)
    raise NotImplementedError("Harnais d'evaluation : a implementer (semaine 3-4).")


if __name__ == "__main__":
    raise SystemExit(main())
