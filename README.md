# SAÉ Data Pipeline — Running Performance Analysis

**BUT Informatique 2A — Parcours Data**
IUT Reims-Châlons-Charleville · 2025-2026

**Équipe :** Khalil · Adrien · Nathan · Arthur

**Présentation diaporama :** [presentation-sae.vercel.app](https://presentation-sae.vercel.app/)

---

## Problématique

> Les conditions environnementales (météo) ont-elles un impact mesurable sur les performances de course à pied, et cet impact varie-t-il selon les coureurs ?

Pour y répondre, nous collectons nos propres données de course (Garmin FIT second-par-second) et les croisons avec des données météorologiques (Open-Meteo) au moment et au lieu exact de chaque séance. Toutes les analyses portent sur le **Tour 2 uniquement** (400m à effort maximal), extrait automatiquement des fichiers FIT.

---

## Architecture du pipeline

```
[Garmin FIT CSV (second-par-second)]
        │
        ▼
[scripts/extract_tour2.py] ──► [data/fit/tour2_results.csv]
[scripts/ingest_csv.py] ──────────────────────┐
                                               ▼
[API Open-Meteo] ──► [scripts/ingest_meteo.py] ──► [PostgreSQL]
[data/meteo.json] ◄──────────────────────────────── (fallback local)
                                                         │
                              ┌──────────────────────────┤
                              ▼                          ▼
                        [Streamlit]               [Power BI]
```

Le script `scripts/pipeline.py` orchestre l'ensemble et est déclenché automatiquement par un **cron** sur la VM.

---

## Structure du dépôt

```
SAE_data/
├── data/
│   ├── Seance1.csv … Seance4.csv   # Archives Garmin (historique, non utilisées par le pipeline actuel)
│   ├── fit/                         # Fichiers FIT second-par-second
│   │   ├── {Coureur}_s{N}.csv      # Ex: Khalil_s2.csv
│   │   └── tour2_results.csv       # Métriques Tour 2 extraites (source principale dashboard)
│   ├── meteo.json                   # Météo Open-Meteo par séance (fallback sans PostgreSQL)
│   └── processed/                  # CSV archivés après ingestion
├── database/
│   └── schema.sql                  # Schéma PostgreSQL (5 tables + 1 vue)
├── scripts/
│   ├── extract_tour2.py            # Extraction Tour 2 depuis fichiers FIT
│   ├── ingest_csv.py               # Ingestion Tour 2 (tour2_results.csv) → PostgreSQL
│   ├── ingest_meteo.py             # Ingestion API Open-Meteo → PostgreSQL
│   ├── fetch_garmin.py             # Export activités Garmin API → CSV
│   └── pipeline.py                 # Orchestrateur principal (cron)
├── streamlit/
│   ├── app.py                      # Dashboard interactif (17 sections)
│   ├── db.py                       # Couche données (PostgreSQL + fallback CSV/JSON)
│   └── requirements.txt
├── POWER_BI/
│   └── SAE_S4.pbix                 # Dashboard Power BI
├── cron/
│   └── crontab.example             # Configuration cron à adapter sur la VM
├── logs/                           # Journaux d'exécution (ignoré par git)
├── .env.example                    # Modèle de configuration BDD
└── README.md
```

---

## Schéma de la base de données

```
coureurs          seances
────────          ───────
id (PK)           id (PK)
nom               numero
prenom            date_seance
                  heure_debut
                  lieu
                  latitude / longitude

activites                        meteo
─────────                        ─────
id (PK)                          id (PK)
coureur_id (FK → coureurs)       seance_id (FK → seances) UNIQUE
seance_id  (FK → seances)        temperature_c
distance_km                      temperature_ressentie_c
duree_secondes                   humidite_pct
allure_moyenne_s                 vent_vitesse_kmh / direction
meilleure_allure_s               precipitation_mm
fc_moyenne / fc_maximale         pression_hpa / uv_index
cadence_moyenne
foulee_moyenne_m                 conditions_coureur
puissance_moyenne_w              ──────────────────
te_aerobie                       id (PK)
...                              coureur_id (FK)
                                 seance_id  (FK)
                                 a_jeun / heures_sommeil
                                 etat_general (1-5)
                                 courbatures / dernier_repas_h
                                 notes

Vue : performances_avec_meteo
→ Jointure activites + seances + coureurs + meteo + conditions_coureur
→ Utilisée directement par Streamlit et Power BI
```

---

## Sources de données

### Source 1 — Garmin Connect (FIT + CSV)

Deux niveaux d'export depuis Garmin Connect après chaque séance :

**CSV résumé** — 1 ligne par activité avec métriques globales (allure moy, FC moy, distance...).
> ⚠️ Ces métriques moyennent les 3 tours (échauffement + effort + récupération) et **sous-estiment massivement la performance réelle**.

**FIT second-par-second** — 1 ligne par seconde avec vitesse instantanée, GPS, FC, cadence, puissance.
> ✅ Source principale des analyses. Permet d'isoler le **Tour 2** (effort maximal ~400m).

**Extraction automatique du Tour 2 (`scripts/extract_tour2.py`) :**
- Détection du pic de vitesse dans le FIT
- Seuil adaptatif : 75% du pic (évite de capturer l'échauffement)
- Résultat : `data/fit/tour2_results.csv` — métriques réelles du 400m rapide

> **Note :** Toutes les activités sont enregistrées sur le compte Garmin d'Arthur (70 kg).
> Les calories et puissance sont corrigées par le poids réel de chaque coureur.
>
> | Coureur | Poids | Facteur |
> |---------|-------|---------|
> | Arthur  | 70 kg | × 1.00 |
> | Nathan  | 76 kg | × 1.09 |
> | Khalil  | 80 kg | × 1.14 |
> | Adrien  | 64 kg | × 0.91 |

### Source 2 — Open-Meteo (API historique)

API météo **gratuite et sans clé API**. Données horaires au lieu et à l'heure exact de chaque séance.

Variables : température, température ressentie, humidité, vent (vitesse/direction/rafales), précipitations, pression atmosphérique, indice UV.

En mode local (sans VM) : les données sont sauvegardées dans `data/meteo.json` et chargées directement par le dashboard.

---

## Dashboard Streamlit — 17 sections

Toutes les métriques sont calculées sur le **Tour 2 uniquement**.

| # | Section | Contenu |
|---|---------|---------|
| 1 | KPI & Classement | Records personnels (temps 400m, FC max, cadence, puissance) |
| 2 | Temps 400m & Météo | Double axe temps/température, scatter corrélation |
| 3 | Puissance & Effort | Évolution watts, FC, efficacité cardiovasculaire |
| 4 | Face-à-tête | Comparaison 2 coureurs : tableau + radar normalisé |
| 5 | Profil de vitesse | Courbe m/s second-par-second sur le 400m |
| 6 | Accélérations | Dérivée de vitesse : départ fort / ralentissement fin |
| 7 | Récupération cardiaque | Descente FC après Tour 2, seuil ajustable |
| 8 | Heatmap Météo | Température × coureur × performance |
| 9 | Progression | Évolution % vs séance 1 sur 4 séances |
| 10 | Carte GPS animée | Simulation positions sur parcours réel (slider + animation Plotly) |
| 11 | Tour 1 / 2 / 3 | Comparaison échauffement / effort / récupération |
| 12 | Splits 100m | Stratégie de course : temps par tranche de 100m |
| 13 | Distribution vitesses | Histogramme + violin + zones de vitesse |
| 14 | Allure instantanée | Courbe min/km avec axe lisible |
| 15 | Puissance W/kg | Correction biais poids, watts bruts vs relatifs |
| 16 | FC vs Distance | Réponse cardiaque selon position sur le 400m |
| 17 | Vent & Direction | Rose des vents par séance, corrélation vent/performance |

> Le dashboard fonctionne en **mode local sans PostgreSQL** (fallback automatique sur `tour2_results.csv` + `meteo.json`).
> La connexion PostgreSQL s'active automatiquement une fois les variables `.env` configurées sur la VM.

---

## Guide d'installation sur la VM

### 1. Prérequis

```bash
sudo apt install postgresql postgresql-contrib python3 python3-venv python3-pip
```

### 2. Cloner le dépôt

```bash
git clone <url-du-depot-gitlab>
cd SAE_data
```

### 3. Environnement Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r streamlit/requirements.txt
```

### 4. Base de données

```bash
sudo -u postgres psql -c "CREATE DATABASE sae_running;"
sudo -u postgres psql -c "CREATE USER sae_user WITH PASSWORD 'votre_mdp';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sae_running TO sae_user;"
psql -U sae_user -d sae_running -f database/schema.sql
```

### 5. Configuration

```bash
cp .env.example .env
# Éditer .env avec les credentials PostgreSQL
```

### 6. Ingérer les données

```bash
# Déposer les FIT CSV dans data/fit/ puis extraire le Tour 2
python scripts/extract_tour2.py

# Ingérer les métriques Tour 2 + météo dans PostgreSQL
python scripts/pipeline.py
```

### 7. Configurer le cron

```bash
crontab cron/crontab.example
```

### 8. Lancer le dashboard

```bash
streamlit run streamlit/app.py --server.port 8501
```

---

## Séances réalisées

| Séance | Date | Heure | Conditions météo | Statut |
|--------|------|-------|-----------------|--------|
| S1 | 12/03/2026 | ~17h30 | 12.5°C · vent 23.6 km/h (SO) · sec | ✅ FIT + météo |
| S2 | 19/03/2026 | ~15h00 | 15.4°C · vent 15.1 km/h (NE) · sec | ✅ FIT + météo |
| S3 | 25/03/2026 | ~18h30 | 5.3°C · vent 23.6 km/h (ONO) · 1.4mm pluie | ✅ FIT + météo (Khalil absent) |
| S4 | 30/03/2026 | ~09h30 | 7.8°C · vent 16.7 km/h (ONO) · humidité 87% | ✅ FIT + météo |

**Coordonnées GPS :** 49.240841°N, 4.054274°E — Parc de Champagne, Reims

---

## Choix technologiques

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| Base de données | **PostgreSQL** | Standard industrie, transactions ACID, connecteur Power BI natif |
| Ingestion | **Python + pandas** | Parsing CSV flexible, appels API simples, format FIT natif |
| Extraction Tour 2 | **Python (numpy)** | Seuil adaptatif 75% du pic — fonctionne quel que soit le niveau du coureur |
| API météo | **Open-Meteo** | Gratuit, sans clé, données historiques horaires, couverture France |
| Automatisation | **Cron** | Natif Linux, simple, adapté à la fréquence de nos séances |
| Dashboard 1 | **Streamlit + Plotly** | Python natif, graphiques interactifs, animation GPS, déploiement immédiat |
| Dashboard 2 | **Power BI** | Connecteur PostgreSQL natif, adapté aux présentations |

---

## Biais identifiés

| Biais | Impact | Traitement |
|-------|--------|-----------|
| Profil Garmin unique (Arthur, 70 kg) | Calories, puissance, TE biaisés | ✅ Correction par poids réel (W/kg, kcal/km) |
| Métriques CSV moyennées sur 3 tours | Sous-estime la performance réelle de 30 à 60% | ✅ Remplacement par extraction FIT Tour 2 |
| Khalil absent séance 3 (maladie) | Données manquantes S3 | ✅ Exclu explicitement, mentionné dans les visu |
| GPS précision ±3-5m sur 400m | Distance ±1% | ⚠️ Normalisation à 400m exact pour comparaisons |
| Enregistrements à heures différentes (Adrien S4 à 12h34 vs groupe à 09h30) | Météo différente pour Adrien S4 | ⚠️ Mentionné en note critique |
| Niveaux physiques hétérogènes | Comparaison absolue peu pertinente | ✅ Progression % neutralise l'effet |
| Apprentissage du parcours S1→S2 | Amélioration non liée à la forme physique | ⚠️ Mentionné en note critique |
| Anomalie FC Nathan S2 (moy 115 bpm) | Valeur aberrante probable capteur | ⚠️ Signalé dans les visualisations |
