# SAÉ Data Pipeline — Running Performance Analysis

**BUT Informatique 2A — Parcours Data**
IUT Reims-Châlons-Charleville · 2025-2026

**Équipe :** Khalil · Adrien · Nathan · Arthur

---

## Problématique

> Les conditions environnementales (météo) ont-elles un impact mesurable sur les performances de course à pied, et cet impact varie-t-il selon les coureurs ?

Pour y répondre, nous collectons nos propres données de course (Garmin) et les croisons avec des données météorologiques (Open-Meteo) au moment et au lieu exact de chaque séance.

---

## Architecture du pipeline

```
[Export Garmin CSV]
        │
        ▼
[scripts/ingest_csv.py] ──────────────────────┐
                                               ▼
[API Open-Meteo] ──► [scripts/ingest_meteo.py] ──► [PostgreSQL]
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
│   ├── SeanceN.csv          # Données Garmin brutes (déposées ici pour ingestion)
│   ├── processed/           # CSV archivés après ingestion
│   └── conditions.json      # Conditions physiologiques (local uniquement, non commité)
├── database/
│   └── schema.sql           # Schéma PostgreSQL (5 tables + vue)
├── scripts/
│   ├── ingest_csv.py        # Ingestion CSV Garmin → PostgreSQL
│   ├── ingest_meteo.py      # Ingestion API Open-Meteo → PostgreSQL
│   ├── fetch_garmin.py      # Export activités Garmin API → CSV
│   └── pipeline.py          # Orchestrateur principal (cron)
├── streamlit/
│   ├── app.py               # Dashboard interactif (6 pages)
│   ├── db.py                # Couche données (PostgreSQL + fallback CSV automatique)
│   └── requirements.txt     # Dépendances Python
├── cron/
│   └── crontab.example      # Configuration cron à adapter sur la VM
├── logs/                    # Journaux d'exécution (ignoré par git)
├── .env.example             # Modèle de configuration BDD
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
cadence_moyenne                  couverture_nuageuse_pct
foulee_moyenne_m                 vpd_kpa
puissance_moyenne_w
te_aerobie                conditions_coureur
...                       ──────────────────
                          id (PK)
                          coureur_id (FK)
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

### Source 1 — Garmin Connect (CSV)
Export depuis Garmin Connect après chaque séance.
Format : CSV avec ~35 colonnes (allure, FC, cadence, puissance, foulée...).

> **Note :** Toutes les activités sont enregistrées sur le compte Garmin d'Arthur (1m88, 70 kg).
> Les calories sont automatiquement corrigées par le poids réel de chaque coureur dans le dashboard.
> | Coureur | Poids | Facteur correction calories |
> |---------|-------|----------------------------|
> | Arthur  | 70 kg | × 1.00 |
> | Nathan  | 76 kg | × 1.09 |
> | Khalil  | 80 kg | × 1.14 |
> | Adrien  | 64 kg | × 0.91 |

### Source 2 — Open-Meteo (API)
API météo historique, **gratuite et sans clé API**.

Variables collectées : température, température ressentie, humidité, vent (vitesse/direction/rafales), précipitations, pression atmosphérique, indice UV, couverture nuageuse, VPD.

---

## Dashboard Streamlit — Pages

| Page | Contenu |
|------|---------|
| **Vue d'ensemble** | KPI par coureur, classement, records personnels |
| **Performance** | Allure par séance, % progression, évolution temporelle, heatmap |
| **Biomécanique** | Radar normalisé, cadence vs allure, foulée vs allure, efficacité cardio, TE, calories corrigées |
| **Météo & Corrélations** | Scatter temp/allure, humidité/FC, heatmap corrélations (actif après PostgreSQL) |
| **Tête-à-tête** | Comparaison directe de 2 coureurs sur toutes les métriques |
| **Conditions & Contexte** | Saisie conditions physiologiques, biais identifiés |

> Le dashboard fonctionne en **mode CSV** (sans PostgreSQL) avec fallback automatique.
> La page Météo s'active automatiquement une fois les données en base.

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
# Déposer les CSV dans data/ puis lancer le pipeline
cp Seance1.csv data/
cp Seance2.csv data/
python scripts/pipeline.py
```

### 7. Configurer le cron

```bash
# Éditer cron/crontab.example avec les bons chemins
crontab cron/crontab.example
```

### 8. Lancer le dashboard

```bash
streamlit run streamlit/app.py --server.port 8501
```

---

## Choix technologiques

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| Base de données | **PostgreSQL** | Standard industrie, transactions ACID, connecteur Power BI natif, déploiement VM simple |
| Ingestion | **Python + pandas** | Parsing CSV flexible, appels API simples, écosystème data riche |
| API météo | **Open-Meteo** | Gratuit, sans clé API, données historiques horaires précises, couverture France |
| Automatisation | **Cron** | Natif Linux, simple, suffisant pour la fréquence de nos séances |
| Dashboard 1 | **Streamlit** | Python natif, déploiement rapide, graphiques interactifs avec Plotly |
| Dashboard 2 | **Power BI** | Connecteur PostgreSQL natif, visualisations avancées, adapté aux présentations |

---

## Protocole de collecte

**Format des séances :** 3×400m au Parc de Champagne, Reims
**Coordonnées GPS :** 49.240841°N, 4.054274°E

| Séance | Date | Objectif | Statut |
|--------|------|----------|--------|
| Séance 1 | 12/03/2026 | Baseline commune | ✅ Données intégrées |
| Séance 2 | 19/03/2026 | Effet de l'heure | ✅ Données intégrées |
| Séance 3 | À venir | Effet du terrain (plat vs dénivelé) | ⏳ |
| Séance 4 | À venir | Reproductibilité (conditions séance 1) | ⏳ |

---

## Biais identifiés

| Biais | Impact | Traitement |
|-------|--------|-----------|
| Profil Garmin unique (Arthur, 70 kg) | Calories, puissance, TE biaisés | ✅ Calories corrigées par poids réel |
| À jeun / état physiologique variable | FC, énergie disponible | ✅ Collecté via page Conditions |
| GPS précision ~3-5m sur 400m | Distance ±1-2% | ❌ Non corrigeable |
| Métriques moyennées sur 3 tours | Mélange effort modéré + maximal + récup | ⚠️ Mentionné en note critique |
| Apprentissage du parcours S1→S2 | Amélioration non liée à la condition physique | ⚠️ Mentionné en note critique |
| Niveaux physiques hétérogènes | Comparaison absolue peu pertinente | ✅ % progression neutralise l'effet |

---

## Organisation du travail

| Membre | Responsabilité |
|--------|----------------|
| Khalil | Pipeline ingestion CSV + cron + Dashboard Streamlit |
| Adrien | Pipeline météo Open-Meteo + base de données PostgreSQL |
| Nathan | Dashboard Power BI |
| Arthur | Dashboard Power BI |
| Tous | Documentation, journal de bord, analyse critique, soutenance |