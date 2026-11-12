# Plan de traitement des données — nomenclature

Plan de travail pour **deux personnes**, sur les fichiers Excel de la nomenclature
nationale. Chaque tâche indique ce qu'il faut faire, le fichier à créer, et
**comment savoir qu'elle est terminée**.

Vocabulaire : « A » = Aya, « B » = le binôme. Changez les prénoms si besoin.

---

## Ce qu'on a comme données

10 fichiers Excel, tous la même table officielle :

| Groupe | Fichiers | Taille |
|---|---|---|
| Versions de la nomenclature | Déc 2025, Fév 2026, Avr 2026, Juin 2026, Août 2026 | ~5 300 lignes, 3 feuilles chacun |
| Fichiers par année | 2021, 2022, 2023, 2024, 2025 | ~330 lignes chacun |

Les 19 colonnes :

```
N° · N°ENREGISTREMENT · CODE · DENOMINATION COMMUNE INTERNATIONALE ·
NOM DE MARQUE · FORME · DOSAGE · CONDITIONNEMENT · LISTE · P1 · P2 · OBS ·
LABORATOIRE DETENTEUR · PAYS DU LABORATOIRE · DATE D'ENREGISTREMENT INITIAL ·
DATE D'ENREGISTREMENT FINAL · TYPE · STATUT · DUREE DE STABILITE
```

Les trois feuilles de chaque version : `Nomenclature`, `Non Renouvelés`, `Retraits`.

**Au total, environ 50 000 lignes à traiter.**

### Trois pièges à connaître avant d'écrire une ligne de code

1. **L'en-tête n'est pas sur la ligne 1.** Il y a d'abord l'en-tête officiel du
   ministère. Les vrais titres de colonnes sont sur la **ligne 14** dans les
   versions de la nomenclature, mais sur la **ligne 11** dans les fichiers par
   année. Ne codez pas le numéro en dur : cherchez la première ligne qui contient
   au moins 15 cellules non vides.
2. **La feuille `Retraits` n'a pas les mêmes colonnes.** Pas de `OBS`, mais deux
   colonnes en plus : `DATE DE RETRAIT` et `MOTIF DE RETRAIT`. Si on lit cette
   feuille avec les positions de la feuille principale, les laboratoires se
   retrouvent dans le mauvais champ **sans aucune erreur affichée**.
3. **Fermez Excel avant de lancer un script.** Un fichier ouvert crée un fichier
   fantôme `~$NOM-DU-FICHIER.xlsx` et bloque la lecture.

---

## Étape 0 — à faire ensemble, une seule fois (~1 h)

Tant que ce n'est pas fait, ne commencez pas à coder chacun de votre côté.

### 0.1 — Chacun installe le projet

```bash
git clone https://github.com/KettabAya/pharmeazor.git
cd pharmeazor
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pip install openpyxl
pytest
```

**Terminé quand :** `pytest` affiche `55 passed` chez chacun des deux.

### 0.2 — Ranger les fichiers Excel

Créez le dossier `data/raw/nomenclature/` et copiez-y les 10 fichiers. Renommez-les
pour qu'ils soient triables, sans accent ni espace :

```
nomenclature_2025-12.xlsx
nomenclature_2026-02.xlsx
nomenclature_2026-04.xlsx
nomenclature_2026-06.xlsx
nomenclature_2026-08.xlsx
annee_2021.xlsx … annee_2025.xlsx
```

Ce dossier est ignoré par git : les fichiers restent sur vos machines, on ne les
pousse pas. Partagez-les entre vous par clé USB ou Drive.

**Terminé quand :** les deux ont les 10 fichiers, avec exactement les mêmes noms.

### 0.3 — Se mettre d'accord sur le format de sortie

C'est le contrat entre A et B. Une fois écrit, chacun travaille sans attendre
l'autre. Ajoutez dans `src/pharmeazor/schemas.py` :

| Champ | Vient de | Type |
|---|---|---|
| `registration_no` | N°ENREGISTREMENT | texte |
| `code` | CODE | texte |
| `inn` | DCI | texte |
| `brand_name` | NOM DE MARQUE | texte |
| `form` | FORME | texte |
| `strength_value` | DOSAGE (partie chiffre) | nombre |
| `strength_unit` | DOSAGE (partie unité) | texte |
| `packaging_count` | CONDITIONNEMENT (B/10 → 10) | nombre |
| `list_class` | LISTE | texte |
| `lab_name` | LABORATOIRE DETENTEUR | texte |
| `lab_country` | PAYS DU LABORATOIRE | texte |
| `date_initial` | DATE D'ENREGISTREMENT INITIAL | date ISO |
| `date_final` | DATE D'ENREGISTREMENT FINAL | date ISO |
| `type_code` | TYPE | texte |
| `status` | STATUT | texte |
| `withdrawal_date` | DATE DE RETRAIT (Retraits seulement) | date ISO ou vide |
| `withdrawal_reason` | MOTIF DE RETRAIT (Retraits seulement) | texte ou vide |
| `source_version` | nom du fichier → `2026-06` | texte |
| `source_sheet` | `nomenclature` / `non_renouveles` / `retraits` | texte |

