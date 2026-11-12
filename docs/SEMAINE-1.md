# Semaine 1 — trois médicaments, la chaîne complète

L'enseignant demande **trois médicaments** cette semaine, pas trente. L'objectif
n'est pas la quantité : c'est de faire fonctionner la chaîne **de bout en bout**
une fois. Passer de 3 à 50 ensuite, c'est changer une liste.

---

## Les trois médicaments

Un par classe thérapeutique, choisis dans la nomenclature de juin 2026 :

| DCI | Classe | Produits enregistrés | Marques distinctes |
|---|---|---|---|
| **PARACETAMOL** | antalgique / anti-inflammatoire | 143 | 89 |
| **AMOXICILLINE** | antibiotique | 61 | 31 |
| **AMLODIPINE** | antihypertenseur | 80 | 40 |

Pourquoi ceux-là : très courants, bien documentés, et chacun contient une
difficulté différente — associations (`500MG/30MG`, `1G/125MG`, `5MG/160MG`),
formes multiples, et une faute de frappe dans la source officielle
(`SUSPENSSION`) qui montrera que le nettoyage sert à quelque chose.

**À confirmer auprès de l'enseignant** avant de lancer la semaine : il a peut-être
sa propre liste.

---

## Ce qui est déjà fait

[`data/reference/drugs_semaine1.csv`](../data/reference/drugs_semaine1.csv) —
**284 lignes**, les trois DCI extraites de la nomenclature de juin 2026, avec
pour chaque produit : marque, code, n° d'enregistrement, forme, dosage,
conditionnement, laboratoire, pays, dates, statut.

Ne le refaites pas. **Vérifiez-le** : ouvrez-le, prenez 5 lignes au hasard,
retrouvez-les dans le fichier Excel d'origine. Si tout correspond, c'est votre
point de départ. Si quelque chose cloche, dites-le avant de construire dessus.

---

## Le résultat attendu en fin de semaine

Pour **chacun** des trois médicaments :

1. Des documents venant d'**au moins trois sources différentes, dont une
   officielle** — la nomenclature en est déjà une
2. Les **quatre rubriques** extraites : indications, contre-indications,
   posologie, interactions
3. Les **noms reliés** : marque → DCI → code, fautes de frappe comprises
4. Les **équivalents** : quelles boîtes remplacent quelle boîte

Et pour finir, **une seule question** répondue correctement avec sa citation
exacte. Une seule suffit. Par exemple :

> « ZYTREX est en rupture, quels équivalents enregistrés en Algérie ? »

---

## Répartition — A et B

Ne découpez pas « toi un médicament et demi, moi un et demi » : vous écririez le
même code deux fois. Découpez par **type de source**.

### A — la source structurée (le tableur)

> **État : A1 → A5 sont implémentées et testées.** Le code est dans
> `src/pharmeazor/normalize/dosage.py` et `catalogue.py`, les sorties dans
> `data/reference/`. Lancez `python scripts/build_week1.py` pour tout
> reconstruire. Il reste à **relire et comprendre** ce code : c'est vous qui le
> présenterez, et A1 — la vérification du CSV contre l'Excel — n'a pas été faite
> et ne peut pas l'être à votre place.

Vous partez du CSV déjà extrait.

| # | Tâche | Terminé quand |
|---|---|---|
| A1 | Vérifier le CSV contre l'Excel, sur 5 lignes au hasard | les 5 correspondent exactement |
| A2 | Séparer `strength_raw` en valeur + unité (`500MG` → `500` + `mg`), en gardant le texte d'origine | `500MG/30MG` n'est pas cassé en silence — il garde son texte brut |
| A3 | Séparer `packaging_raw` (`B/16` → `16`) | `B/FL 15 ML` ne plante pas, il reste vide plutôt que faux |
| A4 | Construire le dictionnaire des noms : une ligne par façon d'écrire un produit → `drug_id` | `NameResolver` retrouve `DOLI-BIEN`, `paracetamol` et `doliben` (faute) sur la bonne fiche |
| A5 | Grouper les équivalents : même DCI + même dosage + même forme | pour `ZYTREX`, la liste produite correspond à ce que vous lisez vous-même dans l'Excel |

**Livrables :** `data/reference/name_index.csv`, `data/processed/equivalents.csv`,
plus les tests dans `tests/`.

### B — les sources documentaires (les notices)

| # | Tâche | Terminé quand |
|---|---|---|
| B1 | Trouver, pour chacun des 3 médicaments, **2 documents** en plus de la nomenclature : une notice ou un RCP officiel, et une fiche d'un site professionnel | 6 documents enregistrés dans `data/raw/notices/` |
| B2 | Pour chaque document : noter sa provenance — adresse, date de collecte, langue, niveau d'autorité | un fichier `.json` à côté de chaque document, avec ces 4 champs |
| B3 | **Avant toute collecte automatique** : lire le `robots.txt` et les CGU de chaque site, les consigner dans `docs/DATA_SOURCES.md` | le tableau du fichier n'a plus de « à remplir » pour les sites utilisés |
| B4 | Convertir chaque document en texte | 6 fichiers `.txt` lisibles, accents compris |
| B5 | Découper en rubriques avec `split_sections()` (déjà écrit dans le dépôt) | sur les 6 documents, les 4 rubriques sont retrouvées — notez le score, même s'il est mauvais |

**Livrables :** `data/raw/notices/` avec ses fiches de provenance,
`docs/DATA_SOURCES.md` rempli, et le score de couverture des rubriques.

Si `split_sections()` rate des rubriques, **ne trichez pas en modifiant le test** :
notez le chiffre réel et ajoutez le motif manquant dans
`src/pharmeazor/extract/sections.py`. Le cahier des charges demande un taux mesuré,
pas un taux parfait.

---

## Déroulement de la semaine

| Jour | Qui | Quoi |
|---|---|---|
| 1 | ensemble | Installer le projet, lire ce fichier, confirmer les 3 médicaments avec l'enseignant |
| 2–3 | A et B en parallèle | A1→A3 · B1→B3 |
| 4 | A et B en parallèle | A4→A5 · B4→B5 |
| 5 | ensemble | Fusionner les branches, répondre à **une** question avec citation, commiter |

Branches : `feat/semaine1-nomenclature` pour A, `feat/semaine1-notices` pour B.
Dossiers différents, donc aucun conflit possible.

---

## Les trois règles à ne jamais enfreindre

Elles viennent du cahier des charges et elles sont déjà appliquées dans le code :

1. **Rien ne s'affiche sans source.** Une valeur sans son passage d'origine
   n'apparaît pas.
2. **Tout chiffre affiché doit se retrouver mot pour mot dans le passage cité.**
   C'est `number_guard.py` qui le vérifie, sans appeler aucun modèle.
3. **On ne devine pas.** Deux produits aux noms proches → on signale l'ambiguïté,
   on ne tranche pas tout seul.

---

## Ce qu'on ne fait PAS cette semaine

- les 30 à 50 médicaments — c'est plus tard, et ce sera une ligne à changer
- la comparaison BM25 / vecteurs
- les 30 questions du jeu de test — une seule suffit cette semaine
- l'interface — elle existe déjà comme maquette

Faire fonctionner trois médicaments complètement vaut mieux que cinquante à moitié.
