-- ============================================================
--  SAÉ Data Pipeline — Schéma PostgreSQL
--  BUT Informatique 2A · IUT Reims-Châlons-Charleville
--  2025-2026
-- ============================================================

-- ── Extension utile pour les UUIDs (optionnel) ──────────────
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Nettoyage (ordre inverse des dépendances) ───────────────
DROP TABLE IF EXISTS meteo CASCADE;
DROP TABLE IF EXISTS activites CASCADE;
DROP TABLE IF EXISTS seances CASCADE;
DROP TABLE IF EXISTS coureurs CASCADE;

-- ============================================================
--  TABLE : coureurs
--  Un enregistrement par athlète participant au projet
-- ============================================================
CREATE TABLE coureurs (
    id          SERIAL PRIMARY KEY,
    nom         VARCHAR(50)  NOT NULL UNIQUE,
    prenom      VARCHAR(50),
    created_at  TIMESTAMP    DEFAULT NOW()
);

-- Données initiales
INSERT INTO coureurs (nom) VALUES
    ('Adrien'),
    ('Nathan'),
    ('Khalil'),
    ('Arthur');

-- ============================================================
--  TABLE : seances
--  Une séance = un créneau commun aux 4 coureurs
-- ============================================================
CREATE TABLE seances (
    id              SERIAL PRIMARY KEY,
    numero          SMALLINT     NOT NULL UNIQUE,   -- 1, 2, 3…
    date_seance     DATE         NOT NULL,
    heure_debut     TIME,
    lieu            VARCHAR(100) DEFAULT 'Parc de Champagne, Reims',
    latitude        NUMERIC(9,6) DEFAULT 49.240841,  -- coordonnées GPS Parc de Champagne
    longitude       NUMERIC(9,6) DEFAULT 4.054274,
    description     TEXT,
    created_at      TIMESTAMP    DEFAULT NOW()
);

-- Séance 1 déjà réalisée
INSERT INTO seances (numero, date_seance, heure_debut, description) VALUES
    (1, '2026-03-12', '17:30:00', 'Baseline commune — 3×400m, même parcours, même heure');

-- ============================================================
--  TABLE : activites
--  Métriques Garmin d'un coureur pour une séance donnée
-- ============================================================
CREATE TABLE activites (
    id                      SERIAL PRIMARY KEY,
    coureur_id              INT          NOT NULL REFERENCES coureurs(id) ON DELETE CASCADE,
    seance_id               INT          NOT NULL REFERENCES seances(id)  ON DELETE CASCADE,

    -- Identification
    garmin_titre            VARCHAR(100),
    garmin_date             TIMESTAMP,

    -- Volume
    distance_km             NUMERIC(6,3),
    duree_secondes          INT,
    calories                INT,
    nombre_pas              INT,
    nombre_tours            INT,

    -- Allure (stockée en secondes/km pour les calculs)
    allure_moyenne_s        INT,          -- ex: 357 pour 5:57/km
    meilleure_allure_s      INT,          -- ex: 207 pour 3:27/km
    gap_moyenne_s           INT,          -- Grade Adjusted Pace

    -- Fréquence cardiaque
    fc_moyenne              SMALLINT,
    fc_maximale             SMALLINT,

    -- Cadence
    cadence_moyenne         SMALLINT,     -- pas/min
    cadence_maximale        SMALLINT,

    -- Foulée
    foulee_moyenne_m        NUMERIC(4,2), -- en mètres

    -- Puissance
    puissance_moyenne_w     SMALLINT,
    puissance_max_w         SMALLINT,
    normalized_power_w      SMALLINT,
    tss                     NUMERIC(6,2),

    -- Dénivelé
    ascension_totale_m      SMALLINT,
    descente_totale_m       SMALLINT,
    altitude_min_m          SMALLINT,
    altitude_max_m          SMALLINT,

    -- Effort
    te_aerobie              NUMERIC(3,1), -- Training Effect aérobie (0.0–5.0)

    -- Temps
    temps_deplacement_s     INT,
    temps_ecoule_s          INT,
    temps_meilleur_circuit_s INT,

    -- Contrainte d'unicité : 1 activité par coureur par séance
    UNIQUE (coureur_id, seance_id),

    created_at              TIMESTAMP    DEFAULT NOW()
);