**Terminé quand :** le tableau est dans `schemas.py`, commité, et les deux l'ont tiré.

---

## Partie A — Lecture et nettoyage *(Aya)*

Objectif : transformer 10 fichiers Excel en **une seule table propre**.

### A1 — Lire une feuille (~2 h)

Créer `src/pharmeazor/collect/nomenclature.py` avec une fonction qui ouvre un
fichier, trouve la ligne d'en-tête toute seule, et renvoie une liste de
dictionnaires.

La partie qui compte, la détection d'en-tête :

```python
def find_header_row(ws, max_scan=25):
    """Renvoie le numéro de la ligne des titres de colonnes."""
    for idx, row in enumerate(ws.iter_rows(max_row=max_scan, values_only=True), 1):
        filled = [c for c in row if c not in (None, "")]
        if len(filled) >= 15:
            return idx
    raise ValueError("En-tête introuvable dans les 25 premières lignes")
```

**Terminé quand :** sur `nomenclature_2026-06.xlsx`, la fonction renvoie 14, et sur
`annee_2023.xlsx` elle renvoie 11 — sans qu'on lui ait rien dit.

### A2 — Les trois feuilles (~2 h)

Même fichier. Lire les trois feuilles de chaque classeur, en traitant `Retraits`
séparément puisque ses colonnes diffèrent. Ne vous fiez **jamais** à la position
d'une colonne : construisez un dictionnaire `titre → position` à partir de la
ligne d'en-tête trouvée en A1, et lisez par titre.

**Terminé quand :** un test vérifie que pour la feuille `Retraits`, le champ
`lab_name` contient bien un nom de laboratoire et non une date.

### A3 — Échantillon pour débloquer B (~30 min) — **à faire avant A4**

Exporter les 100 premières lignes lues au format du contrat, dans
`tests/fixtures/nomenclature_sample.csv`, et le commiter.

**Terminé quand :** le fichier est sur GitHub et B peut commencer sans attendre la
suite. **C'est la tâche la plus importante de la semaine** : elle permet à B de
travailler en parallèle au lieu de vous attendre.

### A4 — Nettoyer les champs (~3 h)

| Champ | Avant | Après |
|---|---|---|
| `DOSAGE` | `"10MG"` | `strength_value=10`, `strength_unit="mg"` |
| `CONDITIONNEMENT` | `"B/10"` | `packaging_count=10` |
| dates | `2006-07-31 00:00:00` | `"2006-07-31"` |
| textes | `"  EL KENDI  "` | `"EL KENDI"` |

Attention : certains dosages sont composés (`"500MG/125MG"`). Ne les cassez pas de
force — gardez le texte original dans un champ `strength_raw` en plus, pour pouvoir
vérifier plus tard.

**Terminé quand :** `tests/test_nomenclature.py` couvre au moins 8 cas, dont un
dosage composé et une cellule vide, et `pytest` est vert.

### A5 — Tout écrire dans une base (~2 h)

Créer `scripts/build_nomenclature.py` qui lit les 10 fichiers et écrit
`data/processed/nomenclature.db` (SQLite, une seule table).

```bash
python scripts/build_nomenclature.py
```

**Terminé quand :** la commande affiche le nombre de lignes écrites (environ
**50 000**) et se relance sans créer de doublons.

**Livrable de la partie A :** `data/processed/nomenclature.db`, une table, toutes
les versions, chaque ligne sachant de quel fichier et de quelle feuille elle vient.

---

## Partie B — Exploitation *(le binôme)*

Objectif : transformer la table propre en ce dont le projet a besoin. Commencez sur
l'échantillon de A3 — n'attendez pas A5.

### B1 — Charger et compter (~1 h)

