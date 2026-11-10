## What this changes

<!-- One or two sentences. Link the issue it closes. -->

Closes #

## Which brick of the chain

- [ ] 1. Collecte (sources + provenance)
- [ ] 2. Extraction des rubriques
- [ ] 3. Normalisation des noms
- [ ] 4. Reponse avec preuves
- [ ] 5. Reconciliation des sources
- [ ] 6. Interface / jeu de test
- [ ] Docs, CI, outillage

## Evidence

<!-- Numbers, not impressions. Before/after on the evaluation set where relevant. -->

| Metric | Before | After |
|---|---|---|
|  |  |  |

## Checklist

- [ ] `pytest` passes locally
- [ ] `ruff check src tests` is clean
- [ ] No API key, no personal data, no real prescription in the diff
- [ ] Any new source is declared in `data/reference/source_registry.yaml` with its robots.txt / terms record
- [ ] Nothing is displayed without a citation
