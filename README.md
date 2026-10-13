# Impact of Weather on Running Performance

End-of-year data project of my second year of the BUT Computer Science (Data track) at the IUT of Reims (2025-2026), done in a team of 4: do weather conditions measurably affect 400 m running performance, and does the effect differ from one runner to another?

We collected our own running data with GPS watches, enriched it with historical weather, stored it in PostgreSQL and explored it through a Streamlit dashboard (17 sections) and a Power BI report.

**Presentation:** [presentation-sae.vercel.app](https://presentation-sae.vercel.app/)

**Stack:** Python, Pandas, PostgreSQL, Streamlit, Plotly, Power BI, Open-Meteo API, cron (Linux).

## Team

Project of 4 students: Khalil, Adrien, Nathan and Arthur.

My contribution: design of the PostgreSQL schema (5 tables and one analytical view), and the ingestion scripts for the running data and the weather data. The rest of the pipeline, the dashboards and the analysis were built collectively.

## Research question

1. **Weather impact:** do temperature, wind, humidity and rain affect the 400 m time?
2. **Inter-individual variability:** does each runner respond differently to the same conditions?
3. **Progress vs weather:** how can real physical progress be separated from weather effects across sessions?

All analyses focus on the second lap of each session, a maximal effort of about 400 m, extracted automatically from second-by-second files.

## Data collection

- **Protocol:** 3 laps of 400 m on the same asphalt track (Parc de Champagne, Reims), with a warm-up lap, a maximal effort lap and a recovery lap.
- **Sessions:** 4 sessions in March 2026, in contrasted conditions, from dry and mild to cold with rain.
- **Volume:** 4 runners, 15 maximal efforts in total (one runner was absent for one session).
- **Sensors:** Garmin Instinct 2 (1 Hz GPS, heart rate, cadence, estimated power) and a Polar OH1+ optical sensor to cross-check heart rate.
- **Weather:** Open-Meteo historical API (temperature, apparent temperature, humidity, wind, precipitation, pressure, UV), matched to each session by time and GPS position.

## Pipeline

```
Garmin FIT data (1 Hz)
      |
      v
extract_tour2.py  -->  tour2_results.csv
      |                       |
      v                       v
 ingest_csv.py           ingest_meteo.py  <--  Open-Meteo API
      \                       /
       v                     v
            PostgreSQL (5 tables + view)
                  |
        +---------+---------+
        v                   v
    Streamlit            Power BI
```

- **Automatic lap detection:** the effort lap is isolated with an adaptive threshold set at 75% of the peak speed, within a plausible duration window, so it works whatever the level of the runner.
- **Database:** 5 tables (runners, sessions, activities, weather, runner conditions) and a view `performances_avec_meteo` that joins running data, session, runner and weather.
- **Automation:** `pipeline.py` orchestrates the steps and is triggered by a cron job on a Linux VM, so a new file refreshes the database and the dashboards.
- **Fallback mode:** the dashboard also runs without PostgreSQL, from local CSV and JSON files.

## Analysis tools

**Streamlit dashboard (17 sections)**
KPIs and records, 400 m time vs weather, power and effort, head-to-head comparison, speed profile, accelerations, heart-rate recovery, weather heatmap, progression, animated GPS map, lap comparison, 100 m splits, speed distribution, instantaneous pace, power per kilogram, heart rate vs distance, wind and direction.

**Power BI report**
Power Query cleaning and star schema, DAX measures (progress in percent, normalized 400 m time, power per kilogram, deviation from average), direct connection to the analytical view.

## Results

- A consistent trend appears: at similar effort, heart rate tends to be lower in colder conditions.
- Runners respond differently: one shows the strongest relative progression (about 14% faster between the first and last session) with a controlled heart rate, while the fastest runner has the most stable times.
- The data supports descriptive findings only. With 4 sessions, no causal link between weather and performance can be established, and no result is statistically significant.

## Limitations and biases

- **Small sample:** 4 runners and 4 sessions. Each runner is their own control.
- **Confounding:** temperature, humidity and wind are correlated, so their effects cannot be separated.
- **Course learning:** the improvement between the first sessions may reflect familiarity with the track rather than fitness.
- **Sensors:** GPS accuracy of about 3 to 5 m, heart-rate delay of about 15 s on short efforts, power estimated by an undocumented Garmin algorithm, one suspicious heart-rate value flagged as a probable sensor artifact.
- **Single watch profile:** all sessions were recorded on one account, so calories, power and zones were corrected with the real weight of each runner.
- **Weather:** model data from a cell 1 to 5 km away, which does not capture the microclimate of the park.
- **Unmeasured factors:** sleep, nutrition, fatigue and stress may matter more than weather.

The full discussion is in [NOTE_CRITIQUE.md](NOTE_CRITIQUE.md) and the project timeline in [JOURNAL_DE_BORD.md](JOURNAL_DE_BORD.md).

## Possible improvements

At least 8 to 10 sessions, a dedicated running power sensor, pre-session form tracking, air quality data, and wind angle relative to the running direction computed from GPS.

## Run the project

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r streamlit/requirements.txt

# Local mode, without PostgreSQL (CSV and JSON fallback)
streamlit run streamlit/app.py --server.port 8501
```

Full mode with PostgreSQL:

```bash
psql -U <user> -d <database> -f database/schema.sql
cp .env.example .env        # fill in the database credentials
python scripts/extract_tour2.py
python scripts/pipeline.py
crontab cron/crontab.example
```

## Repository structure

```
data/
  fit/                      second-by-second files and tour2_results.csv
  meteo.json                weather per session (local fallback)
database/
  schema.sql                PostgreSQL schema (5 tables and 1 view)
scripts/
  extract_tour2.py          effort lap extraction from FIT data
  ingest_csv.py             lap metrics to PostgreSQL
  ingest_meteo.py           Open-Meteo API to PostgreSQL
  fetch_garmin.py           Garmin activities export
  pipeline.py               orchestrator (cron)
streamlit/
  app.py, db.py             dashboard and data layer
POWER_BI/
  SAE_S4.pbix               Power BI report
cron/
  crontab.example
JOURNAL_DE_BORD.md          project log
NOTE_CRITIQUE.md            critical reading note
```

## Author

Khalil Moughamir
- Portfolio: [khalil-moughamir.vercel.app](https://khalil-moughamir.vercel.app)
- LinkedIn: [linkedin.com/in/khalil-moughamir](https://www.linkedin.com/in/khalil-moughamir)
