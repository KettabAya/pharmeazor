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
| RCP et notices ANPP | 4 — officielle | 2026-11-13 | accès manuel uniquement | robots.txt : aucun chemin interdit. Aucun lien CGU ou mentions légales identifié sur la page d’accueil; conditions de réutilisation non confirmées. Vérifier les droits avant redistribution. |
| Nomenclature (Ministère de l'Industrie pharmaceutique) | 3 — officielle | *à remplir* | accès automatique interdit | téléchargement manuel |
| Thésaurus des interactions — ANSM | 2 — institutionnelle | *à remplir* | *à remplir* | complément, jamais substitut |
| DailyMed | 2 — institutionnelle | 2026-11-13 | accès interdit au corpus (droits non confirmés) | robots.txt : seul /archives/ est interdit. Droits de réutilisation des labels fournis par les sociétés non confirmés. Ne pas intégrer ni redistribuer sans vérification. |
| EMA | 2 — institutionnelle | *à remplir* | *à remplir* | notice européenne, peut différer |
| Pharm'Net (e-Sahti) | 1 — secondaire | 2026-11-13 | accès manuel uniquement | robots.txt : accès autorisé aux chemins publics, chemins privés et administratifs interdits. CGU : aucun lien identifié sur la page d'accueil lors de la vérification du 13/11/2026. Conditions d'utilisation non confirmées. |
| VIDAL | 0 — écartée | 2026-11-13 | forbidden | CGU : reproduction intégrale ou partielle interdite sans consentement. Source exclue faute d'autorisation de réutilisation. |
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

## État du corpus documentaire — semaine 1

### Paracétamol — DOLIPRANE 2,4 %

| Document | Source | Type | Rubriques extraites |
|---|---|---|---:|
| `paracetamol_doliprane_2.4_rcp` | ANPP (DZ) | RCP officiel | 5/5 |
| `paracetamol_doliprane_2.4_notice` | Pharm'Net (DZ) | Notice patient | 2/5 |

Le RCP officiel couvre les indications, la posologie, les contre-indications,
les interactions et les effets indésirables.

La notice patient est conservée comme document complémentaire. Son extraction
partielle (posologie et effets indésirables) est rapportée telle quelle ;
elle n'est pas assimilée à une fiche professionnelle.

Les fichiers PDF, TXT et JSON du corpus sont conservés localement dans
`data/raw/notices/`, dossier exclu du suivi Git.


### Amoxicilline — BIOPAMOX / AMOXICILLINE BGR

| Document | Source | Type | Rubriques extraites |
|---|---|---|---:|
| `amoxicilline_biopamox_rcp` | Pharm'Net (DZ) | RCP professionnel | 5/5 |
| `amoxicilline_bgr_1g_notice` | ANSM / BDPM (FR) | Notice patient officielle | 5/5 |

Le RCP BIOPAMOX est un document professionnel hébergé par Pharm'Net.
La notice AMOXICILLINE BGR est une notice patient officielle française,
conservée comme source complémentaire et non comme substitut à une source algérienne.

Les deux documents concernent des présentations pharmaceutiques différentes.
Leurs informations de dosage ne doivent pas être fusionnées.
