"""
extract_tour2.py
────────────────
Extrait automatiquement les métriques du Tour 2 (effort maximal)
depuis les fichiers CSV second-par-second exportés depuis les FIT Garmin.

Convention de nommage attendue : {Coureur}_s{N}.csv (ex: Khalil_s4.csv)
Dossier d'entrée : data/fit/
Dossier de sortie : data/fit/tour2_results.csv

Usage :
    python extract_tour2.py                         # traite tous les fichiers dans data/fit/
    python extract_tour2.py --file data/fit/Khalil_s4.csv
    python extract_tour2.py --seance 4              # traite uniquement la séance 4
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

# ── Paramètres de détection ────────────────────────────────────────────────────

# Fraction du pic de vitesse utilisée comme seuil de détection du Tour 2.
# 0.75 = 75% de la vitesse de pointe.
# Ex: Arthur pic 7.4 m/s → seuil 5.5 m/s | Khalil pic 5.1 m/s → seuil 3.8 m/s
SEUIL_RELATIF = 0.75

# Durée minimale du Tour 2 (secondes) — évite de capturer une accélération courte
DUREE_MIN_TOUR2 = 45

# Durée maximale du Tour 2 (secondes) — un 400m ne prend pas plus de 3 min
DUREE_MAX_TOUR2 = 200

# Cadence Garmin = foulées/min pour chaque pied → multiplier par 2 pour pas/min total
CADENCE_FACTOR = 2

# Coureurs connus et leurs poids (pour correction calories si besoin)
COUREURS_CONNUS = ["Adrien", "Nathan", "Khalil", "Arthur"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_nom_fichier(path: Path) -> tuple[str | None, int | None]:
    """
    'Khalil_s4.csv' → ('Khalil', 4)
    'Nathans4.csv'  → ('Nathan', 4)
    """
    stem = path.stem  # sans extension
    # Cherche un coureur connu dans le nom (insensible à la casse)
    coureur = None
    for nom in COUREURS_CONNUS:
        if nom.lower() in stem.lower():
            coureur = nom
            break

    # Cherche le numéro de séance
    m = re.search(r"s(\d+)", stem, re.IGNORECASE)
    seance = int(m.group(1)) if m else None

    return coureur, seance


def col(df: pd.DataFrame, *candidates: str) -> str | None:
    """Retourne le premier nom de colonne présent dans df parmi les candidats."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def pace_str(seconds_per_km: float) -> str:
    """357.3 → '5:57/km'"""
    m = int(seconds_per_km // 60)
    s = int(seconds_per_km % 60)
    return f"{m}:{s:02d}/km"


# ── Extraction du Tour 2 ───────────────────────────────────────────────────────

def extraire_tour2(path: Path, coureur: str, seance: int) -> dict | None:
    """
    Charge un CSV FIT second-par-second et extrait les métriques du Tour 2.
    Retourne un dict ou None en cas d'échec.
    """
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"  [ERREUR] Impossible de lire {path.name} : {e}")
        return None

    df.columns = df.columns.str.strip().str.lower()

    # ── Normalisation du format français (virgules décimales → points) ─────────
    # Les exports Garmin en locale française utilisent "7,362" au lieu de "7.362"
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].str.replace(",", ".", regex=False)

    # ── Colonne vitesse ────────────────────────────────────────────────────────
    col_speed = col(df, "enhanced_speed", "speed")
    if col_speed is None:
        print(f"  [ERREUR] Colonne vitesse introuvable dans {path.name} — colonnes : {list(df.columns)}")
        return None

    df["vitesse"] = pd.to_numeric(df[col_speed], errors="coerce")

    # ── Colonne timestamp ──────────────────────────────────────────────────────
    col_ts = col(df, "timestamp", "time", "datetime")
    if col_ts:
        # Tente plusieurs formats : ISO, DD/MM/YYYY HH:MM:SS, etc.
        df["ts"] = pd.to_datetime(df[col_ts], dayfirst=True, errors="coerce")
    else:
        # Fallback : index en secondes
        df["ts"] = pd.to_datetime("2000-01-01") + pd.to_timedelta(df.index, unit="s")

    df = df.dropna(subset=["vitesse", "ts"]).reset_index(drop=True)

    # ── Colonne distance ───────────────────────────────────────────────────────
    col_dist = col(df, "distance")
    if col_dist:
        df["distance"] = pd.to_numeric(df[col_dist], errors="coerce")
    else:
        df["distance"] = None

    # ── Autres métriques ───────────────────────────────────────────────────────
    col_hr      = col(df, "heart_rate")
    col_cadence = col(df, "cadence")
    col_power   = col(df, "power")

    # ── Lissage de la vitesse (fenêtre glissante 5 s) ─────────────────────────
    df["vitesse_lisse"] = df["vitesse"].rolling(window=5, center=True, min_periods=1).mean()

    # ── Détection du pic de vitesse = centre du Tour 2 ────────────────────────
    idx_pic = df["vitesse_lisse"].idxmax()
    vitesse_pic = df.at[idx_pic, "vitesse_lisse"]

    # Seuil adaptatif : 75 % du pic (s'ajuste à chaque coureur)
    seuil = vitesse_pic * SEUIL_RELATIF

    # Expansion : cherche le début (speed < seuil avant le pic)
    idx_debut = 0
    for i in range(idx_pic, -1, -1):
        if df.at[i, "vitesse_lisse"] < seuil:
            idx_debut = i + 1
            break

    # Expansion : cherche la fin (speed < seuil après le pic)
    idx_fin = len(df) - 1
    for i in range(idx_pic, len(df)):
        if df.at[i, "vitesse_lisse"] < seuil:
            idx_fin = i - 1
            break

    segment = df.iloc[idx_debut : idx_fin + 1].copy()

    # ── Validation de la durée ─────────────────────────────────────────────────
    duree_s = (segment["ts"].iloc[-1] - segment["ts"].iloc[0]).total_seconds()

    if duree_s < DUREE_MIN_TOUR2:
        print(f"  [WARN] {path.name} : segment détecté trop court ({duree_s:.0f}s)")
    if duree_s > DUREE_MAX_TOUR2:
        print(f"  [WARN] {path.name} : segment long ({duree_s:.0f}s) — normal si coureur très rapide en Tour 1")

    # ── Calcul des métriques ──────────────────────────────────────────────────
    vitesse_moy = segment["vitesse"].mean()          # m/s
    vitesse_pic = segment["vitesse"].max()           # m/s

    # Allure (s/km) = 1000 / vitesse_moy
    allure_s_km  = 1000 / vitesse_moy if vitesse_moy > 0 else None
    allure_pic_s = 1000 / vitesse_pic if vitesse_pic > 0 else None

    # Distance (si disponible, sinon estimée depuis vitesse × durée)
    if col_dist and segment["distance"].notna().any():
        dist_debut = segment["distance"].dropna().iloc[0]
        dist_fin   = segment["distance"].dropna().iloc[-1]
        distance_m = abs(dist_fin - dist_debut)
    else:
        distance_m = vitesse_moy * duree_s

    fc_moy  = segment[col_hr].mean()  if col_hr      else None
    fc_max  = segment[col_hr].max()   if col_hr      else None
    cad_moy = segment[col_cadence].mean() * CADENCE_FACTOR if col_cadence else None
    pow_moy = segment[col_power].mean()   if col_power     else None

    result = {
        "coureur":        coureur,
        "seance":         seance,
        "tour2_debut":    segment["ts"].iloc[0].strftime("%H:%M:%S"),
        "tour2_fin":      segment["ts"].iloc[-1].strftime("%H:%M:%S"),
        "duree_s":        round(duree_s),
        "distance_m":     round(distance_m, 1),
        "allure_s_km":    round(allure_s_km) if allure_s_km else None,
        "allure_str":     pace_str(allure_s_km) if allure_s_km else None,
        "meilleure_allure_s_km": round(allure_pic_s) if allure_pic_s else None,
        "meilleure_allure_str":  pace_str(allure_pic_s) if allure_pic_s else None,
        "fc_moyenne":     round(fc_moy,  1) if fc_moy  is not None else None,
        "fc_max":         round(fc_max)     if fc_max  is not None else None,
        "cadence_moyenne_spm": round(cad_moy, 1) if cad_moy is not None else None,
        "puissance_moyenne_w": round(pow_moy, 1) if pow_moy is not None else None,
    }

    return result