Créer `src/pharmeazor/normalize/nomenclature_index.py` : charger la table (ou
l'échantillon CSV) et afficher des compteurs — nombre de produits, de DCI
distinctes, de laboratoires, répartition par `STATUT`.

**Terminé quand :** vous pouvez dire combien de DCI distinctes existent. Si le
chiffre paraît absurde (3 DCI, ou 40 000), c'est que la lecture est cassée —
prévenez A tout de suite.

### B2 — Réduire aux trois classes (~2 h)

Le projet ne porte que sur **30 à 50 médicaments** : antalgiques et
anti-inflammatoires, antibiotiques courants, antihypertenseurs. Repérer comment la
colonne `CODE` encode la classe (`01 A 003` → les premiers caractères regroupent),
puis filtrer.

Écrire le résultat dans `data/reference/drugs.csv`.

**Terminé quand :** le fichier contient entre 30 et 50 lignes et que vous avez
vérifié **à la main** que chacune appartient bien à sa classe.

### B3 — Dictionnaire des noms (~3 h)

Construire `data/reference/name_index.csv` : une ligne par façon d'écrire un
produit — nom de marque, DCI, code — toutes pointant vers le même `drug_id`.

C'est ce fichier qui alimente le `NameResolver` déjà écrit dans
`src/pharmeazor/normalize/names.py`. Lisez-le avant de commencer : il attend des
objets `DrugEntry`, votre travail est de les produire.

**Terminé quand :** `NameResolver` chargé avec votre fichier retrouve la bonne
fiche à partir d'un nom de marque, d'une DCI, et d'une faute de frappe.

### B4 — Équivalents (~2 h)

Deux produits sont équivalents s'ils partagent DCI + dosage + forme. Grouper, et
écrire `data/processed/equivalents.csv`.

**Terminé quand :** pour un médicament au hasard, la liste d'équivalents produite
correspond à ce que vous lisez vous-même dans le fichier Excel.

### B5 — Comparaison des versions (~3 h)

On a 5 photos datées de la même liste, de décembre 2025 à août 2026. Comparer :
quels produits ont été **ajoutés**, **retirés**, **renouvelés** entre deux versions.

Écrire `data/processed/versions_diff.csv`.

**Terminé quand :** vous pouvez répondre « entre avril et juin 2026, X produits
ajoutés et Y retirés », avec les numéros d'enregistrement à l'appui.

C'est un **bonus direct** sur le cahier des charges : c'est l'extension « suivi des
versions », et ça nourrit la brique « réconciliation des sources ».

### B6 — Tableau d'évaluation (~2 h)

Le cahier des charges demande une évaluation chiffrée sur **au moins 40 noms**
saisis de différentes façons. Préparer le tableau dans `docs/EVALUATION.md` :
40 saisies (marques, DCI, fautes de frappe, noms proches), la fiche attendue pour
chacune, puis le résultat obtenu.

**Terminé quand :** le tableau a 40 lignes remplies et un pourcentage en bas.

---

## Étape finale — ensemble (~2 h)

1. `git merge` des deux branches dans `develop`, puis `pytest`
2. Lancer toute la chaîne depuis zéro sur une machine propre
3. Remplir les chiffres dans `docs/EVALUATION.md`
4. Pull request vers `main`

---

## Récapitulatif des livrables

| Fichier | Qui | Contenu |
|---|---|---|
| `data/processed/nomenclature.db` | A | ~50 000 lignes, toutes versions |
| `tests/fixtures/nomenclature_sample.csv` | A | 100 lignes, pour débloquer B |
| `src/pharmeazor/collect/nomenclature.py` | A | le lecteur |
| `scripts/build_nomenclature.py` | A | la commande qui construit tout |
| `data/reference/drugs.csv` | B | les 30–50 médicaments retenus |
| `data/reference/name_index.csv` | B | marque / DCI / code → fiche |
| `data/processed/equivalents.csv` | B | produits interchangeables |
| `data/processed/versions_diff.csv` | B | ajouts, retraits, renouvellements |
| `docs/EVALUATION.md` rempli | A + B | les chiffres du rapport |

---

## Organisation git

| | Branche | Dossiers touchés |
|---|---|---|
| A | `feat/nomenclature-ingest` | `collect/`, `extract/`, `scripts/` |
| B | `feat/nomenclature-entities` | `normalize/`, `reconcile/` |

Des dossiers différents : **aucun conflit de fusion possible**. Seul
`schemas.py` est commun — si l'un de vous doit le modifier, prévenez l'autre avant.

Commitez souvent, petit, avec un message clair. Relisez `CONTRIBUTING.md` pour le
format.

---

## Si vous bloquez

- **La lecture renvoie des colonnes décalées** → vous lisez par position au lieu
  de lire par titre. Revenez à A2.
- **`PermissionError` à l'ouverture d'un fichier** → il est ouvert dans Excel.
- **Des accents cassés (`DÃ©cembre`)** → un problème d'encodage à l'écriture :
  ajoutez `encoding="utf-8"` partout où vous écrivez un fichier.
- **Les deux chiffres ne concordent pas entre A et B** → c'est le contrat de
  l'étape 0.3 qui a dérivé. Reprenez-le ensemble avant de continuer.
