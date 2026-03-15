"""
pipeline.py
───────────
Script principal déclenché par le cron.

Comportement :
  1. Scanne le dossier data/ à la recherche de nouveaux fichiers CSV
  2. Pour chaque CSV non encore traité :
     a. Détermine le numéro de séance depuis le nom du fichier (ex: Seance2.csv → 2)
     b. Lance l'ingestion CSV → PostgreSQL
     c. Lance l'ingestion météo Open-Meteo → PostgreSQL
     d. Déplace le CSV dans data/processed/ pour ne pas le retraiter
  3. Logue toutes les opérations dans logs/pipeline.log

Usage manuel :
    python scripts/pipeline.py

Via cron (exemple — toutes les heures) :
    0 * * * * /chemin/vers/venv/bin/python /chemin/vers/scripts/pipeline.py
"""

import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ── Chemins ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / "data"
PROCESSED   = ROOT / "data" / "processed"
LOGS_DIR    = ROOT / "logs"
PYTHON      = sys.executable  # pointe vers le venv actif

# ── Config logging ─────────────────────────────────────────────────────────────
LOGS_DIR.mkdir(exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

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

def extraire_numero_seance(csv_path: Path) -> int | None:
    """
    Extrait le numéro de séance depuis le nom du fichier.
    Exemples : Seance1.csv → 1 | seance_2.csv → 2 | S3.csv → 3
    """
    match = re.search(r"(\d+)", csv_path.stem)
    return int(match.group(1)) if match else None


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


# ── Pipeline principal ─────────────────────────────────────────────────────────

def traiter_csv(csv_path: Path) -> bool:
    numero = extraire_numero_seance(csv_path)
    if numero is None:
        log.warning("Impossible de déterminer le numéro de séance pour : %s", csv_path.name)
        return False

    log.info("══════════════════════════════════════════")
    log.info("Traitement : %s (séance %d)", csv_path.name, numero)
    log.info("══════════════════════════════════════════")

    # Étape 1 : ingestion CSV
    ok = run_script("ingest_csv.py", ["--csv", str(csv_path), "--seance", str(numero)])
    if not ok:
        log.error("Ingestion CSV échouée — séance %d ignorée", numero)
        return False

    # Étape 2 : ingestion météo
    ok = run_script("ingest_meteo.py", ["--seance", str(numero)])
    if not ok:
        log.warning("Ingestion météo échouée pour séance %d — données course OK", numero)
        # On continue quand même : les données de course sont en base

    # Étape 3 : archivage du CSV
    destination = PROCESSED / csv_path.name
    shutil.move(str(csv_path), str(destination))
    log.info("CSV archivé : %s → data/processed/", csv_path.name)

    return True


def main():
    log.info("=== Démarrage pipeline SAÉ Running ===")

    # Scan des CSV dans data/
    csv_files = sorted(DATA_DIR.glob("*.csv"))

    if not csv_files:
        log.info("Aucun nouveau CSV trouvé dans data/ — rien à faire")
        return

    log.info("%d fichier(s) CSV détecté(s) : %s",
             len(csv_files), [f.name for f in csv_files])

    resultats = {"ok": 0, "erreur": 0}

    for csv_path in csv_files:
        succes = traiter_csv(csv_path)
        if succes:
            resultats["ok"] += 1
        else:
            resultats["erreur"] += 1

    log.info("=== Pipeline terminé : %d OK, %d erreur(s) ===",
             resultats["ok"], resultats["erreur"])


if __name__ == "__main__":
    main()