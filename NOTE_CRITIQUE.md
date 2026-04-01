# Note de lecture critique — SAÉ Data Pipeline

**BUT Informatique 2A · Parcours Data**
IUT Reims-Châlons-Charleville · 2025-2026

---

## 1. À quelles questions nos visualisations répondent-elles ?

### Questions auxquelles on peut répondre avec confiance

**"Qui est le plus rapide sur 400m ?"**
Réponse claire : Arthur (meilleur temps ~56s), suivi de Khalil (~1:15), Nathan (~1:13–1:30 selon séance), Adrien (~1:31–1:37). Données FIT fiables, directement mesurées.

**"Y a-t-il une tendance météo / performance visible ?"**
Réponse partielle : la séance 3 (5.3°C, pluie) montre des FC plus basses pour des temps similaires — cohérent avec une dissipation thermique facilitée par le froid. Mais avec seulement 4 points de données par coureur, aucune corrélation statistiquement significative ne peut être établie.

**"Qui récupère le mieux après l'effort ?"**
Visible dans la section 7 (récupération cardiaque) : descente de FC différenciée selon les coureurs. Indicateur de condition physique aérobie.

**"Chaque coureur a-t-il une stratégie de course différente ?"**
Oui, visible dans les sections 12 (splits 100m) et 5 (profil de vitesse) : certains partent fort et ralentissent, d'autres gèrent leur effort.

### Questions auxquelles on ne peut pas répondre de façon fiable

**"Les conditions météo causent-elles les variations de performance ?"**
Non établissable. 4 séances = 4 points. On peut observer des corrélations mais pas inférer de causalité. Un coureur peut performer mieux en S2 pour de nombreuses raisons non mesurées (forme du jour, alimentation, sommeil).

**"Y a-t-il une progression physique réelle ?"**
Difficile à dire. L'amélioration entre S1 et S2 peut s'expliquer par l'apprentissage du parcours plutôt que par une progression physique. Seule la séance 4 (reproductibilité) permettrait de distinguer les deux effets — et encore, les conditions météo différentes S1 vs S4 complexifient l'interprétation.

---

## 2. Qualité et fiabilité des données

### Source Garmin — points forts

