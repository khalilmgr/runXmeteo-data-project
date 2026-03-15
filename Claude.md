# SAÉ Data Pipeline — Contexte Projet

## Équipe
- **Khalil** (porteur du projet)
- **Adrien**
- **Nathan**
- **Arthur**

Étudiants en 2ème année BUT Informatique, parcours Data, à l'IUT Reims-Châlons-Charleville.

---

## Thématique
**Analyse comparative de performances de course à pied croisée avec des données environnementales.**

L'originalité du projet : nous utilisons nos propres données de course, collectées sur le terrain, et non un dataset pré-existant.

---

## Objectif
Construire un data pipeline complet :
1. **Ingestion** de deux sources de données distinctes
2. **Stockage** dans une base de données relationnelle (PostgreSQL)
3. **Automatisation** via cron sur une VM
4. **Visualisation** via Power BI + Streamlit
5. **Analyse critique** des données, biais et limites

---

## Sources de données

### Source 1 — Données de course (Garmin/Strava)
Données personnelles des 4 coureurs, exportées depuis Garmin Connect en CSV.

**Métriques disponibles :**
- Type d'activité, Date, Titre (identifiant du coureur)
- Distance (km), Calories, Durée
- Fréquence cardiaque moyenne / maximale
- TE aérobie
- Cadence de course moyenne / maximale
- Allure moyenne, Meilleure allure, GAP moyenne
- Ascension totale, Descente totale
- Longueur moyenne des foulées
- Puissance moyenne / max
- Pas, Nombre de tours, Temps du meilleur circuit
- Temps de déplacement, Temps écoulé
- Altitude minimale / maximale

### Source 2 — Données environnementales
API **Open-Meteo** (gratuite, sans clé API) pour récupérer au moment et au lieu exact de chaque course :
- Température
- Humidité
- Vent (vitesse, direction)
- Pression atmosphérique
- Précipitations

Complément possible : **qualité de l'air** via OpenAQ ou ATMO Grand Est (indice AQI, PM2.5, PM10, pollinique).

---

## Protocole de course

### Séance type
Format **3×400m** au Parc de Champagne, Reims :
- Tour 1 : modéré (échauffement)
- Tour 2 : à fond, 90-95% de la VMA (effort maximal)
- Tour 3 : récupération

Les 4 coureurs courent le même parcours, la même distance, dans les mêmes conditions.

### Plan de séances
| Séance | Objectif | Variables testées |
|--------|----------|-------------------|
| Séance 1 ✅ | Baseline commune | Référence — même parcours, même heure |
| Séance 2 | Effet de l'heure | Même parcours, heure différente (matin vs soir) |
| Séance 3 | Effet du terrain | Parcours différent (plat vs dénivelé, ville vs parc) |
| Séance 4 | Reproductibilité | Reprise conditions séance 1 |
| Séance 5 (bonus) | Météo extrême | Saisir une journée avec conditions différentes (pluie, chaleur, vent) |

### Séances réalisées

#### Séance 1 — 12 mars 2026, ~17h30, Parc de Champagne, Reims
Format : 3×400m
Fichier : `Seance1.csv`

| Coureur | Distance | Durée | FC moy | FC max | Allure moy | Meilleure allure | Cadence moy | Foulée moy | Pas |
|---------|----------|-------|--------|--------|-------------|------------------|-------------|-------------|-----|
| Adrien | 1.24 km | 07:23 | 159 | 170 | 5:57/km | 3:27/km | 149 | 1.09 m | 1116 |
| Nathan | 1.24 km | 06:12 | 184 | 196 | 5:00/km | 3:25/km | 144 | 1.36 m | 900 |
| Khalil | 1.26 km | 07:50 | 172 | 196 | 6:13/km | 2:47/km | 145 | 1.11 m | 1096 |
| Arthur | 1.26 km | 04:26 | 163 | 188 | 3:31/km | 2:05/km | 171 | 1.64 m | 766 |

