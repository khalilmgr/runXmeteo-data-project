"""
ingest_meteo.py
───────────────
Appelle l'API Open-Meteo pour récupérer les données météo
au moment et au lieu exact d'une séance, puis les insère
dans la table `meteo` de la base PostgreSQL.

Usage :
    python ingest_meteo.py --seance 1
    python ingest_meteo.py --seance 2
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

# ── Config logging ─────────────────────────────────────────────────────────────
(Path(__file__).parent.parent / "logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "ingest.log"),
    ],
)
log = logging.getLogger(__name__)

# ── Chargement des variables d'environnement ───────────────────────────────────
load_dotenv(Path(__file__).parent.parent / ".env")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "sae_running"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# ── Paramètres Open-Meteo ──────────────────────────────────────────────────────
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

VARIABLES_HORAIRES = ",".join([
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dew_point_2m",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "precipitation",
    "surface_pressure",
    "uv_index",
    "cloud_cover",
    "visibility",
    "vapour_pressure_deficit",
])


# ── Récupération des données météo ─────────────────────────────────────────────

def fetch_meteo(lat: float, lon: float, date: str, heure: str) -> dict:
    """
    Appelle Open-Meteo Historical API et retourne les valeurs
    pour l'heure exacte de la séance.

    date  : "2026-03-12"
    heure : "17:30:00"
    """
    params = {
        "latitude":        lat,
        "longitude":       lon,
        "start_date":      date,
        "end_date":        date,
        "hourly":          VARIABLES_HORAIRES,
        "timezone":        "Europe/Paris",
        "wind_speed_unit": "kmh",
    }

    log.info("Appel Open-Meteo : lat=%s lon=%s date=%s heure=%s", lat, lon, date, heure)
    response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    # Trouver l'index correspondant à l'heure de la séance
    heure_cible = f"{date}T{heure[:5]}"  # ex: "2026-03-12T17:30"
    times = data["hourly"]["time"]

    # On prend l'heure la plus proche (arrondi à l'heure inférieure)
    heure_h = int(heure[:2])
    index = None
    for i, t in enumerate(times):
        if t == f"{date}T{heure_h:02d}:00":
            index = i
            break

    if index is None:
        log.warning("Heure exacte non trouvée, on prend la première disponible")
        index = 0

    hourly = data["hourly"]

    def val(key):
        v = hourly.get(key, [None])
        return v[index] if index < len(v) else None

    meteo = {
        "temperature_c":            val("temperature_2m"),
        "temperature_ressentie_c":  val("apparent_temperature"),
        "humidite_pct":             val("relative_humidity_2m"),
        "point_de_rosee_c":         val("dew_point_2m"),
        "vent_vitesse_kmh":         val("wind_speed_10m"),
        "vent_rafales_kmh":         val("wind_gusts_10m"),
        "vent_direction_deg":       val("wind_direction_10m"),
        "precipitation_mm":         val("precipitation"),
        "pression_hpa":             val("surface_pressure"),
        "uv_index":                 val("uv_index"),
        "couverture_nuageuse_pct":  val("cloud_cover"),
        "visibilite_m":             val("visibility"),
        "vpd_kpa":                  val("vapour_pressure_deficit"),
    }

    log.info(
        "Météo récupérée : %.1f°C, ressentie %.1f°C, humidité %s%%, vent %.1f km/h",
        meteo["temperature_c"] or 0,
        meteo["temperature_ressentie_c"] or 0,
        meteo["humidite_pct"] or 0,
        meteo["vent_vitesse_kmh"] or 0,
    )

    return meteo


# ── Insertion en base ──────────────────────────────────────────────────────────

def get_seance(cur, numero: int) -> tuple | None:
    cur.execute(
        "SELECT id, date_seance, heure_debut, latitude, longitude FROM seances WHERE numero = %s",
        (numero,)
    )
    return cur.fetchone()


def insert_meteo(seance_id: int, meteo: dict, conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO meteo (
                seance_id,
                temperature_c, temperature_ressentie_c,
                humidite_pct, point_de_rosee_c,
                vent_vitesse_kmh, vent_rafales_kmh, vent_direction_deg,
                precipitation_mm,
                pression_hpa, uv_index, couverture_nuageuse_pct,
                visibilite_m, vpd_kpa
            )
            VALUES (
                %(seance_id)s,
                %(temperature_c)s, %(temperature_ressentie_c)s,
                %(humidite_pct)s, %(point_de_rosee_c)s,
                %(vent_vitesse_kmh)s, %(vent_rafales_kmh)s, %(vent_direction_deg)s,
                %(precipitation_mm)s,
                %(pression_hpa)s, %(uv_index)s, %(couverture_nuageuse_pct)s,
                %(visibilite_m)s, %(vpd_kpa)s
            )
            ON CONFLICT (seance_id) DO UPDATE SET
                temperature_c            = EXCLUDED.temperature_c,
                temperature_ressentie_c  = EXCLUDED.temperature_ressentie_c,
                humidite_pct             = EXCLUDED.humidite_pct,
                vent_vitesse_kmh         = EXCLUDED.vent_vitesse_kmh,
                vent_rafales_kmh         = EXCLUDED.vent_rafales_kmh,
                vent_direction_deg       = EXCLUDED.vent_direction_deg,
                precipitation_mm         = EXCLUDED.precipitation_mm,
                pression_hpa             = EXCLUDED.pression_hpa,
                uv_index                 = EXCLUDED.uv_index
            """,
            {**meteo, "seance_id": seance_id},
        )
    conn.commit()
    log.info("Météo insérée/mise à jour pour séance_id=%d", seance_id)


# ── Point d'entrée ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingestion météo Open-Meteo → PostgreSQL")
    parser.add_argument("--seance", required=True, type=int, help="Numéro de séance (ex: 1)")
    args = parser.parse_args()

    # Connexion PostgreSQL
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log.info("Connexion PostgreSQL OK")
    except psycopg2.OperationalError as e:
        log.error("Connexion PostgreSQL échouée : %s", e)
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            seance = get_seance(cur, args.seance)

        if not seance:
            log.error("Séance %d introuvable en base — lancez d'abord ingest_csv.py", args.seance)
            sys.exit(1)

        seance_id, date_seance, heure_debut, lat, lon = seance
        log.info("=== Météo séance %d : %s %s (%s, %s) ===",
                 args.seance, date_seance, heure_debut, lat, lon)

        # Appel Open-Meteo
        meteo = fetch_meteo(
            lat=float(lat),
            lon=float(lon),
            date=str(date_seance),
            heure=str(heure_debut) if heure_debut else "17:00:00",
        )

        # Insertion
        insert_meteo(seance_id, meteo, conn)
        log.info("=== Ingestion météo terminée pour séance %d ===", args.seance)

    except requests.RequestException as e:
        log.error("Erreur API Open-Meteo : %s", e)
        sys.exit(1)
    except Exception as e:
        log.error("Erreur inattendue : %s", e)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()