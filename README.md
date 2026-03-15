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
│   ├── Seance1.csv          # Données Garmin brutes
│   └── processed/           # CSV archivés après ingestion
├── database/
│   └── schema.sql           # Schéma PostgreSQL (tables + vue)
├── scripts/
│   ├── ingest_csv.py        # Ingestion CSV Garmin → PostgreSQL
│   ├── ingest_meteo.py      # Ingestion API Open-Meteo → PostgreSQL
│   └── pipeline.py          # Orchestrateur principal (cron)
├── streamlit/
│   ├── app.py               # Dashboard interactif
│   ├── db.py                # Couche données (PostgreSQL + fallback CSV)
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
                  description

activites                        meteo
─────────                        ─────
id (PK)                          id (PK)
coureur_id (FK → coureurs)       seance_id (FK → seances) UNIQUE
seance_id  (FK → seances)        temperature_c
distance_km                      temperature_ressentie_c
duree_secondes                   humidite_pct
allure_moyenne_s                 vent_vitesse_kmh
meilleure_allure_s               vent_rafales_kmh
fc_moyenne / fc_maximale         vent_direction_deg
cadence_moyenne                  precipitation_mm
foulee_moyenne_m                 pression_hpa
puissance_moyenne_w              uv_index
te_aerobie                       couverture_nuageuse_pct
...                              vpd_kpa

Vue : performances_avec_meteo
→ Jointure activites + seances + coureurs + meteo
→ Utilisée directement par Streamlit et Power BI
```

---

## Sources de données

### Source 1 — Garmin Connect (CSV)
Export manuel depuis Garmin Connect par chaque coureur après chaque séance.
Format : CSV avec ~35 colonnes (allure, FC, cadence, puissance, foulée...).

### Source 2 — Open-Meteo (API)
API météo historique, **gratuite et sans clé API**.
Documentation : https://open-meteo.com/en/docs

Variables collectées : température, température ressentie, humidité, vent (vitesse/direction/rafales), précipitations, pression atmosphérique, indice UV, couverture nuageuse.

---

## Guide d'installation sur la VM

### 1. Prérequis

```bash
# PostgreSQL
sudo apt install postgresql postgresql-contrib

# Python 3.11+
sudo apt install python3 python3-venv python3-pip
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
# Créer la base
sudo -u postgres psql -c "CREATE DATABASE sae_running;"
sudo -u postgres psql -c "CREATE USER sae_user WITH PASSWORD 'votre_mdp';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sae_running TO sae_user;"

# Appliquer le schéma
psql -U sae_user -d sae_running -f database/schema.sql
```

### 5. Configuration

```bash
cp .env.example .env
# Éditer .env avec les credentials PostgreSQL
```

### 6. Tester le pipeline manuellement

```bash
# Déposer un CSV dans data/
cp Seance1.csv data/

# Lancer le pipeline
python scripts/pipeline.py
```

### 7. Configurer le cron

```bash
# Éditer cron/crontab.example en remplaçant les chemins
crontab cron/crontab.example
```

### 8. Lancer le dashboard Streamlit

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

| Séance | Date | Objectif |
|--------|------|----------|
| Séance 1 ✅ | 12/03/2026 | Baseline commune |
| Séance 2 | À venir | Effet de l'heure (matin vs soir) |
| Séance 3 | À venir | Effet du terrain (plat vs dénivelé) |
| Séance 4 | À venir | Reproductibilité (conditions séance 1) |

---