# ── Affichage ──────────────────────────────────────────────────────────────────

def afficher_tableau(resultats: list[dict]) -> None:
    if not resultats:
        return
    print()
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║                  RÉSULTATS TOUR 2 — EFFORT MAXIMAL                      ║")
    print("╠══════════════╦═══════╦══════════╦══════════╦════════╦═════════╦═════════╣")
    print("║  Coureur     ║ Séan. ║  Allure  ║  Durée   ║ Dist.  ║ FC moy  ║ FC max  ║")
    print("╠══════════════╬═══════╬══════════╬══════════╬════════╬═════════╬═════════╣")
    for r in sorted(resultats, key=lambda x: (x["seance"], x.get("allure_s_km") or 9999)):
        allure  = r.get("allure_str", "N/A")
        duree   = f"{r['duree_s']}s"
        dist    = f"{r['distance_m']:.0f}m"
        fc_moy  = f"{r['fc_moyenne']:.0f}" if r.get("fc_moyenne") else "N/A"
        fc_max  = str(r.get("fc_max", "N/A"))
        print(f"║  {r['coureur']:<12}║  {r['seance']:<5}║ {allure:<8} ║ {duree:<8} ║ {dist:<6} ║ {fc_moy:<7} ║ {fc_max:<7} ║")
    print("╚══════════════╩═══════╩══════════╩══════════╩════════╩═════════╩═════════╝")
    print()