**Observations préliminaires :**
- Arthur est nettement le plus rapide (allure 3:31/km, foulée 1.64m)
- Nathan a la FC la plus élevée (184 moy, 196 max) — effort cardiaque intense
- Khalil a la meilleure pointe de vitesse (2:47/km) mais l'allure moyenne la plus lente
- Adrien a la FC la plus basse (159 moy) — effort le plus maîtrisé

---

## Architecture technique

### Stack
| Composant | Technologie |
|-----------|-------------|
| VM | Machine virtuelle (déploiement complet) |
| Base de données | PostgreSQL |
| Ingestion | Python (parsing CSV + appels API Open-Meteo) |
| Automatisation | Cron (scripts Python planifiés) |
| Visualisation 1 | Power BI |
| Visualisation 2 | Streamlit |
| Versioning | GitLab |

### Schéma du pipeline
```
[Garmin CSV] → [Script Python parsing] → [PostgreSQL]
                                              ↑
[API Open-Meteo] → [Script Python API] ──────┘
                                              ↓
                                    [Power BI + Streamlit]
```

### Automatisation (Cron)
Script Python déclenché par cron qui :
1. Détecte de nouveaux fichiers CSV dans un dossier d'import
2. Parse et insère les données de course en base
3. Appelle Open-Meteo avec la date/heure/coordonnées GPS de la séance
4. Insère les données météo correspondantes
5. Log l'opération dans un fichier de journalisation

---

## Visualisations prévues

### Power BI — Vue d'ensemble et comparaison
- Comparaison d'allure entre les 4 coureurs par séance
- Évolution des performances dans le temps
- Corrélations météo / performance (matrice visuelle)
- KPI cards par coureur (meilleure allure, FC max, distance totale)

### Streamlit — Dashboard interactif et exploratoire
- Filtres dynamiques par coureur, séance, plage de dates
- Splits détaillés (si données disponibles)
- Scatter plots : allure vs température, FC vs humidité
- Carte du parcours avec Folium (si coordonnées GPS disponibles)
- Analyse statistique : moyennes, écarts-types, tendances

---

## Documentation à livrer (GitLab)

### README.md (Rapport Technique)
- Architecture du pipeline
- Schéma de la BDD
- Guide d'installation sur la VM
- Choix technologiques justifiés
- Organisation du travail en équipe

### Journal de bord
Historique versionné : idées, étapes, bugs, arbitrages techniques.

### Note de lecture critique
- À quelles questions nos visualisations répondent-elles ?
- Incertitudes des sources (précision GPS Garmin, station météo la plus proche vs lieu exact)
- Biais possibles (niveaux physiques différents, fatigue, alimentation, sommeil)
- Limites des visualisations (nombre de séances, taille de l'échantillon)
- Risques de mauvaise interprétation

---

## Soutenance (en anglais)
Structure :
1. **Problématique** : Can environmental conditions measurably impact running performance across different athletes?
2. **Données** : présentation des 2 sources
3. **Pipeline** : démonstration de l'architecture
4. **Démonstration live** des 2 dashboards
5. **Conclusions** tirées des données
6. **Discussion critique** : qualité de la donnée, fiabilité des conclusions visuelles

---

## Répartition du travail (suggestion)
| Membre | Responsabilité principale |
|--------|--------------------------|
| Personne A | Pipeline ingestion course + cron |
| Personne B | Pipeline météo/qualité de l'air + BDD PostgreSQL |
| Personne C | Dashboard Power BI |
| Personne D | Dashboard Streamlit |
| Tous | Documentation, journal de bord, analyse critique |

---

## État d'avancement
- [x] Idée validée
- [x] Protocole de course défini (3×400m)
- [x] Séance 1 réalisée (12/03/2026, Parc de Champagne)
- [x] CSV Séance 1 nettoyé (4 coureurs extraits)
- [ ] Séances 2 à 4 à planifier
- [ ] Création de la BDD PostgreSQL
- [ ] Scripts d'ingestion Python
- [ ] Configuration cron sur VM
- [ ] API Open-Meteo intégrée
- [ ] Dashboard Power BI
- [ ] Dashboard Streamlit
- [ ] README technique
- [ ] Journal de bord
- [ ] Note critique
- [ ] Préparation soutenance anglais
