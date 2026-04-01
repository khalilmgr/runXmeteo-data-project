# Journal de bord — SAÉ Data Pipeline

**BUT Informatique 2A · Parcours Data**
IUT Reims-Châlons-Charleville · 2025-2026
Équipe : Khalil · Adrien · Nathan · Arthur

---

## Semaine 1 — Cadrage du projet (début mars 2026)

**Idée initiale :** analyser l'impact des conditions météo sur nos performances de course. Originalité du projet : utiliser nos propres données plutôt qu'un dataset existant.

**Décisions prises :**
- Format retenu : 3×400m au Parc de Champagne, Reims — parcours identique pour tous, conditions contrôlées
- Enregistrement sur le Garmin d'Arthur (seul à en avoir un) — accepté avec note sur le biais profil
- Sources de données : Garmin Connect (export CSV + FIT) + API Open-Meteo (gratuite, sans clé)
- Stack technique : Python + PostgreSQL + Streamlit + Power BI

**Problème identifié dès le départ :** les CSV exportés depuis Garmin moyennent les 3 tours (échauffement + effort + récupération), ce qui masque complètement la performance réelle du 400m rapide. Solution envisagée : utiliser les fichiers FIT second-par-second pour isoler le Tour 2.

---

## Séance 1 — 12 mars 2026, ~17h30, Parc de Champagne

**Conditions :** 12.5°C · vent 23.6 km/h (direction SO) · sec · ressenti 7.4°C

**Résultats Tour 2 (extrait des FIT) :**
| Coureur | Temps 400m | Allure | FC moy | FC max |
|---------|-----------|--------|--------|--------|
| Arthur  | 0:56      | 2:14/km | 178 bpm | 188 bpm |
| Khalil  | 1:15      | 3:02/km | 190 bpm | 196 bpm |
| Nathan  | 1:27      | 3:38/km | 192 bpm | 196 bpm |
| Adrien  | 1:32      | 3:43/km | 167 bpm | 170 bpm |

**Observations :** Arthur nettement le plus rapide. Nathan et Khalil poussent fort en FC (196 bpm max). Adrien a la FC la plus maîtrisée.

**Point technique :** réalisation que les CSV Garmin utilisent la virgule comme séparateur décimal (format français) dans les fichiers FIT. Nécessite un pré-traitement avant `pd.to_numeric()`.

---

## Semaine 2 — Développement du pipeline (mi-mars 2026)

**Travail effectué :**
- Khalil : mise en place du schéma PostgreSQL (5 tables + vue `performances_avec_meteo`), scripts `ingest_csv.py` et `ingest_meteo.py`
- Adrien : intégration API Open-Meteo, test des appels historiques
- Nathan + Arthur : exploration Power BI, connexion PostgreSQL

**Difficultés rencontrées :**
- L'API Open-Meteo historique renvoie des données horaires (pas à la minute). Résolu : on prend l'heure de début de séance.
- Les exports Garmin cumulatifs : `Seance2.csv` contient aussi les activités de S1. Résolu dans `db.py` avec `drop_duplicates`.
- Colonnes nommées différemment selon le type d'activité (course vs vélo) dans les CSV Garmin S2. Résolu avec `_col()` qui essaie plusieurs noms.

---

## Séance 2 — 19 mars 2026, ~15h00, Parc de Champagne

**Conditions :** 15.4°C · vent 15.1 km/h (direction NE) · sec · ressenti 12.2°C

**Résultats Tour 2 :**
| Coureur | Temps 400m | Allure | FC moy | FC max |
|---------|-----------|--------|--------|--------|
| Arthur  | 0:57      | 2:18/km | 176 bpm | 181 bpm |
| Nathan  | 1:13      | 3:00/km | 115 bpm* | 165 bpm |
| Khalil  | 1:26      | 3:32/km | 163 bpm | 169 bpm |
| Adrien  | 1:37      | 3:58/km | 179 bpm | 182 bpm |

*Anomalie FC Nathan : FC moyenne 115 bpm avec FC max 165 — probable artefact capteur en début de Tour 2 (capteur mal positionné ou départ froid). Valeur à interpréter avec précaution.

