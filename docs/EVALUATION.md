# Évaluation

Le projet est noté sur des chiffres, pas sur des impressions. Chaque choix technique
garde ici sa trace : méthode, échantillon, résultat avant et après.

## Jeu de test

[`eval/questions.yaml`](../eval/questions.yaml) — objectif : **au moins 30 questions**,
chacune avec sa réponse attendue et son passage de référence. Rejouable en une commande :

```bash
python scripts/run_eval.py
```

Répartition visée :

| Niveau | Description | Nombre |
|---|---|---|
| 1 — directe | la réponse est dans un seul document | ~10 |
| 2 — croisée | la réponse demande plusieurs sources | ~10 |
| 3 — contexte patient | précautions pour un profil donné | ~5 |
| piège | le système doit signaler, pas deviner | ~3 |
| hors périmètre | le système doit refuser | ~2 |

## Mesures

### Exactitude des citations

Le passage cité contient-il réellement l'information avancée ? Vérifié à la main sur
l'ensemble du jeu de test.

| Date | Version | Citations correctes | Note |
|---|---|---|---|
| *à remplir* | | | |

### Recherche — BM25 contre vecteurs sémantiques

Rappel @k sur le jeu de test. Le retriever dense ne remplace BM25 que s'il le bat ici.

| Méthode | Rappel @1 | Rappel @5 | Rappel @10 | Latence médiane |
|---|---|---|---|---|
| BM25 | | | | |
| Vecteurs (E5 / BGE-M3) | | | | |
| Hybride | | | | |

### Couverture des rubriques

Part des rubriques correctement retrouvées, sur **20 notices vérifiées à la main**.

| Rubrique | Taux | Erreurs fréquentes |
|---|---|---|
| Indications | | |
| Contre-indications | | |
| Posologie | | |
| Interactions | | |

### Normalisation des noms

Sur **au moins 40 noms** saisis de différentes manières (marque, DCI, faute de frappe,
variante d'écriture).

| Type de saisie | Nombre | Résolus | Ambiguïtés signalées | Erreurs |
|---|---|---|---|---|
| Nom commercial exact | | | | |
| DCI | | | | |
| Faute de frappe | | | | |
| Noms proches (piège) | | | | |

Une ambiguïté correctement signalée compte comme une réussite, pas comme un échec.

### Réconciliation

Objectif : **au moins 10 désaccords réels** repérés et annotés par l'équipe.

| # | Médicament | Champ | Source A | Source B | Retenue | Correct ? |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

### Contrôle des chiffres

| Date | Chiffres avancés | Vérifiés | Bloqués | Faux positifs du garde |
|---|---|---|---|---|
| *à remplir* | | | | |

Un faux positif — un chiffre correct bloqué à tort — est un vrai défaut : il est corrigé
dans `number_guard.py` et un test est ajouté pour qu'il ne revienne pas.

### Refus

| Questions hors périmètre | Refusées correctement | Taux |
|---|---|---|
| | | |

### Coût

| Date | Appels au modèle | Dont servis par le cache | Durée du run |
|---|---|---|---|
| *à remplir* | | | |

## Protocole

1. Toute modification qui touche la chaîne est suivie d'un run complet.
2. Le tableau avant/après est reporté dans la pull request (voir le gabarit).
3. Un résultat non reproductible depuis le cache n'est pas un résultat.
4. Les échantillons annotés à la main sont versionnés avec le code, pas refaits à chaque
   run : sinon les chiffres de deux semaines différentes ne sont pas comparables.
