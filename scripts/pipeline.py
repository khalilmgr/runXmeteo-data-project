"""
pipeline.py
───────────
Script principal déclenché par le cron.

Comportement :
  1. Lance l'ingestion Tour 2 (data/fit/tour2_results.csv) vers PostgreSQL
  2. Lance l'ingestion météo Open-Meteo pour chaque séance présente dans tour2_results.csv
  3. Logue toutes les opérations dans logs/pipeline.log

Usage manuel :
    python scripts/pipeline.py

Via cron (exemple — toutes les heures) :
    0 * * * * /chemin/vers/venv/bin/python /chemin/vers/scripts/pipeline.py
"""

import logging
import subprocess
import sys
from pathlib import Path

import pandas as pd

# ── Chemins ────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
LOGS_DIR   = ROOT / "logs"
TOUR2_PATH = ROOT / "data" / "fit" / "tour2_results.csv"
PYTHON     = sys.executable  # pointe vers le venv actif

# ── Config logging ─────────────────────────────────────────────────────────────
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "pipeline.log"),
    ],
)
log = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def run_script(script: str, args: list[str]) -> bool:
    """Lance un script Python et retourne True si succès."""
    cmd = [PYTHON, str(ROOT / "scripts" / script)] + args
    log.info("Lancement : %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        for line in result.stdout.strip().splitlines():
            log.info("  [%s] %s", script, line)
    if result.stderr:
        for line in result.stderr.strip().splitlines():
            log.warning("  [%s] %s", script, line)

    if result.returncode != 0:
        log.error("%s a échoué (code %d)", script, result.returncode)
        return False

    return True


def seances_from_tour2() -> list[int]:
    """Retourne les numéros de séance présents dans tour2_results.csv."""
    if not TOUR2_PATH.exists():
        return []
    df = pd.read_csv(TOUR2_PATH)
    if "seance" not in df.columns:
        return []
    return sorted(df["seance"].dropna().astype(int).unique().tolist())


# ── Pipeline principal ─────────────────────────────────────────────────────────

def main():
    log.info("=== Démarrage pipeline SAÉ Running ===")

    if not TOUR2_PATH.exists():
        log.error("Fichier manquant : %s", TOUR2_PATH)
        log.error("Lancez d'abord : python scripts/extract_tour2.py")
        sys.exit(1)

    log.info("Source Tour 2 : %s", TOUR2_PATH)

    # Étape 1 : ingestion Tour 2
    ok = run_script("ingest_csv.py", [])
    if not ok:
        log.error("Ingestion Tour 2 échouée")
        sys.exit(1)

    # Étape 2 : ingestion météo pour chaque séance présente
    seances = seances_from_tour2()
    if not seances:
        log.warning("Aucune séance détectée dans tour2_results.csv")
        return

    meteo_ok = 0
    meteo_err = 0
    for seance in seances:
        ok = run_script("ingest_meteo.py", ["--seance", str(seance)])
        if ok:
            meteo_ok += 1
        else:
            meteo_err += 1

    log.info("=== Pipeline terminé : Tour2=OK, Météo %d OK / %d erreur(s) ===", meteo_ok, meteo_err)


if __name__ == "__main__":
    main()
