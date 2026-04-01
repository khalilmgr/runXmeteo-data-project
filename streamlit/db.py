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

COUREURS_CONNUS = ["Adrien", "Nathan", "Khalil", "Arthur"]


def _get_coureur(titre: str) -> str | None:
    for nom in COUREURS_CONNUS:
        if nom.lower() in str(titre).lower():
            return nom
    return None


def _col(row, *noms):
    for nom in noms:
        val = row.get(nom)
        if val is not None and str(val).strip() not in ("--", "", "nan"):
            return val
    return None


def _parse_seance(csv_path: Path, numero: int) -> pd.DataFrame:
    import re
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # Garder uniquement les courses à pied des 4 coureurs
    df = df[df["Type d'activité"].str.lower().str.contains("course", na=False)].copy()
    df["Coureur"] = df["Titre"].apply(_get_coureur)
    df = df[df["Coureur"].notna()].copy()

    if df.empty:
        return pd.DataFrame()

    df["Séance"] = numero
    df["Date"] = df["Date"].str[:10]

    # Allure — deux noms de colonnes possibles selon le type d'export
    df["Allure_s"] = df.apply(lambda r: pace_to_seconds(_col(r, "Allure moyenne", "Vitesse moyenne")), axis=1)
    df["Meilleure_allure_s"] = df.apply(lambda r: pace_to_seconds(_col(r, "Meilleure allure", "Vitesse max")), axis=1)
    df["Allure_str"] = df["Allure_s"].apply(seconds_to_pace_str)
    df["Meilleure_allure_str"] = df["Meilleure_allure_s"].apply(seconds_to_pace_str)

    df["Durée_s"] = df["Durée"].apply(duration_to_seconds)
    df["Durée_min"] = df["Durée_s"] / 60
    df["Distance"] = pd.to_numeric(df["Distance"], errors="coerce")
    df["Calories"] = pd.to_numeric(df["Calories"], errors="coerce")
    df["FC_moy"] = pd.to_numeric(df["Fréquence cardiaque moyenne"], errors="coerce")
    df["FC_max"] = pd.to_numeric(df["Fréquence cardiaque maximale"], errors="coerce")

    # Cadence — deux noms possibles
    df["Cadence_moy"] = df.apply(
        lambda r: clean_int(_col(r, "Cadence de course moyenne", "Cadence de vélo moyenne")), axis=1
    )
    df["Foulée_moy"] = pd.to_numeric(df["Longueur moyenne des foulées"], errors="coerce")
    df["Puissance_moy"] = pd.to_numeric(df["Puissance moyenne"], errors="coerce")
    df["TE"] = pd.to_numeric(df["TE aérobie"], errors="coerce")
    df["Pas"] = df["Pas"].apply(clean_int)

    for c in ["Météo_Temp", "Météo_TempRessentie", "Météo_Humidite", "Météo_Vent", "Météo_Precipitation"]:
        df[c] = None

    return df


def _load_from_csv() -> pd.DataFrame:
    import re
    root = Path(__file__).parent.parent

    # Détecter tous les SeanceN.csv à la racine ou dans data/
    csv_files = sorted([
        *root.glob("Seance*.csv"),
        *root.glob("data/Seance*.csv"),
    ])

    frames = []
    for csv_path in csv_files:
        match = re.search(r"(\d+)", csv_path.stem)
        numero = int(match.group(1)) if match else 0
        frame = _parse_seance(csv_path, numero)
        if not frame.empty:
            frames.append(frame)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    # Garmin exporte en cumulatif : Seance2.csv contient aussi les activités de Seance1.
    # On garde la première occurrence (séance la plus basse) pour chaque (Coureur, Date).
    df = df.sort_values("Séance").drop_duplicates(subset=["Coureur", "Date"], keep="first").reset_index(drop=True)
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