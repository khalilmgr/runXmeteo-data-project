"""
ingest_csv.py
─────────────
Lit data/fit/tour2_results.csv et insère les métriques Tour 2
dans la base PostgreSQL (tables seances + activites).

Source : data/fit/tour2_results.csv  (généré par extract_tour2.py)

Usage :
    python ingest_csv.py
    python ingest_csv.py --csv data/Seance1.csv --seance 1   # accepté (compat), ignoré
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

# ── Config logging ─────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "ingest.log"),
    ],
)
log = logging.getLogger(__name__)

load_dotenv(ROOT / ".env")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "sae_running"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Dates et heures officielles des séances
SEANCE_INFO = {
    1: {"date": "2026-03-12", "heure": "17:30:00"},
    2: {"date": "2026-03-19", "heure": "15:00:00"},
    3: {"date": "2026-03-25", "heure": "18:30:00"},
    4: {"date": "2026-03-30", "heure": "09:30:00"},
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def time_400m(duree_s, distance_m):
    if duree_s and distance_m and distance_m > 0:
        return round(duree_s * (400 / distance_m), 2)
    return None


def get_or_create_seance(cur, numero: int) -> int:
    cur.execute("SELECT id FROM seances WHERE numero = %s", (numero,))
    result = cur.fetchone()
    if result:
        return result[0]
    info = SEANCE_INFO.get(numero, {})
    cur.execute(
        "INSERT INTO seances (numero, date_seance, heure_debut) VALUES (%s, %s, %s) RETURNING id",
        (numero, info.get("date"), info.get("heure")),
    )
    seance_id = cur.fetchone()[0]
    log.info("Séance %d créée (id=%d)", numero, seance_id)
    return seance_id


def get_coureur_id(cur, nom: str) -> int | None:
    cur.execute("SELECT id FROM coureurs WHERE nom = %s", (nom,))
    result = cur.fetchone()
    if not result:
        log.error("Coureur '%s' introuvable en base", nom)
        return None
    return result[0]


# ── Ingestion ──────────────────────────────────────────────────────────────────

def ingest(conn) -> int:
    tour2_path = ROOT / "data" / "fit" / "tour2_results.csv"
    if not tour2_path.exists():
        log.error("Fichier introuvable : %s — lancez d'abord extract_tour2.py", tour2_path)
        return 0

    df = pd.read_csv(tour2_path)
    log.info("%d lignes Tour 2 à ingérer", len(df))

    inserted = 0
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            coureur_nom = str(row["coureur"]).strip()
            seance_num  = int(row["seance"])

            coureur_id = get_coureur_id(cur, coureur_nom)
            if coureur_id is None:
                continue

            seance_id = get_or_create_seance(cur, seance_num)
            conn.commit()

            t400 = time_400m(row.get("duree_s"), row.get("distance_m"))

            cur.execute(
                """
                INSERT INTO activites (
                    coureur_id, seance_id,
                    distance_km, duree_secondes,
                    allure_moyenne_s, meilleure_allure_s,
                    fc_moyenne, fc_maximale,
                    cadence_moyenne,
                    puissance_moyenne_w,
                    temps_400m_s, sprint_s
                )
                VALUES (
                    %(coureur_id)s, %(seance_id)s,
                    %(distance_km)s, %(duree_s)s,
                    %(allure_s_km)s, %(meilleure_allure_s_km)s,
                    %(fc_moyenne)s, %(fc_max)s,
                    %(cadence_moyenne_spm)s,
                    %(puissance_moyenne_w)s,
                    %(temps_400m_s)s, %(sprint_s)s
                )
                ON CONFLICT (coureur_id, seance_id) DO UPDATE SET
                    distance_km         = EXCLUDED.distance_km,
                    duree_secondes      = EXCLUDED.duree_secondes,
                    allure_moyenne_s    = EXCLUDED.allure_moyenne_s,
                    meilleure_allure_s  = EXCLUDED.meilleure_allure_s,
                    fc_moyenne          = EXCLUDED.fc_moyenne,
                    fc_maximale         = EXCLUDED.fc_maximale,
                    cadence_moyenne     = EXCLUDED.cadence_moyenne,
                    puissance_moyenne_w = EXCLUDED.puissance_moyenne_w,
                    temps_400m_s        = EXCLUDED.temps_400m_s,
                    sprint_s            = EXCLUDED.sprint_s
                """,
                {
                    "coureur_id":           coureur_id,
                    "seance_id":            seance_id,
                    "distance_km":          round(row.get("distance_m", 0) / 1000, 3),
                    "duree_s":              int(row["duree_s"]) if pd.notna(row.get("duree_s")) else None,
                    "allure_s_km":          int(row["allure_s_km"]) if pd.notna(row.get("allure_s_km")) else None,
                    "meilleure_allure_s_km":int(row["meilleure_allure_s_km"]) if pd.notna(row.get("meilleure_allure_s_km")) else None,
                    "fc_moyenne":           int(row["fc_moyenne"]) if pd.notna(row.get("fc_moyenne")) else None,
                    "fc_max":               int(row["fc_max"]) if pd.notna(row.get("fc_max")) else None,
                    "cadence_moyenne_spm":  int(row["cadence_moyenne_spm"]) if pd.notna(row.get("cadence_moyenne_spm")) else None,
                    "puissance_moyenne_w":  int(row["puissance_moyenne_w"]) if pd.notna(row.get("puissance_moyenne_w")) else None,
                    "temps_400m_s":         t400,
                    "sprint_s":             int(row["meilleure_allure_s_km"]) if pd.notna(row.get("meilleure_allure_s_km")) else None,
                },
            )
            inserted += 1
            log.info("✓ %s S%d — temps 400m : %ss", coureur_nom, seance_num, t400)

    conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Ingestion Tour 2 (tour2_results.csv) vers PostgreSQL")
    # Compatibilité ascendante : d'anciens appels passent --csv/--seance.
    parser.add_argument("--csv", default=None, help="Ignoré (ancien mode Garmin résumé)")
    parser.add_argument("--seance", default=None, type=int, help="Ignoré (ancien mode Garmin résumé)")
    parser.parse_args()

    (ROOT / "logs").mkdir(exist_ok=True)
    log.info("=== Début ingestion Tour 2 → PostgreSQL ===")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log.info("Connexion PostgreSQL OK")
    except psycopg2.OperationalError as e:
        log.error("Connexion échouée : %s", e)
        sys.exit(1)

    try:
        nb = ingest(conn)
        log.info("=== Ingestion terminée : %d ligne(s) insérée(s) ===", nb)
    except Exception as e:
        log.error("Erreur : %s", e)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