- Mesures continues (1 Hz) sur toute l'activité — résolution temporelle excellente
- GPS intégré avec précision ±3-5m — suffisant pour un 400m
- Fréquence cardiaque optique avec ceinture thoracique (plus fiable qu'optique poignet)
- Cadence et puissance calculées en temps réel

### Source Garmin — limites et biais

**Profil unique (Arthur, 70 kg)**
Toutes les activités sont enregistrées sur le compte Garmin d'Arthur. Cela signifie que les métriques dépendantes du profil utilisateur (calories, puissance, TE aérobie, zones FC) sont calculées en référence aux caractéristiques physiques d'Arthur, pas des autres coureurs. Corrections appliquées : calories et puissance normalisées par le poids réel (W/kg, kcal/km). Le TE aérobie reste non corrigeable.

**Métriques CSV moyennées sur 3 tours**
Le CSV exporté depuis Garmin Connect donne une seule ligne par activité, moyennant les 3 tours (échauffement modéré + effort maximal + récupération). Exemple : Adrien S4 affiché à 8:41/km dans le CSV vs 3:53/km réel sur le Tour 2. L'écart de 55% rend le CSV inutilisable pour des comparaisons sérieuses. **Solution adoptée : extraction systématique du Tour 2 depuis les FIT.**

**Heure d'enregistrement différente — Adrien S4**
Adrien a couru la séance 4 à 12h34, soit 3 heures après les autres (09h27-09h50). Les conditions météo n'étaient pas strictement identiques. Pour S4, la météo enregistrée est celle de 9h (groupe principal). La performance d'Adrien en S4 doit donc être comparée avec précaution.

**Détection automatique du Tour 2**
L'algorithme utilise un seuil à 75% du pic de vitesse. Dans les cas normaux, il isole correctement le Tour 2 (validé manuellement sur tous les fichiers). Cas limite identifié : si le Tour 2 ne présente pas de pic de vitesse net (effort mal engagé, problème technique), la détection pourrait être erronée. Vérification recommandée en cas de durée Tour 2 < 45s ou > 200s.

### Source Open-Meteo — points forts

- Données historiques réelles, pas de prévisions interpolées
- Résolution horaire suffisante pour notre usage
- Gratuit, reproductible, sans dépendance à une clé API

### Source Open-Meteo — limites

**Résolution spatiale**
L'API retourne des données pour la cellule de modèle la plus proche (~1-5 km). La station météo "virtuelle" peut être à plusieurs kilomètres du Parc de Champagne. Les micro-conditions locales (couloir de vent, ombrage) ne sont pas capturées.

**Résolution temporelle**
Données horaires uniquement. Si la météo a évolué au cours de la séance (~20-30 minutes), on ne dispose que d'un seul point de mesure.

**Indice UV**
Non disponible pour les dates de nuit/soir. Apparaît comme `null` dans `meteo.json` pour les séances S1 (17h30), S3 (18h30).

---

## 3. Biais potentiels dans l'analyse

### Biais de sélection / petit échantillon

Avec 4 coureurs et 4 séances maximum, tout résultat statistique est fragile. Une corrélation observée entre température et performance pourrait disparaître avec 10 séances supplémentaires. Les visualisations montrent des **tendances observables**, pas des faits établis.

### Biais de confusion

Les variables météo sont toutes corrélées entre elles : les séances froides (S3, S4) sont aussi les plus humides. Il est impossible de démêler l'effet de la température de l'effet de l'humidité ou de la pluie avec seulement 4 points.

### Hétérogénéité des niveaux

Arthur (temps 400m : ~57s) est dans une catégorie différente des autres (~1:15–1:35). Comparer leurs FC, cadences ou puissances de façon absolue n'a pas de sens. Les visualisations en % de progression ou en W/kg atténuent ce biais sans l'éliminer.

### Facteurs non mesurés

Aucune donnée sur : alimentation avant séance, qualité du sommeil, état de fatigue accumulée, échauffement préalable, équipement (chaussures), stress psychologique. Ces variables peuvent avoir un impact sur la performance comparable ou supérieur à celui de la météo.

### Biais de motivation / effet caméra

Savoir qu'on est filmé/mesuré peut influencer l'effort fourni. Les 4 coureurs ne produisent pas forcément le même effort relatif à leur capacité maximale à chaque séance.

---

## 4. Limites des visualisations

**Section 2 (Temps & Météo) — droite de tendance**
La droite de régression est tracée avec seulement 4 points par coureur maximum. Sa pente et sa direction n'ont aucune valeur prédictive fiable.

**Section 7 (Récupération cardiaque)**
La récupération cardiaque dépend fortement de l'intensité de l'effort qui précède. Si deux coureurs ont des FC de départ différentes (ex: 190 vs 165), comparer leur vitesse de descente absolue est trompeur. Une normalisation par la FC de départ serait plus rigoureuse.

**Section 11 (Tour 1 / 2 / 3)**
La détection des 3 tours repose sur les bornes du Tour 2 connues. Tour 1 et Tour 3 peuvent inclure des transitions (marche, changement de sens) si le coureur ne s'arrête pas entre les tours.

**Section 15 (Puissance W/kg)**
La puissance Garmin est une estimation algorithmique, pas une mesure directe (il faudrait un capteur de puissance dédié comme un Stryd). Elle est donc doublement approximative : estimation + référence au profil d'Arthur.

---

## 5. Ce que ce projet démontre malgré ses limites

Indépendamment des limites statistiques, ce projet démontre :

1. **La faisabilité d'un pipeline complet** : ingestion → stockage → visualisation → automatisation, sur des données réelles collectées sur le terrain
2. **L'importance du niveau de granularité** : les données FIT second-par-second révèlent des informations invisibles dans les résumés CSV — splits, profils de vitesse, récupération
3. **La valeur de la correction des biais** : la normalisation W/kg et kcal/km change les classements entre coureurs — sans elle, l'analyse serait faussée
4. **Des tendances cohérentes avec la physiologie** : FC plus basse par temps froid à effort égal, profils d'accélération différenciés, récupération variable selon la condition physique

---

## 6. Perspectives d'amélioration

- Augmenter le nombre de séances (objectif : 8-10 minimum pour analyses statistiques)
- Ajouter un capteur de puissance dédié (Stryd) pour mesure directe
- Collecter les conditions physiologiques (sommeil, alimentation) via formulaire avant chaque séance
- Intégrer la qualité de l'air (AQI, PM2.5) via OpenAQ ou ATMO Grand Est
- Utiliser les données GPS pour calculer l'angle vent/direction de course — impact théoriquement mesurable au-dessus de 20 km/h