-- ============================================================
--  TABLE : meteo
--  Données Open-Meteo pour une séance (1 ligne par séance)
-- ============================================================
CREATE TABLE meteo (
    id                      SERIAL PRIMARY KEY,
    seance_id               INT          NOT NULL REFERENCES seances(id) ON DELETE CASCADE UNIQUE,

    -- Température
    temperature_c           NUMERIC(5,2),          -- °C à 2m
    temperature_ressentie_c NUMERIC(5,2),          -- apparent temperature

    -- Humidité
    humidite_pct            SMALLINT,              -- % humidité relative
    point_de_rosee_c        NUMERIC(5,2),

    -- Vent
    vent_vitesse_kmh        NUMERIC(6,2),          -- à 10m
    vent_rafales_kmh        NUMERIC(6,2),
    vent_direction_deg      SMALLINT,              -- 0–360°

    -- Précipitations
    precipitation_mm        NUMERIC(5,2),

    -- Pression & rayonnement
    pression_hpa            NUMERIC(7,2),
    uv_index                NUMERIC(4,2),
    couverture_nuageuse_pct SMALLINT,

    -- Visibilité & confort
    visibilite_m            INT,
    vpd_kpa                 NUMERIC(5,3),          -- Vapour Pressure Deficit

    -- Métadonnées
    source                  VARCHAR(50)  DEFAULT 'open-meteo',
    recupere_le             TIMESTAMP    DEFAULT NOW(),

    created_at              TIMESTAMP    DEFAULT NOW()
);

-- ============================================================
--  TABLE : conditions_coureur
--  Contexte physiologique de chaque coureur pour une séance
--  Saisie manuelle avant/après chaque séance
-- ============================================================
DROP TABLE IF EXISTS conditions_coureur CASCADE;

CREATE TABLE conditions_coureur (
    id              SERIAL PRIMARY KEY,
    coureur_id      INT          NOT NULL REFERENCES coureurs(id) ON DELETE CASCADE,
    seance_id       INT          NOT NULL REFERENCES seances(id)  ON DELETE CASCADE,

    a_jeun          BOOLEAN,                          -- à jeun au moment de la course
    heures_sommeil  NUMERIC(4,1),                     -- heures de sommeil la nuit précédente
    etat_general    SMALLINT CHECK (etat_general BETWEEN 1 AND 5), -- 1=très mauvais 5=excellent
    courbatures     BOOLEAN      DEFAULT FALSE,        -- courbatures / douleurs légères
    dernier_repas_h NUMERIC(4,1),                     -- heures depuis le dernier repas
    notes           TEXT,                             -- remarques libres (stress, blessure...)

    UNIQUE (coureur_id, seance_id),
    created_at      TIMESTAMP    DEFAULT NOW()
);

-- ============================================================
--  VUE : performances_avec_meteo
--  Croisement activités + météo + conditions — base des visu
-- ============================================================
CREATE OR REPLACE VIEW performances_avec_meteo AS
SELECT
    c.nom                           AS coureur,
    s.numero                        AS seance,
    s.date_seance,
    s.heure_debut,
    s.lieu,

    -- Allure lisible (reconvertie depuis secondes)
    TO_CHAR((a.allure_moyenne_s || ' seconds')::INTERVAL, 'MI:SS') || '/km'
                                    AS allure_moyenne,
    TO_CHAR((a.meilleure_allure_s || ' seconds')::INTERVAL, 'MI:SS') || '/km'
                                    AS meilleure_allure,
    a.allure_moyenne_s,
    a.meilleure_allure_s,

    a.distance_km,
    a.duree_secondes,
    a.fc_moyenne,
    a.fc_maximale,
    a.cadence_moyenne,
    a.foulee_moyenne_m,
    a.puissance_moyenne_w,
    a.te_aerobie,
    a.calories,

    -- Météo
    m.temperature_c,
    m.temperature_ressentie_c,
    m.humidite_pct,
    m.vent_vitesse_kmh,
    m.vent_direction_deg,
    m.precipitation_mm,
    m.pression_hpa,
    m.uv_index,

    -- Conditions physiologiques
    cc.a_jeun,
    cc.heures_sommeil,
    cc.etat_general,
    cc.courbatures,
    cc.dernier_repas_h,
    cc.notes

FROM activites a
JOIN coureurs c  ON c.id  = a.coureur_id
JOIN seances  s  ON s.id  = a.seance_id
LEFT JOIN meteo            m  ON m.seance_id  = a.seance_id
LEFT JOIN conditions_coureur cc ON cc.coureur_id = a.coureur_id
                                AND cc.seance_id  = a.seance_id
ORDER BY s.numero, a.allure_moyenne_s;