# ── Point d'entrée ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extraction Tour 2 depuis fichiers FIT CSV")
    parser.add_argument("--file",   default=None, help="Fichier FIT CSV spécifique à traiter")
    parser.add_argument("--seance", default=None, type=int, help="Filtrer par numéro de séance")
    parser.add_argument("--output", default=None, help="Chemin CSV de sortie (défaut: data/fit/tour2_results.csv)")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    fit_dir = root / "data" / "fit"
    out_path = Path(args.output) if args.output else fit_dir / "tour2_results.csv"

    # ── Sélection des fichiers à traiter ──────────────────────────────────────
    if args.file:
        fichiers = [Path(args.file)]
    else:
        fichiers = sorted(fit_dir.glob("*.csv"))
        # Exclure le fichier de résultats lui-même
        fichiers = [f for f in fichiers if f.name != "tour2_results.csv"]

    if not fichiers:
        print(f"Aucun fichier FIT CSV trouvé dans {fit_dir}")
        print("Déposez vos fichiers (ex: Khalil_s4.csv) dans data/fit/ et relancez.")
        sys.exit(0)

    resultats = []

    for fpath in fichiers:
        coureur, seance = parse_nom_fichier(fpath)

        if not coureur:
            print(f"[SKIP] {fpath.name} — nom de coureur non reconnu ({COUREURS_CONNUS})")
            continue
        if seance is None:
            print(f"[SKIP] {fpath.name} — numéro de séance introuvable dans le nom")
            continue
        if args.seance and seance != args.seance:
            continue

        print(f"→ Traitement : {fpath.name}  ({coureur}, séance {seance})")
        result = extraire_tour2(fpath, coureur, seance)

        if result:
            fc_info = f" | FC moy {result['fc_moyenne']:.0f} bpm" if result.get('fc_moyenne') else ''
            print(f"  ✓ Tour 2 : {result['tour2_debut']} → {result['tour2_fin']} "
                  f"| {result['allure_str']} | {result['duree_s']}s | {result['distance_m']:.0f}m{fc_info}")
            resultats.append(result)
        else:
            print(f"  ✗ Extraction échouée pour {fpath.name}")

    if not resultats:
        print("Aucun résultat extrait.")
        sys.exit(0)

    # ── Tableau récapitulatif ─────────────────────────────────────────────────
    afficher_tableau(resultats)

    # ── Sauvegarde CSV ────────────────────────────────────────────────────────
    df_out = pd.DataFrame(resultats)
    df_out.to_csv(out_path, index=False)
    print(f"Résultats sauvegardés → {out_path}")


if __name__ == "__main__":
    main()