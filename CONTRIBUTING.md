# Contribuer

Équipe de 4 à 5 personnes sur un dépôt partagé. Ces conventions existent pour qu'on
puisse travailler en parallèle sans se marcher dessus.

## Branches

```
main         toujours vert : les tests passent, la démo tourne
develop      intégration
feat/<nom>   une brique, une branche
fix/<nom>    correction
```

Rien ne part directement sur `main`. Tout passe par une pull request.

## Commits

Format court et lisible :

```
<type>(<brique>): <ce que ça change>
```

Exemples :

```
collect(sources): ajoute le registre de conformité robots.txt
fix(guard): accepte "24 heures" comme équivalent de "24 h"
eval(retrieval): compare BM25 et E5 sur les 30 questions
```

Types : `feat`, `fix`, `docs`, `test`, `refactor`, `eval`, `chore`.

## Avant d'ouvrir une pull request

```bash
pytest
```

```bash
ruff check src tests
```

Et vérifier :

- aucune clé d'API, aucune donnée personnelle, aucune vraie ordonnance dans le diff ;
- toute source nouvelle est déclarée dans `data/reference/source_registry.yaml` avec son
  relevé robots.txt / CGU ;
- si le changement touche la chaîne, le tableau avant/après est dans la PR.

## Règles non négociables

Ce sont les règles du cahier des charges. Une PR qui les enfreint est refusée, même si
elle améliore un chiffre :

1. Rien n'est affiché sans source.
2. Un chiffre absent du passage cité est bloqué, jamais affiché comme un fait.
3. Un niveau d'interaction n'est jamais adouci. « Aucune interaction trouvée » n'est pas
   « sans risque ».
4. Une ambiguïté est signalée, jamais tranchée en silence.
5. Une source de rang inférieur n'est jamais préférée sans le dire.
6. Le système ne prescrit ni ne diagnostique.

## Tests

Tout correctif de bug arrive avec le test qui l'aurait attrapé. Les modules du coeur
(`number_guard`, `names`, `conflicts`, `sections`, `bm25`) sont testés sans dépendance
externe : la suite doit tourner sur une machine nue, avec seulement pytest installé.

## Secrets

`.env` est ignoré par git et doit le rester. Chaque membre crée sa propre clé gratuite
dans Google AI Studio. Une clé qui finit dans un commit est révoquée immédiatement, même
si le commit est réécrit ensuite — l'historique a déjà été poussé.

## Répartition du travail

Les six briques sont volontairement découplées. Deux personnes peuvent travailler en
même temps sur l'extraction et sur la normalisation sans conflit de fichiers : elles
communiquent par les types de `schemas.py`, qui changent rarement et se discutent avant.
