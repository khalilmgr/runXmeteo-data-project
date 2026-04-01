"""
db.py — Sources de données pour le dashboard SAÉ Running
─────────────────────────────────────────────────────────
Source principale : data/fit/tour2_results.csv  (métriques Tour 2 extraites des FIT)
Source secondaire : data/meteo.json             (Open-Meteo, 1 ligne par séance)
FIT raw          : data/fit/{Coureur}_s{N}.csv  (second-par-second, pour profils)

Fallback PostgreSQL conservé pour la VM.
"""

import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ROOT = Path(__file__).parent.parent
FIT_DIR = ROOT / "data" / "fit"

COUREURS_CONNUS = ["Adrien", "Nathan", "Khalil", "Arthur"]
POIDS = {"Arthur": 70, "Khalil": 80, "Adrien": 64, "Nathan": 76}

# Dates officielles des séances
SEANCE_DATES = {1: "2026-03-12", 2: "2026-03-19", 3: "2026-03-25", 4: "2026-03-30"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def pace_str(s):
    if s is None or pd.isna(s):
        return "N/A"
    try:
        return f"{int(s)//60}:{int(s)%60:02d}/km"
    except Exception:
        return "N/A"


def time_400m(duree_s, distance_m):
    """Normalise la durée à 400m exact."""
    if pd.isna(duree_s) or pd.isna(distance_m) or distance_m == 0:
        return None
    return duree_s * (400 / distance_m)


def _parse_fit_csv(path: Path) -> pd.DataFrame:
    """Parse un fichier FIT CSV Garmin (format décimal français)."""
    df = pd.read_csv(path)
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = df[c].str.replace(",", ".", regex=False)
            except AttributeError:
                pass
    df["ts"] = pd.to_datetime(df["timestamp"], dayfirst=True, errors="coerce")
    for col in ["enhanced_speed", "heart_rate", "cadence", "power", "distance",
                "enhanced_altitude", "grade_adjusted_speed",
                "position_lat", "position_long"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ── Tour 2 results ─────────────────────────────────────────────────────────────

def load_tour2() -> pd.DataFrame:
    """Charge tour2_results.csv et merge avec météo."""
    path = FIT_DIR / "tour2_results.csv"
    df = pd.read_csv(path)

    # Colonnes normalisées
    df = df.rename(columns={
        "coureur": "Coureur",
        "seance":  "Séance",
        "duree_s": "Durée_s",
        "distance_m": "Distance_m",
        "allure_s_km": "Allure_s",
        "allure_str": "Allure_str",
        "meilleure_allure_s_km": "Sprint_s",
        "meilleure_allure_str": "Sprint_str",
        "fc_moyenne": "FC_moy",
        "fc_max": "FC_max",
        "cadence_moyenne_spm": "Cadence_spm",
        "puissance_moyenne_w": "Puissance_w",
    })

    df["Temps400m_s"] = df.apply(lambda r: time_400m(r["Durée_s"], r["Distance_m"]), axis=1)
    df["Temps400m_str"] = df["Temps400m_s"].apply(
        lambda s: f"{int(s)//60}:{int(s)%60:02d}" if pd.notna(s) else "N/A"
    )
    df["Date"] = df["Séance"].map(SEANCE_DATES)

    # Merge météo
    meteo_path = ROOT / "data" / "meteo.json"
    if meteo_path.exists():
        meteo = pd.DataFrame(json.loads(meteo_path.read_text()))
        meteo = meteo.rename(columns={"seance": "Séance"})
        df = df.merge(meteo, on="Séance", how="left")

    return df.sort_values(["Séance", "Allure_s"]).reset_index(drop=True)


# ── FIT segment loader ────────────────────────────────────────────────────────

def load_fit_segment(coureur: str, seance: int,
                     window: str = "tour2",
                     post_minutes: float = 4.0) -> pd.DataFrame | None:
    """
    Charge le segment FIT d'un coureur pour une séance.

    window :
      "tour2"       → uniquement le Tour 2 (effort max)
      "post_tour2"  → post_minutes après la fin du Tour 2 (récupération)
      "full"        → activité complète
    """
    fit_path = FIT_DIR / f"{coureur}_s{seance}.csv"
    if not fit_path.exists():
        return None

    df = _parse_fit_csv(fit_path)
    if df["ts"].isna().all():
        return None

    # Récupère les bornes Tour 2 depuis tour2_results.csv
    t2_path = FIT_DIR / "tour2_results.csv"
    t2 = pd.read_csv(t2_path)
    row = t2[(t2["coureur"] == coureur) & (t2["seance"] == seance)]
    if row.empty and window != "full":
        return None

    if window != "full" and not row.empty:
        date = df["ts"].dropna().iloc[0].date()
        debut = pd.Timestamp(f"{date} {row.iloc[0]['tour2_debut']}")
        fin   = pd.Timestamp(f"{date} {row.iloc[0]['tour2_fin']}")

        if window == "tour2":
            mask = (df["ts"] >= debut) & (df["ts"] <= fin)
            ref_ts = debut
        else:  # post_tour2
            post_end = fin + pd.Timedelta(minutes=post_minutes)
            mask = (df["ts"] > fin) & (df["ts"] <= post_end)
            ref_ts = fin
    else:
        mask = pd.Series([True] * len(df), index=df.index)
        ref_ts = df["ts"].dropna().iloc[0]

    seg = df[mask].copy()
    if seg.empty:
        return None

    seg["t_rel"] = (seg["ts"] - ref_ts).dt.total_seconds()
    if "distance" in seg.columns and seg["distance"].notna().any():
        seg["dist_rel"] = seg["distance"] - seg["distance"].iloc[0]
    else:
        seg["dist_rel"] = seg["t_rel"]  # fallback

    return seg.reset_index(drop=True)


# ── Détection des 3 tours ────────────────────────────────────────────────────

def load_all_tours(coureur: str, seance: int) -> dict | None:
    """
    Divise l'activité en 3 tours en utilisant les bornes du Tour 2 déjà connues.
    Tour 1 = avant Tour 2 | Tour 2 = effort max | Tour 3 = après Tour 2.
    Returns dict: {'tour1': df, 'tour2': df, 'tour3': df} ou None si données manquantes.
    """
    fit_path = FIT_DIR / f"{coureur}_s{seance}.csv"
    if not fit_path.exists():
        return None

    df = _parse_fit_csv(fit_path)
    df = df.dropna(subset=["enhanced_speed"]).copy()
    if df.empty:
        return None

    df["t_act"] = (df["ts"] - df["ts"].iloc[0]).dt.total_seconds()

    # Récupère les bornes Tour 2 depuis tour2_results.csv
    t2_path = FIT_DIR / "tour2_results.csv"
    t2 = pd.read_csv(t2_path)
    row = t2[(t2["coureur"] == coureur) & (t2["seance"] == seance)]
    if row.empty:
        return None

    date = df["ts"].dropna().iloc[0].date()
    debut_t2 = pd.Timestamp(f"{date} {row.iloc[0]['tour2_debut']}")
    fin_t2   = pd.Timestamp(f"{date} {row.iloc[0]['tour2_fin']}")

    def make_seg(mask, num):
        seg = df[mask].copy()
        if seg.empty or seg["t_act"].max() - seg["t_act"].min() < 15:
            return None
        # Filtre vitesse > 1.0 m/s (exclut pauses)
        seg = seg[seg["enhanced_speed"] > 1.0].copy()
        if seg.empty:
            return None
        seg["t_lap"] = seg["t_act"] - seg["t_act"].iloc[0]
        seg["tour_num"] = num
        if "distance" in seg.columns:
            seg["dist_lap"] = seg["distance"] - seg["distance"].iloc[0]
        return seg.reset_index(drop=True)

    t1 = make_seg(df["ts"] < debut_t2, 1)
    t2_seg = make_seg((df["ts"] >= debut_t2) & (df["ts"] <= fin_t2), 2)
    t3 = make_seg(df["ts"] > fin_t2, 3)

    result = {}
    if t1 is not None:
        result["tour1"] = t1
    if t2_seg is not None:
        result["tour2"] = t2_seg
    if t3 is not None:
        result["tour3"] = t3

    return result if len(result) >= 2 else None


# ── PostgreSQL (VM) ────────────────────────────────────────────────────────────

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
        SELECT coureur AS "Coureur", seance AS "Séance", date_seance AS "Date",
               allure_moyenne_s AS "Allure_s", meilleure_allure_s AS "Sprint_s",
               distance_km*1000 AS "Distance_m", duree_secondes AS "Durée_s",
               fc_moyenne AS "FC_moy", fc_maximale AS "FC_max",
               cadence_moyenne AS "Cadence_spm",
               puissance_moyenne_w AS "Puissance_w",
               temperature_c, humidite_pct, vent_vitesse_kmh AS vent_kmh,
               precipitation_mm
        FROM performances_avec_meteo ORDER BY seance, allure_moyenne_s
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df["Allure_str"] = df["Allure_s"].apply(pace_str)
    df["Sprint_str"]  = df["Sprint_s"].apply(pace_str)
    df["Temps400m_s"] = df.apply(lambda r: time_400m(r["Durée_s"], r["Distance_m"]), axis=1)
    df["Temps400m_str"] = df["Temps400m_s"].apply(
        lambda s: f"{int(s)//60}:{int(s)%60:02d}" if pd.notna(s) else "N/A"
    )
    return df


def load_data() -> tuple[pd.DataFrame, str]:
    try:
        return _load_from_postgres(), "postgresql"
    except Exception:
        return load_tour2(), "csv"