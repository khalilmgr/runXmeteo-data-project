"""
fetch_garmin.py
───────────────
Se connecte à Garmin Connect et exporte les activités
d'une séance en CSV prêt à être ingéré par ingest_csv.py.

Usage :
    python scripts/fetch_garmin.py --seance 2
"""

import argparse
import os
import sys
import csv
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv(Path(__file__).parent.parent / ".env")

# Noms des coureurs tels qu'ils apparaissent dans les titres Garmin
COUREURS = ["Adrien", "Nathan", "Khalil", "Arthur"]

# Correspondance numéro de séance → date approximative pour filtrer
DATES_SEANCES = {
    1: "2026-03-12",
    2: None,  # sera détecté automatiquement
    3: None,
    4: None,
}


def connect_garmin() -> Garmin:
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    if not email or not password:
        print("GARMIN_EMAIL ou GARMIN_PASSWORD manquant dans .env")
        sys.exit(1)
    client = Garmin(email, password)
    client.login()
    print(f"Connecté à Garmin Connect : {email}")
    return client


def fetch_activities(client: Garmin, days_back: int = 60) -> list[dict]:
    start = (datetime.today() - timedelta(days=days_back)).date().isoformat()
    end = datetime.today().date().isoformat()
    activities = client.get_activities_by_date(start, end)
    print(f"{len(activities)} activité(s) récupérée(s) depuis {start}")
    return activities


def filter_seance(activities: list[dict], seance_num: int) -> list[dict]:
    """
    Filtre les activités qui correspondent à la séance demandée.
    Cherche les activités dont le titre contient un nom de coureur + '400m'
    et qui sont proches dans le temps (même journée).
    """
    # Filtrer par type course à pied
    courses = [a for a in activities if "running" in a.get("activityType", {}).get("typeKey", "").lower()]

    # Filtrer par titre contenant un nom de coureur
    seance_acts = [
        a for a in courses
        if any(c.lower() in a.get("activityName", "").lower() for c in COUREURS)
        and "400" in a.get("activityName", "")
    ]

    if not seance_acts:
        print("Aucune activité de séance trouvée. Vérifiez les titres dans Garmin Connect.")
        print("Titres disponibles :", [a.get("activityName") for a in courses[:10]])
        return []

    # Grouper par date et prendre le groupe le plus récent si séance non datée
    from collections import defaultdict
    par_date = defaultdict(list)
    for a in seance_acts:
        date = a.get("startTimeLocal", "")[:10]
        par_date[date].append(a)

    dates_triees = sorted(par_date.keys(), reverse=True)
    print(f"Dates de séances détectées : {dates_triees}")

    # Séance 1 = la plus ancienne, séance N = la N-ième
    if seance_num <= len(dates_triees):
        date_cible = dates_triees[seance_num - 1]  # index inversé : séance 1 = dernière entrée
        # En réalité on veut séance 1 = la première, séance 2 = la deuxième
        date_cible = sorted(par_date.keys())[seance_num - 1]
    else:
        print(f"Séance {seance_num} introuvable — seulement {len(dates_triees)} séance(s) détectée(s)")
        return []

    print(f"Séance {seance_num} → date : {date_cible}")
    return par_date[date_cible]


def activity_to_row(a: dict) -> dict:
    """Convertit une activité Garmin en ligne CSV au format Seance1.csv."""

    def fmt_duration(seconds):
        if seconds is None:
            return ""
        h = int(seconds) // 3600
        m = (int(seconds) % 3600) // 60
        s = int(seconds) % 60
        return f"{h:02d}:{m:02d}:{s:02d}.0"

    def fmt_pace(speed_ms):
        """Vitesse m/s → allure MM:SS/km"""
        if not speed_ms or speed_ms == 0:
            return "--"
        pace_s = 1000 / speed_ms
        m = int(pace_s) // 60
        s = int(pace_s) % 60
        return f"{m}:{s:02d}"

    avg_speed = a.get("averageSpeed", 0)
    max_speed = a.get("maxSpeed", 0)

    return {
        "Type d'activité":                     "Course à pied",
        "Date":                                 a.get("startTimeLocal", ""),
        "Favori":                               "false",
        "Titre":                                a.get("activityName", ""),
        "Distance":                             round(a.get("distance", 0) / 1000, 2),
        "Calories":                             a.get("calories", ""),
        "Durée":                                fmt_duration(a.get("duration")),
        "Fréquence cardiaque moyenne":          a.get("averageHR", ""),
        "Fréquence cardiaque maximale":         a.get("maxHR", ""),
        "TE aérobie":                           a.get("aerobicTrainingEffect", ""),
        "Cadence de course moyenne":            a.get("averageRunningCadenceInStepsPerMinute", ""),
        "Cadence de course maximale":           a.get("maxRunningCadenceInStepsPerMinute", ""),
        "Allure moyenne":                       fmt_pace(avg_speed),
        "Meilleure allure":                     fmt_pace(max_speed),
        "Ascension totale":                     a.get("elevationGain", ""),
        "Descente totale":                      a.get("elevationLoss", ""),
        "Longueur moyenne des foulées":         round(a.get("avgStrideLength", 0), 2) if a.get("avgStrideLength") else "",
        "GAP moyenne":                          "--",
        "Normalized Power® (NP®)":             a.get("normPower", ""),
        "Training Stress Score® (TSS®)":       a.get("trainingStressScore", ""),
        "Puissance moyenne":                    a.get("avgPower", ""),
        "Puissance max.":                       a.get("maxPower", ""),
        "Pas":                                  a.get("steps", ""),
        "Nombre de tours":                      a.get("lapCount", ""),
        "Temps du meilleur circuit":            "",
        "Temps de déplacement":                 fmt_duration(a.get("movingDuration")),
        "Temps écoulé":                         fmt_duration(a.get("duration")),
        "Altitude minimale":                    a.get("minElevation", ""),
        "Altitude maximale":                    a.get("maxElevation", ""),
    }


def export_csv(activities: list[dict], seance_num: int) -> Path:
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"Seance{seance_num}.csv"

    rows = [activity_to_row(a) for a in activities]
    fieldnames = list(rows[0].keys())

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV exporté : {output_path} ({len(rows)} activité(s))")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Export Garmin → CSV")
    parser.add_argument("--seance", required=True, type=int, help="Numéro de séance (ex: 2)")
    parser.add_argument("--days", default=90, type=int, help="Nombre de jours à remonter (défaut: 90)")
    args = parser.parse_args()

    client = connect_garmin()
    activities = fetch_activities(client, days_back=args.days)
    seance_acts = filter_seance(activities, args.seance)

    if not seance_acts:
        sys.exit(1)

    print(f"\nActivités trouvées pour séance {args.seance} :")
    for a in seance_acts:
        print(f"  - {a.get('activityName')} | {a.get('startTimeLocal')} | {round(a.get('distance', 0)/1000, 2)} km")

    export_csv(seance_acts, args.seance)


if __name__ == "__main__":
    main()