# Architecture

Ce document explique les choix techniques et, surtout, **pourquoi** ils ont été faits.
Il est mis à jour quand une décision change, pas à la fin du projet.

## Principe directeur

Le socle est un RAG (génération augmentée par la recherche). Mais le RAG n'est qu'un
outil : ce qui fait la qualité du système, c'est la **base de connaissances** construite
en amont et la **vérification** appliquée en aval. Le modèle génératif ne rédige qu'à
partir des passages retrouvés, et il n'a pas le droit d'avancer un chiffre que le
contrôle déterministe ne retrouve pas dans ces passages.

Conséquence d'architecture : la génération est la couche la plus mince du système.

## Les couches

### 1. Collecte — `collect/`

Chaque source est déclarée dans `data/reference/source_registry.yaml` avec son rang
d'autorité, son mode d'accès et son relevé de conformité (`robots.txt`, CGU, date de
lecture). `assert_collectable()` refuse la collecte automatique tant que ce relevé est
vide. Ce n'est pas une politesse : une source qui interdit l'automatisation est utilisée
manuellement ou écartée, jamais contournée.

Chaque document téléchargé est accompagné d'une fiche `Provenance` : source, URL,
autorité, date de collecte, langue, pays, empreinte. La collecte est **rejouable** : un
document déjà présent avec la même empreinte est ignoré, pas dupliqué.

### 2. Extraction — `extract/`

Les notices ne sont pas structurées de la même façon deux fois. `sections.py` reconnaît
un titre de rubrique quelle que soit sa formulation : `4.3. Contre-indications` (style
RCP) et `Ne prenez jamais ce médicament` (style notice patient) tombent dans la même
rubrique canonique.

Décision : **un titre non reconnu n'est pas deviné**. Il va dans `unmapped`, pour revue
manuelle. Une rubrique mal étiquetée est pire qu'une rubrique non étiquetée, parce
qu'elle produit ensuite une citation fausse.

Les phrases d'origine sont conservées telles quelles. Sans cela, aucune citation exacte
n'est possible.

### 3. Normalisation — `normalize/`

Un produit s'écrit de plusieurs façons : nom commercial, DCI, code ATC, variantes,
fautes de frappe. `NameResolver` combine distance d'édition (Levenshtein) et similarité
par trigrammes de caractères — la première gère les lettres manquantes, la seconde les
transpositions.

Décision : quand les deux meilleurs candidats sont séparés de moins de `margin`, la
fonction renvoie une `Ambiguity` et non un `Match`. Deux médicaments aux noms proches,
c'est précisément le piège du jeu de test ; y répondre par un choix silencieux est une
faute, pas une approximation.

### 4. Recherche — `retrieve/`

`bm25.py` est une implémentation compacte et sans dépendance, présente dès le départ
pour servir de **référence mesurable**. L'index vectoriel n'est pas adopté sur la foi de
sa réputation : il doit battre BM25 sur le jeu de test, chiffres à l'appui.

Attendu : la recherche par mots-clés rate les reformulations, la recherche par sens
confond parfois deux médicaments proches. Le résultat probable est une combinaison des
deux, mais c'est la mesure qui tranche.

### 5. Réconciliation — `reconcile/`

`detect()` groupe les affirmations par (médicament, champ) et signale tout groupe où les
valeurs diffèrent. `arbitrate()` applique la règle d'or : le rang supérieur l'emporte.

Deux raffinements inscrits dans `ConflictPolicy` :

- `prefer_algerian` — une source étrangère institutionnelle ne prime pas sur une source
  officielle algérienne, car chaque autorité valide son propre texte ;
- `prefer_recent_on_tie` — à rang égal, la collecte la plus récente l'emporte, puisqu'une
  notice est mise à jour après de nouvelles études.

La source écartée reste affichée, avec son passage et sa date. Le système explique
pourquoi elle perd ; il ne la supprime pas.

### 6. Réponse et vérification — `answer/`

Format imposé : réponse courte, explication simple, sources citées avec autorité et date
de collecte, niveau de confiance et limites.

`number_guard.py` extrait chaque nombre et son unité de la réponse rédigée, les
normalise (virgule décimale, espaces insécables, `24 h` / `24 heures` / `24h`), puis les
cherche dans les passages réellement cités. Un chiffre introuvable est **bloqué**.

Décision assumée : le garde ne convertit pas les unités. Décider que `4 g` et `4000 mg`
sont la même chose est un raisonnement clinique que le système n'a pas le droit de faire
seul. Il préfère bloquer et signaler.

## Ce qui n'est pas fait, et pourquoi

- **Pas de système multi-agents.** Le cahier des charges ne le demande pas. Un
  enchaînement de fonctions avec quelques outils appelés par le modèle suffit, et se
  mesure plus facilement. Une équipe qui veut des agents doit démontrer un gain chiffré.
- **Pas d'appel modèle dans le contrôle des chiffres.** Un contrôle qui peut halluciner
  ne contrôle rien.
- **Pas de réponse par défaut.** Si le corpus n'est pas indexé, l'API répond `503` avec
  la marche à suivre. Une démo qui invente une réponse vraisemblable trahit le projet.

## Contraintes du module

- Modèle génératif **imposé**, identique pour toutes les équipes, gratuit via Google AI
  Studio. Pas de facturation, pas d'abonnement, pas d'autre modèle dans le système rendu.
- Une clé gratuite **par personne**. Multiplier les comptes pour contourner les quotas
  créerait une inégalité entre équipes.
- Les appels sont mis en cache ; le jeu de test doit être rejouable depuis ce cache, et
  le nombre d'appels utilisés figure dans le rapport.
- Seuls des textes publics sont envoyés au modèle. Jamais de données personnelles, jamais
  une vraie ordonnance.
