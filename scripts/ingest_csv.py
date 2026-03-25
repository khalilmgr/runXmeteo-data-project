"""
ingest_csv.py
─────────────
Lit un fichier CSV Garmin exporté et insère les données
dans la base PostgreSQL (tables seances + activites).

Usage :
    python ingest_csv.py --csv ../data/Seance1.csv --seance 1
    python ingest_csv.py --csv ../data/Seance2.csv --seance 2 --date 2026-04-10 --heure 18:00
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

# ── Config logging ─────────────────────────────────────────────────────────────
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

# ── Helpers de conversion ──────────────────────────────────────────────────────

def duration_to_seconds(value: str) -> int | None:
    """'00:07:23.2' ou '00:06:12' → secondes (int)"""
    s = str(value).strip()
    # Supprime les millisecondes
    s = re.sub(r"\.\d+$", "", s)
    parts = s.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def pace_to_seconds(value: str) -> int | None:
    """'5:57' → 357 secondes/km"""
    s = str(value).strip()
    if s in ("--", "", "nan"):
        return None
    parts = s.split(":")
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None


def clean_int(value) -> int | None:
    """'1,116' → 1116"""
    try:
        return int(str(value).replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def clean_float(value) -> float | None:
    try:
        v = str(value).strip()
        if v in ("--", "", "nan"):
            return None
        return float(v.replace(",", "."))
    except (ValueError, TypeError):
        return None


COUREURS_CONNUS = ["Adrien", "Nathan", "Khalil", "Arthur"]


def extract_coureur(titre: str) -> str | None:
    """
    Extrait le nom du coureur depuis le titre Garmin.
    Exemples : 'Adrien400m' → 'Adrien' | 'Arthur400m_s2' → 'Arthur'
    Retourne None si le titre ne correspond pas à une activité de séance.
    """
    titre = str(titre).strip()
    for nom in COUREURS_CONNUS:
        if nom.lower() in titre.lower():
            return nom
    return None


def col(row, *noms):
    """Retourne la première valeur non nulle parmi plusieurs noms de colonnes possibles."""
    for nom in noms:
        val = row.get(nom)
        if val is not None and str(val).strip() not in ("--", "", "nan"):
            return val
    return None


# ── Chargement et parsing du CSV ───────────────────────────────────────────────

def parse_csv(csv_path: Path) -> list[dict]:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # Filtrer uniquement les courses à pied des coureurs connus
    df = df[df["Type d'activité"].str.lower().str.contains("course", na=False)]

    rows = []
    for _, row in df.iterrows():
        coureur = extract_coureur(row.get("Titre", ""))
        if not coureur:
            log.info("Ligne ignorée (pas une activité de séance) : %s", row.get("Titre"))
            continue

        # Allure : Garmin utilise "Allure moyenne" ou "Vitesse moyenne" selon l'export
        record = {
            "coureur_nom":              coureur,
            "garmin_titre":             str(row.get("Titre", "")).strip(),
            "garmin_date":              str(row.get("Date", "")).strip(),

            "distance_km":              clean_float(row.get("Distance")),
            "duree_secondes":           duration_to_seconds(row.get("Durée", "")),
            "calories":                 clean_int(row.get("Calories")),
            "nombre_pas":               clean_int(row.get("Pas")),
            "nombre_tours":             clean_int(row.get("Nombre de tours")),

            # Allure : deux noms de colonnes possibles selon le type d'export Garmin
            "allure_moyenne_s":         pace_to_seconds(col(row, "Allure moyenne", "Vitesse moyenne")),
            "meilleure_allure_s":       pace_to_seconds(col(row, "Meilleure allure", "Vitesse max")),
            "gap_moyenne_s":            pace_to_seconds(row.get("GAP moyenne", "")),

            "fc_moyenne":               clean_int(row.get("Fréquence cardiaque moyenne")),
            "fc_maximale":              clean_int(row.get("Fréquence cardiaque maximale")),

            # Cadence : "Cadence de course" ou "Cadence de vélo" selon l'export
            "cadence_moyenne":          clean_int(col(row, "Cadence de course moyenne", "Cadence de vélo moyenne")),
            "cadence_maximale":         clean_int(col(row, "Cadence de course maximale", "Cadence de vélo maximale")),

            "foulee_moyenne_m":         clean_float(row.get("Longueur moyenne des foulées")),

            "puissance_moyenne_w":      clean_int(row.get("Puissance moyenne")),
            "puissance_max_w":          clean_int(row.get("Puissance max.")),
            "normalized_power_w":       clean_int(row.get("Normalized Power® (NP®)")),
            "tss":                      clean_float(row.get("Training Stress Score® (TSS®)")),

            "ascension_totale_m":       clean_int(row.get("Ascension totale")),
            "descente_totale_m":        clean_int(row.get("Descente totale")),
            "altitude_min_m":           clean_int(row.get("Altitude minimale")),
            "altitude_max_m":           clean_int(row.get("Altitude maximale")),

            "te_aerobie":               clean_float(row.get("TE aérobie")),

            "temps_deplacement_s":      duration_to_seconds(row.get("Temps de déplacement", "")),
            "temps_ecoule_s":           duration_to_seconds(row.get("Temps écoulé", "")),
            "temps_meilleur_circuit_s": duration_to_seconds(row.get("Temps du meilleur circuit", "")),
        }
        rows.append(record)
        log.info("Parsé : %s — allure %s s/km, FC moy %s bpm",
                 coureur, record["allure_moyenne_s"], record["fc_moyenne"])

    return rows


# ── Insertion en base ──────────────────────────────────────────────────────────

def get_or_create_seance(cur, numero: int, date: str | None, heure: str | None) -> int:
    cur.execute("SELECT id FROM seances WHERE numero = %s", (numero,))
    result = cur.fetchone()
    if result:
        log.info("Séance %d déjà en base (id=%d)", numero, result[0])
        return result[0]

    cur.execute(
        """
        INSERT INTO seances (numero, date_seance, heure_debut)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (numero, date, heure),
    )
    seance_id = cur.fetchone()[0]
    log.info("Séance %d créée (id=%d)", numero, seance_id)
    return seance_id


