# Sources de données — registre et conformité

> **À remplir avant toute collecte automatique.** `assert_collectable()` refuse de
> télécharger depuis une source dont la ligne ci-dessous est incomplète. Le registre
> exécutable vit dans [`data/reference/source_registry.yaml`](../data/reference/source_registry.yaml) ;
> ce document en est la justification écrite, destinée au rapport.

## Comment remplir une ligne

1. Ouvrir `https://<domaine>/robots.txt` et lire ce qui est autorisé.
2. Lire les conditions générales d'utilisation du site.
3. Noter la date de lecture et la conclusion dans le tableau ci-dessous.
4. Reporter `access` et `robots_checked_on` dans le YAML.

Si une source interdit l'automatisation, elle est utilisée **manuellement** ou écartée.
Elle n'est jamais contournée.

## Registre

| Source | Rang | robots.txt lu le | Verdict | Conclusion |
|---|---|---|---|---|
| RCP et notices ANPP | 4 — officielle | *à remplir* | *à remplir* | source prioritaire |
| Nomenclature (Ministère de l'Industrie pharmaceutique) | 3 — officielle | *à remplir* | accès automatique interdit | téléchargement manuel |
| Thésaurus des interactions — ANSM | 2 — institutionnelle | *à remplir* | *à remplir* | complément, jamais substitut |
| DailyMed | 2 — institutionnelle | *à remplir* | *à remplir* | notice américaine, peut différer |
| EMA | 2 — institutionnelle | *à remplir* | *à remplir* | notice européenne, peut différer |
| Pharm'Net (e-Sahti) | 1 — secondaire | *à remplir* | *à remplir* | chiffres de 2017 |
| MEDAlgérie | 1 — secondaire | *à remplir* | *à remplir* | pas d'API mentionnée |
| dzair-pharma.net | 1 — secondaire | *à remplir* | *à remplir* | données à titre informatif |
| Forums, blogs, réseaux sociaux | 0 — écartée | — | — | hors corpus |

## Ce qui est gardé, ce qui est écarté

**Gardé** — RCP et notices officiels, nomenclature officielle, tableaux d'interactions
institutionnels, sites professionnels algériens (toujours signalés comme secondaires).

**Écarté** — prix, stocks, publicités, forums, blogs, compléments alimentaires,
dispositifs médicaux.

Un filtre décide si un contenu est pertinent ; il fait partie du travail et il est évalué
de façon chiffrée (voir [EVALUATION.md](EVALUATION.md)).

## Étiquette de collecte

- délai entre deux requêtes : `settings.request_delay_seconds` (2 s par défaut) ;
- `User-Agent` identifiant le projet : `settings.user_agent` ;
- aucune tentative de contourner une limitation de débit ou une protection anti-robot ;
- collecte rejouable : une empreinte par document, pas de doublon.

## Fraîcheur

Une notice est mise à jour après de nouvelles études ou de nouveaux effets signalés. Une
liste de produits enregistrés évolue : produits ajoutés, retirés, renouvelés. Chaque
information garde donc sa **date de collecte**, affichée avec la citation, pour que le
lecteur sache de quand elle date.

## Note sur les différences entre pays

Un même médicament peut avoir une notice différente d'un pays à l'autre, car chaque
autorité valide son propre texte. Une source étrangère sert de complément, **jamais** de
substitut à la source algérienne. Le code applique cette règle dans
`ConflictPolicy.prefer_algerian`.