**Observation :** conditions météo plus favorables (plus chaud, moins de vent). Khalil passe de 3:02 à 3:32 — régression notable à analyser (fatigue ? apprentissage ? météo ?). Nathan progresse fortement (3:38 → 3:00).

---

## Semaine 3 — Extraction Tour 2 et dashboard Streamlit (fin mars 2026)

**Décision clé :** abandonner les CSV résumés comme source principale du dashboard. Exemple concret : Adrien S4 affiché à 8:41/km dans le CSV résumé (inclut la récupération marchée) vs 3:53/km en Tour 2 réel. L'écart est trop important pour toute analyse sérieuse.

**Développement `extract_tour2.py` :**
- Premier algorithme : seuil fixe 3.2 m/s → échec sur Arthur (il court l'échauffement à 4 m/s, supérieur au seuil)
- Solution retenue : **seuil relatif 75% du pic** — s'adapte automatiquement au niveau de chaque coureur
- Validé sur tous les fichiers : détection correcte du Tour 2 pour les 16 entrées disponibles

**Dashboard Streamlit :** refonte complète, 17 sections, données Tour 2 comme source unique.

**Météo sans VM :** réalisation que l'API Open-Meteo peut être appelée directement en local et sauvegardée dans `data/meteo.json`. Le dashboard l'intègre sans nécessiter PostgreSQL.

---

## Séance 3 — 25 mars 2026, ~18h30, Parc de Champagne

**Conditions :** 5.3°C · vent 23.6 km/h (direction ONO) · **1.4mm de pluie** · ressenti 0.1°C — séance la plus difficile météo

**Résultats Tour 2 :**
| Coureur | Temps 400m | Allure | FC moy | FC max |
|---------|-----------|--------|--------|--------|
| Arthur  | 0:57      | 2:25/km | 150 bpm | 157 bpm |
| Nathan  | 1:18      | 3:13/km | 158 bpm | 161 bpm |
| Adrien  | 1:31      | 3:51/km | 169 bpm | 172 bpm |
| Khalil  | —         | —       | —       | —       |

**Khalil absent (maladie).** Décision : ne pas créer de données synthétiques — Khalil S3 exclu explicitement des analyses.

**Observation :** FC d'Arthur nettement plus basse (150 vs 178 en S1) malgré un temps similaire. Piste : temps froid facilite la dissipation thermique, FC peut rester plus basse à même effort.

---

## Séance 4 — 30 mars 2026, ~09h30, Parc de Champagne

**Conditions :** 7.8°C · vent 16.7 km/h (ONO) · humidité 87% · 0.1mm (sol humide)

**Résultats Tour 2 :**
| Coureur | Temps 400m | Allure | FC moy | FC max |
|---------|-----------|--------|--------|--------|
| Arthur  | 1:00      | 2:22/km | 176 bpm | 183 bpm |
| Khalil  | 1:16      | 3:16/km | 186 bpm | 193 bpm |
| Nathan  | 1:30      | 3:49/km | 160 bpm | 165 bpm |
| Adrien  | 1:34      | 3:53/km | 145 bpm | 158 bpm |

**Particularité :** Adrien a couru S4 à 12h34 (3 heures après les autres). Conditions météo légèrement différentes. Mentionné en note critique.

**Problème technique :** fichier `Adrien_s4.csv` initialement tronqué (98 lignes au lieu de ~420) lors du transfert. Fichier complet re-transmis et intégré.

---

## Fin mars / début avril 2026 — Finalisation

**Pipeline FIT complet :** 16 fichiers FIT traités (4 coureurs × 4 séances, sauf Khalil S3). Tour 2 extrait pour chacun.

**Dashboard finalisé :** 17 sections couvrant KPI, météo, biomécanique, GPS animée, splits 100m, récupération cardiaque, puissance W/kg, vent/direction.

**Météo réelle intégrée :** 4 séances × 8 variables météo issues d'Open-Meteo.

**Biais documenté :** Garmin d'Arthur enregistre sur son profil (70 kg) → correction W/kg appliquée dans la section 15, correction kcal/km dans la section 3.

**En cours :** déploiement VM (PostgreSQL + cron), Power BI multi-séances, soutenance.