def get_coureur_id(cur, nom: str) -> int | None:
    cur.execute("SELECT id FROM coureurs WHERE nom = %s", (nom,))
    result = cur.fetchone()
    if not result:
        log.error("Coureur '%s' introuvable en base — vérifiez le nom dans le CSV", nom)
        return None
    return result[0]


def insert_activites(records: list[dict], seance_id: int, conn) -> int:
    inserted = 0
    with conn.cursor() as cur:
        for rec in records:
            coureur_id = get_coureur_id(cur, rec["coureur_nom"])
            if coureur_id is None:
                continue

            cur.execute(
                """
                INSERT INTO activites (
                    coureur_id, seance_id,
                    garmin_titre, garmin_date,
                    distance_km, duree_secondes, calories, nombre_pas, nombre_tours,
                    allure_moyenne_s, meilleure_allure_s, gap_moyenne_s,
                    fc_moyenne, fc_maximale,
                    cadence_moyenne, cadence_maximale,
                    foulee_moyenne_m,
                    puissance_moyenne_w, puissance_max_w, normalized_power_w, tss,
                    ascension_totale_m, descente_totale_m, altitude_min_m, altitude_max_m,
                    te_aerobie,
                    temps_deplacement_s, temps_ecoule_s, temps_meilleur_circuit_s
                )
                VALUES (
                    %(coureur_id)s, %(seance_id)s,
                    %(garmin_titre)s, %(garmin_date)s,
                    %(distance_km)s, %(duree_secondes)s, %(calories)s, %(nombre_pas)s, %(nombre_tours)s,
                    %(allure_moyenne_s)s, %(meilleure_allure_s)s, %(gap_moyenne_s)s,
                    %(fc_moyenne)s, %(fc_maximale)s,
                    %(cadence_moyenne)s, %(cadence_maximale)s,
                    %(foulee_moyenne_m)s,
                    %(puissance_moyenne_w)s, %(puissance_max_w)s, %(normalized_power_w)s, %(tss)s,
                    %(ascension_totale_m)s, %(descente_totale_m)s, %(altitude_min_m)s, %(altitude_max_m)s,
                    %(te_aerobie)s,
                    %(temps_deplacement_s)s, %(temps_ecoule_s)s, %(temps_meilleur_circuit_s)s
                )
                ON CONFLICT (coureur_id, seance_id) DO UPDATE SET
                    distance_km          = EXCLUDED.distance_km,
                    duree_secondes       = EXCLUDED.duree_secondes,
                    allure_moyenne_s     = EXCLUDED.allure_moyenne_s,
                    meilleure_allure_s   = EXCLUDED.meilleure_allure_s,
                    fc_moyenne           = EXCLUDED.fc_moyenne,
                    fc_maximale          = EXCLUDED.fc_maximale,
                    cadence_moyenne      = EXCLUDED.cadence_moyenne,
                    foulee_moyenne_m     = EXCLUDED.foulee_moyenne_m,
                    puissance_moyenne_w  = EXCLUDED.puissance_moyenne_w
                """,
                {**rec, "coureur_id": coureur_id, "seance_id": seance_id},
            )
            inserted += 1
            log.info("Inséré/mis à jour : %s (séance %d)", rec["coureur_nom"], seance_id)

    conn.commit()
    return inserted


# ── Point d'entrée ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingestion CSV Garmin → PostgreSQL")
    parser.add_argument("--csv",     required=True, help="Chemin vers le fichier CSV")
    parser.add_argument("--seance",  required=True, type=int, help="Numéro de séance (ex: 1)")
    parser.add_argument("--date",    default=None, help="Date de la séance (YYYY-MM-DD)")
    parser.add_argument("--heure",   default=None, help="Heure de début (HH:MM)")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        log.error("Fichier CSV introuvable : %s", csv_path)
        sys.exit(1)

    # Création du dossier logs si nécessaire
    (Path(__file__).parent.parent / "logs").mkdir(exist_ok=True)

    log.info("=== Début ingestion : %s (séance %d) ===", csv_path.name, args.seance)

    # Parsing
    records = parse_csv(csv_path)
    if not records:
        log.error("Aucune donnée parsée — vérifiez le CSV")
        sys.exit(1)

    # Connexion PostgreSQL
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log.info("Connexion PostgreSQL OK (%s@%s/%s)", DB_CONFIG["user"], DB_CONFIG["host"], DB_CONFIG["dbname"])
    except psycopg2.OperationalError as e:
        log.error("Connexion PostgreSQL échouée : %s", e)
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            seance_id = get_or_create_seance(cur, args.seance, args.date, args.heure)
            conn.commit()

        nb = insert_activites(records, seance_id, conn)
        log.info("=== Ingestion terminée : %d activité(s) insérée(s) ===", nb)

    except Exception as e:
        log.error("Erreur pendant l'ingestion : %s", e)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()