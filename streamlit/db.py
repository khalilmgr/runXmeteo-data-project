"""
db.py
─────
Gestion de la source de données pour le dashboard Streamlit.

- Si PostgreSQL est configuré et accessible → lit depuis la BDD
- Sinon → fallback sur les fichiers CSV locaux

Cela permet de développer localement sans BDD
et de basculer automatiquement sur PostgreSQL une fois sur la VM.
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ── Helpers de conversion (réutilisés depuis ingest_csv) ──────────────────────

def pace_to_seconds(value: str):
    s = str(value).strip()
    if s in ("--", "", "nan"):
        return None
    parts = s.split(":")
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None


def duration_to_seconds(value: str):
    import re
    s = str(value).strip()
    s = re.sub(r"\.\d+$", "", s)
    parts = s.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None


def clean_int(value):
    try:
        return int(str(value).replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def seconds_to_pace_str(s):
    if s is None or (hasattr(s, '__class__') and s != s):
        return "N/A"
    try:
        m = int(s) // 60
        sec = int(s) % 60
        return f"{m}:{sec:02d}/km"
    except Exception:
        return "N/A"


# ── Source PostgreSQL ──────────────────────────────────────────────────────────

def _load_from_postgres() -> pd.DataFrame:
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "sae_running"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )

    query = """
        SELECT
            coureur,
            seance,
            date_seance,
            allure_moyenne_s,
            meilleure_allure_s,
            distance_km,
            duree_secondes,
            fc_moyenne,
            fc_maximale,
            cadence_moyenne,
            foulee_moyenne_m,
            puissance_moyenne_w,
            te_aerobie,
            calories,
            temperature_c,
            temperature_ressentie_c,
            humidite_pct,
            vent_vitesse_kmh,
            vent_direction_deg,
            precipitation_mm,
            pression_hpa,
            uv_index
        FROM performances_avec_meteo
        ORDER BY seance, allure_moyenne_s
    """

    df = pd.read_sql(query, conn)
    conn.close()

    df["Durée_min"] = df["duree_secondes"] / 60
    df["Allure_str"] = df["allure_moyenne_s"].apply(seconds_to_pace_str)
    df["Meilleure_allure_str"] = df["meilleure_allure_s"].apply(seconds_to_pace_str)

    # Renommage pour compatibilité avec app.py
    df = df.rename(columns={
        "coureur":           "Coureur",
        "seance":            "Séance",
        "date_seance":       "Date",
        "allure_moyenne_s":  "Allure_s",
        "meilleure_allure_s":"Meilleure_allure_s",
        "distance_km":       "Distance",
        "duree_secondes":    "Durée_s",
        "fc_moyenne":        "FC_moy",
        "fc_maximale":       "FC_max",
        "cadence_moyenne":   "Cadence_moy",
        "foulee_moyenne_m":  "Foulée_moy",
        "puissance_moyenne_w":"Puissance_moy",
        "te_aerobie":        "TE",
        "calories":          "Calories",
        "temperature_c":         "Météo_Temp",
        "temperature_ressentie_c":"Météo_TempRessentie",
        "humidite_pct":          "Météo_Humidite",
        "vent_vitesse_kmh":      "Météo_Vent",
        "precipitation_mm":      "Météo_Precipitation",
    })

    return df


# ── Source CSV (fallback) ──────────────────────────────────────────────────────

def _load_from_csv() -> pd.DataFrame:
    import re

    csv_path = Path(__file__).parent.parent / "Seance1.csv"
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    df["Coureur"] = df["Titre"].str.replace(r"\d.*$", "", regex=True).str.strip()
    df["Séance"] = 1
    df["Date"] = "2026-03-12"

    df["Allure_s"] = df["Allure moyenne"].apply(pace_to_seconds)
    df["Meilleure_allure_s"] = df["Meilleure allure"].apply(pace_to_seconds)
    df["Allure_str"] = df["Allure_s"].apply(seconds_to_pace_str)
    df["Meilleure_allure_str"] = df["Meilleure_allure_s"].apply(seconds_to_pace_str)

    df["Durée_s"] = df["Durée"].apply(duration_to_seconds)
    df["Durée_min"] = df["Durée_s"] / 60

    df["Distance"] = pd.to_numeric(df["Distance"], errors="coerce")
    df["Calories"] = pd.to_numeric(df["Calories"], errors="coerce")
    df["FC_moy"] = pd.to_numeric(df["Fréquence cardiaque moyenne"], errors="coerce")
    df["FC_max"] = pd.to_numeric(df["Fréquence cardiaque maximale"], errors="coerce")
    df["Cadence_moy"] = pd.to_numeric(df["Cadence de course moyenne"], errors="coerce")
    df["Foulée_moy"] = pd.to_numeric(df["Longueur moyenne des foulées"], errors="coerce")
    df["Puissance_moy"] = pd.to_numeric(df["Puissance moyenne"], errors="coerce")
    df["Puissance_max"] = pd.to_numeric(df["Puissance max."], errors="coerce")
    df["TE"] = pd.to_numeric(df["TE aérobie"], errors="coerce")
    df["Pas"] = df["Pas"].apply(clean_int)

    # Colonnes météo vides en mode CSV
    for col in ["Météo_Temp", "Météo_TempRessentie", "Météo_Humidite",
                "Météo_Vent", "Météo_Precipitation"]:
        df[col] = None

    return df


# ── Point d'entrée public ──────────────────────────────────────────────────────

def load_data() -> tuple[pd.DataFrame, str]:
    """
    Retourne (dataframe, source) où source vaut "postgresql" ou "csv".
    """
    try:
        df = _load_from_postgres()
        return df, "postgresql"
    except Exception:
        df = _load_from_csv()
        return df, "csv"