"""
=========================================================
TERRA — MOTEUR EXPERT (aide à la décision d'irrigation)
=========================================================
C'est la classe « MoteurExpert «control» » du diagramme de
classes : il raisonne comme un CONSEILLER AGRICOLE et écrit
ses prescriptions dans la table `prescription`, toutes les
5 minutes (planificateur de main.py) — rafraîchissement quasi
temps réel des recommandations sur le dashboard.

Documentation complète : docs/MOTEUR_EXPERT.md
(règles FAO, règles ANADER, formule d'évaporation, priorités).

ENTRÉES (toutes réelles, lues en base) :
  1. profil_culture   → stade courant (Kc FAO, seuils d'humidité
                        volumétrique du sol définis par l'admin)
  2. mesure           → dernières mesures des capteurs réels :
                        capacitif sol (humidité du sol) et DHT22
                        (température + humidité de l'air)
  3. meteo_mesures    → météo actuelle (OpenWeather, stockée)
  4. meteo_previsions → Tmin/Tmax et pluie des prochaines 24 h
  5. parcelle         → jour de culture (date_plantation), latitude

CALCUL CENTRAL — L'ÉVAPORATION :
  ET0 (mm/jour) est estimée par HARGREAVES-SAMANI (FAO-56, éq. 52) :
      ET0 = 0.0023 × Ra × (Tmoy + 17.8) × √(Tmax − Tmin)
  où Ra est le rayonnement extraterrestre (FAO-56, éq. 21-26),
  calculé exactement depuis la latitude et le jour julien.
  Le besoin de la CULTURE est ETc = ET0 × Kc (coefficient cultural
  FAO du stade courant). ETc est PERSISTÉE dans
  parcelle.evaporation_mm et diffusée en WebSocket → le dashboard
  affiche l'évaporation en temps réel.

ARBRE DE DÉCISION (règles FAO F1-F5 + règles ANADER A1-A4) :
  F0  pas de mesure d'humidité fraîche  → vérifier les capteurs
  F1  humidité ≤ humidite_min           → irrigation URGENTE
  F2  humidité <  seuil_bas             → irriguer (ou reporter si
                                          la pluie prévue ramène le
                                          sol au-dessus du seuil)
  F3  humidité <  seuil_cible           → irrigation d'entretien si
                                          l'ETc dépasse la pluie
  F4  humidité ≥ humidite_max           → NE PAS irriguer (asphyxie)
  F5  plage confortable                 → aucune irrigation
  A1  toute irrigation conseillée tôt le matin ou en fin de journée
      (limiter les pertes par évaporation)
  A2  chaleur ≥ 35 °C                   → paillage + arrosage au
                                          crépuscule, priorité relevée
  A3  humidité de l'air ≥ 85 % en floraison/fructification
                                        → vigilance mildiou : ne pas
                                          mouiller le feuillage

DOSE (mm = L/m²) :
  recharge sol = (seuil_cible − humidité) × 3 mm par point %
                 (1 % volumétrique sur 30 cm de sol = 3 mm d'eau)
  dose brute   = recharge + ETc(24 h) − pluie prévue(24 h)
  dose finale  = dose brute ÷ 0.90 (efficacité goutte-à-goutte),
                 bornée à 15 mm par prescription (sécurité).

VOLUME & DURÉE (dépendent de la SURFACE de la parcelle) :
  litres total = dose × surface (1 mm sur 1 m² = 1 litre)
  durée        = litres total ÷ débit du réseau (L/min), décomposée
                 en minutes / secondes / millisecondes ; les minutes
                 sont stockées dans prescription.duree_irrigation_minutes.

FORMAT des recommandations (langage conseiller agricole) :
  action        = « Lancez l'irrigation pendant X minutes… environ
                    Y Litres pour l'ensemble de la parcelle » (ou
                    l'action à mener si pas d'arrosage) ;
  justification = le POURQUOI, appuyé sur les données réelles
                  (humidité mesurée, stade, pluie prévue).

GARANTIES :
  - le moteur RAFRAÎCHIT son avis (les anciennes prescriptions
    « a_faire » marquées [Moteur expert] passent à « ignoree ») ;
  - si la décision est IDENTIQUE à l'avis déjà actif (même action,
    même dose, même priorité), rien n'est réécrit — pas de spam ;
  - les prescriptions saisies à la main sont préservées ;
  - une parcelle en erreur ne bloque jamais les autres ;
  - chaque insertion est diffusée en WebSocket (temps réel).

ALERTES IMMÉDIATES (hors cycle des 5 min) : voir
  services/alerte_expert.py — humidité critique, chaleur/froid,
  capteur muet, pluie forte, irrigation trop retardée, consommation
  anormale. Documentées dans docs/MOTEUR_EXPERT.md, section 7.
=========================================================
"""

import logging
import math
from datetime import datetime, timedelta, timezone

from app.config.config import get_settings
from app.config.database import get_supabase
from app.services import alerte_expert
from app.services.mesure_service import extraire_grandeurs
from app.websocket.manager import manager

logger = logging.getLogger("terra.moteur")

PROFONDEUR_RACINAIRE_MM = 300.0   # repli si stade inconnu (voir _profondeur_racinaire_mm)
EFFICACITE_IRRIGATION = 0.90      # goutte-à-goutte (aspersion ≈ 0.75)
DOSE_MAX_MM = 15.0                # plafond par prescription (anti sur-arrosage)
DOSE_MIN_MM = 2.0                 # en dessous, l'apport est insignifiant
FRAICHEUR_MESURE_H = 24           # une mesure plus vieille n'est plus fiable
HORIZON_PLUIE_H = 24              # fenêtre de prise en compte de la pluie prévue
SEUIL_CANICULE_C = 35.0           # règle ANADER A2 : chaleur extrême
SEUIL_HUMIDITE_AIR_MALADIE = 85.0 # règle ANADER A3 : risque fongique (mildiou)
# Débit du réseau d'irrigation de l'exploitation (litres/minute). Sert à
# convertir le VOLUME total à apporter (qui dépend de la surface) en une
# DURÉE d'arrosage concrète — plus la parcelle est grande, plus il faut
# de litres, donc plus l'arrosage dure. Valeur par défaut : pompe agricole
# ~30 m³/h. À ajuster à la pompe réelle de l'exploitation.
DEBIT_L_PAR_MIN = 500.0
M2_PAR_HECTARE = 10000.0
MARQUE = "[Moteur expert]"        # signature → permet le rafraîchissement

# Cache de détection des colonnes optionnelles (migration non encore jouée)
_colonnes_connues: dict[str, bool] = {}


def _colonne_existe(sb, table: str, colonne: str) -> bool:
    """Teste (une seule fois, puis mémorise) si une colonne existe —
    pour rester fonctionnel avant l'exécution de la migration SQL."""
    cle = f"{table}.{colonne}"
    if cle not in _colonnes_connues:
        try:
            sb.table(table).select(colonne).limit(1).execute()
            _colonnes_connues[cle] = True
        except Exception:
            _colonnes_connues[cle] = False
    return _colonnes_connues[cle]


# =========================================================
# VOLUME & DURÉE D'IRRIGATION (dépendent de la surface — règle 5)
# =========================================================
def calcul_volume_duree(dose_mm: float, superficie_ha: float | None) -> dict:
    """À partir de la dose (mm = L/m²) et de la surface de la parcelle,
    calcule le VOLUME total d'eau et la DURÉE d'arrosage.

    - litres_total   = dose × surface (1 mm sur 1 m² = 1 litre)
    - total_secondes = volume ÷ débit du réseau (converti en secondes)
    - la durée est décomposée en MINUTES, SECONDES et MILLISECONDES.

    Retourne None si la surface est inconnue (calcul impossible)."""
    if not superficie_ha or superficie_ha <= 0:
        return {"litres_total": None, "total_secondes": None,
                "minutes": None, "secondes": None, "millisecondes": None,
                "duree_minutes_arrondi": None}
    surface_m2 = superficie_ha * M2_PAR_HECTARE
    litres_total = dose_mm * surface_m2
    total_secondes = (litres_total / DEBIT_L_PAR_MIN) * 60.0
    entier = int(total_secondes)
    minutes = entier // 60
    secondes = entier % 60
    millisecondes = round((total_secondes - entier) * 1000)
    return {
        "litres_total": round(litres_total),
        "total_secondes": round(total_secondes, 3),
        "minutes": minutes,
        "secondes": secondes,
        "millisecondes": millisecondes,
        "duree_minutes_arrondi": max(1, round(total_secondes / 60)),
    }


# 1) ÉVAPORATION — formules FAO-56

def rayonnement_extraterrestre(latitude_deg: float, jour_julien: int) -> float:
    """Ra, le rayonnement solaire au sommet de l'atmosphère (FAO-56 éq. 21),
    converti en équivalent d'évaporation (mm/jour, éq. 20 : ×0.408).
    Ne dépend QUE de la latitude et de la date — aucune mesure requise."""
    phi = math.radians(latitude_deg)                                    # latitude (rad)
    dr = 1 + 0.033 * math.cos(2 * math.pi * jour_julien / 365)          # dist. Terre-Soleil (éq. 23)
    delta = 0.409 * math.sin(2 * math.pi * jour_julien / 365 - 1.39)    # déclinaison solaire (éq. 24)
    # Angle horaire au coucher du soleil (éq. 25), argument borné
    x = max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta)))
    omega_s = math.acos(x)
    gsc = 0.0820  # constante solaire (MJ·m⁻²·min⁻¹)
    ra_mj = (24 * 60 / math.pi) * gsc * dr * (
        omega_s * math.sin(phi) * math.sin(delta)
        + math.cos(phi) * math.cos(delta) * math.sin(omega_s)
    )
    return 0.408 * ra_mj  # MJ·m⁻²·j⁻¹ → mm/jour


def et0_hargreaves(tmoy: float, tmin: float, tmax: float,
                   latitude_deg: float, jour_julien: int) -> float:
    """ET0 en mm/jour par Hargreaves-Samani (FAO-56 éq. 52).
    L'amplitude thermique sert d'indicateur indirect du rayonnement
    réel (ciel couvert → amplitude réduite → moins d'évaporation).
    Bornes : amplitude ≥ 1 °C, résultat jamais négatif."""
    amplitude = max(1.0, tmax - tmin)
    ra = rayonnement_extraterrestre(latitude_deg, jour_julien)
    et0 = 0.0023 * ra * (tmoy + 17.8) * math.sqrt(amplitude)
    return max(0.0, round(et0, 2))



def _stade_courant(profils: list[dict], jour_culture: int) -> dict | None:
    """Le stade dont [debut_jour, fin_jour] contient le jour de culture
    (jour 1 = plantation). Hors cycle : premier/dernier stade retenu."""
    if not profils:
        return None
    for p in profils:
        if p["debut_jour"] <= jour_culture <= p["fin_jour"]:
            return p
    return profils[0] if jour_culture < profils[0]["debut_jour"] else profils[-1]


def stade_actuel(sb, id_parcelle: int) -> dict | None:
    """Version autonome de la résolution de stade, pour les appelants
    qui n'ont pas déjà chargé parcelle/profils (ex. les alertes
    immédiates déclenchées juste après l'ingestion d'une mesure)."""
    lignes = sb.table("parcelle").select("date_plantation").eq("id", id_parcelle).limit(1).execute().data
    if not lignes:
        return None
    profils = sb.table("profil_culture").select("*").order("debut_jour").execute().data
    date_plantation = datetime.fromisoformat(str(lignes[0]["date_plantation"])).date()
    jour_culture = (datetime.now(timezone.utc).date() - date_plantation).days + 1
    return _stade_courant(profils, jour_culture)


def _mesures_capteurs(sb, id_parcelle: int) -> dict:
    """Dernières valeurs FRAÎCHES (< 24 h) des capteurs ACTIFS de la
    parcelle, toutes grandeurs confondues :
      {humidite_sol, temperature, humidite_air} — None si absente.
    L'humidité du sol est moyennée sur les 3 dernières mesures pour
    lisser le bruit du capteur capacitif."""
    capteurs = (
        sb.table("capteur").select("id, type")
        .eq("id_parcelle", id_parcelle).eq("etat", "actif")
        .execute().data
    )
    if not capteurs:
        return {"humidite_sol": None, "temperature": None, "humidite_air": None}
    types = {c["id"]: c["type"] for c in capteurs}
    limite = (datetime.now(timezone.utc) - timedelta(hours=FRAICHEUR_MESURE_H)).isoformat()
    mesures = (
        sb.table("mesure").select("id_capteur, donnees, date")
        .in_("id_capteur", list(types))
        .gte("date", limite).order("date", desc=True).limit(30)
        .execute().data
    )
    hum_sol: list[float] = []
    resultat: dict[str, float | None] = {"humidite_sol": None, "temperature": None, "humidite_air": None}
    for m in mesures:  # du plus récent au plus ancien
        grandeurs = extraire_grandeurs(types.get(m["id_capteur"], ""), m["donnees"])
        if "humidite_sol" in grandeurs and len(hum_sol) < 3:
            hum_sol.append(grandeurs["humidite_sol"])
        for cle in ("temperature", "humidite_air"):
            if cle in grandeurs and resultat[cle] is None:
                resultat[cle] = grandeurs[cle]  # la plus récente gagne
    if hum_sol:
        resultat["humidite_sol"] = round(sum(hum_sol) / len(hum_sol), 1)
    return resultat


def _meteo_24h(sb) -> dict:
    """Synthèse des prochaines 24 h depuis les prévisions stockées
    (OpenWeather, rafraîchies toutes les 15 min) : Tmin/Tmax/Tmoy
    prévues et pluie cumulée attendue (mm)."""
    maintenant = datetime.now(timezone.utc)
    horizon = maintenant + timedelta(hours=HORIZON_PLUIE_H)
    prevs = (
        sb.table("meteo_previsions").select("prevu_pour, temperature, pluie_3h")
        .gte("prevu_pour", maintenant.isoformat())
        .lte("prevu_pour", horizon.isoformat())
        .order("prevu_pour").execute().data
    )
    if not prevs:
        return {"disponible": False, "tmin": None, "tmax": None, "tmoy": None, "pluie_mm": 0.0}
    temps = [p["temperature"] for p in prevs if p["temperature"] is not None]
    pluie = sum(p["pluie_3h"] or 0.0 for p in prevs)
    return {
        "disponible": True,
        "tmin": min(temps), "tmax": max(temps),
        "tmoy": sum(temps) / len(temps),
        "pluie_mm": round(pluie, 1),
    }


def _temperature_actuelle(sb) -> float | None:
    """Dernière température observée (meteo_mesures) — repli si les
    prévisions manquent au moment du calcul."""
    rows = (
        sb.table("meteo_mesures").select("temperature")
        .order("mesure_le", desc=True).limit(1).execute().data
    )
    return rows[0]["temperature"] if rows else None


# =========================================================
# 3) FORMULATION — recommandations « conseiller agricole »
# =========================================================
def _decrire_stade(nom_stade: str) -> str:
    """Traduit le stade FAO en langage agriculteur (besoin en eau)."""
    s = nom_stade.lower()
    if "florais" in s:
        return "en pleine floraison, un stade où elles ont très soif"
    if "fructif" in s:
        return "en pleine formation des fruits, un stade très gourmand en eau"
    if "lev" in s or "semis" in s:
        return "encore de jeunes plants, très sensibles au manque d'eau"
    if "croissance" in s:
        return "en pleine croissance, avec des besoins en eau qui augmentent"
    if "matur" in s:
        return "en cours de maturation, avec des besoins en eau modérés"
    if "recolte" in s or "récolte" in s:
        return "en période de récolte"
    return f"au stade « {nom_stade} »"


def _phrase_pluie(pluie: float) -> str:
    """Phrase météo pluie, en langage agriculteur."""
    if pluie <= 0.2:
        return "De plus, aucune pluie n'est prévue aujourd'hui."
    if pluie < 3:
        return f"Une faible pluie ({pluie} mm) est prévue, insuffisante pour couvrir les besoins."
    return f"Une pluie de {pluie} mm est prévue aujourd'hui."


def _profondeur_racinaire_mm(nom_stade: str) -> float:
    """Profondeur racinaire EFFECTIVE (zone d'extraction d'eau), pas la
    profondeur anatomique maximale. FAO-56 tab. 22 : le pivot de la
    tomate peut descendre à 0.7-1.5 m, mais la fiche FAO « Crop Water
    Information: Tomato » précise que 70-80 % de l'extraction d'eau a
    lieu dans les 0.4-0.6 m supérieurs. Cibler la profondeur anatomique
    max (ex. 1.5 m) sur-arroserait et lessiverait les engrais au-delà de
    la zone réellement exploitée par la plante — on cible donc la zone
    d'extraction effective, pas le maximum anatomique.
    PROFONDEUR_RACINAIRE_MM reste le repli si le stade est inconnu."""
    s = nom_stade.lower()
    if "semis" in s or "lev" in s:
        return 200.0   # stade initial/repiquage : le plant s'installe
    if "croissance" in s:
        return 300.0   # les racines colonisent le sol
    if "florais" in s or "fructif" in s:
        return 500.0   # cœur du système racinaire actif
    if "matur" in s or "recolte" in s or "récolte" in s:
        return 600.0   # profondeur d'extraction maximale avant lessivage
    return PROFONDEUR_RACINAIRE_MM  # stade non reconnu : repli documenté (30 cm)


def analyser_parcelle(sb, parcelle: dict, profils: list[dict], meteo: dict) -> dict:
    """Analyse UNE parcelle et formule une recommandation en langage
    de conseiller agricole (deux volets « Pourquoi » / « Recommandation »).

    Retourne :
      {"prescription": dict|None, "etc_mm": float, "et0_mm": float,
       "duree_min": int|None}
    - `action`        : ce qu'il faut faire (durée d'arrosage + volume
                        total pour la parcelle, ou l'action à mener) ;
    - `justification` : le POURQUOI, appuyé sur les données réelles ;
    - `duree_min`     : durée d'arrosage en minutes (dépend de la surface).
    `etc_mm` (l'évaporation) est TOUJOURS calculée, même sans action."""
    settings = get_settings()

    # ---- Contexte plante : jour de culture et stade FAO ----------
    date_plantation = datetime.fromisoformat(str(parcelle["date_plantation"])).date()
    jour_culture = (datetime.now(timezone.utc).date() - date_plantation).days + 1
    stade = _stade_courant(profils, jour_culture)
    if stade is None:
        logger.warning("profil_culture vide — le moteur ne peut pas raisonner.")
        return {"prescription": None, "etc_mm": None, "et0_mm": None, "duree_min": None}

    kc = stade.get("kc") or 1.0
    seuil_bas = stade.get("seuil_bas")
    seuil_cible = stade.get("seuil_cible")
    hum_min = stade.get("humidite_min") or seuil_bas
    hum_max = stade.get("humidite_max")
    nom_stade = stade["stade"]
    stade_txt = _decrire_stade(nom_stade)
    superficie = parcelle.get("superficie")
    # Profondeur racinaire DYNAMIQUE (dépend du stade, pas une constante
    # unique) : 1% d'humidité volumétrique sur CETTE profondeur = X mm.
    mm_par_point = _profondeur_racinaire_mm(nom_stade) * 0.01

    # ---- Évaporation : ET0 (Hargreaves, FAO-56) puis ETc = ET0×Kc --
    lat = parcelle.get("lat") or settings.default_lat
    jour_julien = datetime.now(timezone.utc).timetuple().tm_yday
    if meteo["disponible"]:
        tmoy, tmin, tmax = meteo["tmoy"], meteo["tmin"], meteo["tmax"]
    else:
        # Repli documenté : sans prévision, amplitude ±4 °C autour de
        # la dernière température observée.
        t_actuelle = _temperature_actuelle(sb) or 28.0
        tmoy, tmin, tmax = t_actuelle, t_actuelle - 4, t_actuelle + 4
    et0 = et0_hargreaves(tmoy, tmin, tmax, lat, jour_julien)
    etc = round(et0 * kc, 1)          # besoin de la culture (mm / 24 h)
    pluie = meteo["pluie_mm"]

    # ---- Mesures des capteurs réels (sol + DHT22 air) -------------
    capteurs = _mesures_capteurs(sb, parcelle["id"])
    humidite = capteurs["humidite_sol"]
    t_air = capteurs["temperature"]
    h_air = capteurs["humidite_air"]

    # ---- Règles ANADER transverses --------------------------------
    # A2 — chaleur extrême : capteur DHT22 prioritaire, sinon Tmax prévue
    canicule = (t_air is not None and t_air >= SEUIL_CANICULE_C) or \
               (meteo["disponible"] and meteo["tmax"] >= SEUIL_CANICULE_C)
    # A3 — risque fongique : air très humide pendant floraison/fructification
    stade_sensible = any(m in nom_stade.lower() for m in ("florais", "fructif"))
    risque_mildiou = h_air is not None and h_air >= SEUIL_HUMIDITE_AIR_MALADIE and stade_sensible
    # A1 — le moment d'arroser (conseil systématique ANADER)
    moment = "à l'aube ou en fin de journée (forte chaleur)" if canicule else "tôt le matin"

    def presc(action, justification, volume, priorite, duree_min=None):
        return {
            "prescription": {"action": action, "justification": f"{MARQUE} {justification}",
                             "volume_eau": volume, "priorite": priorite},
            "etc_mm": etc, "et0_mm": et0, "duree_min": duree_min,
        }

    def phrase_irrigation(dose_mm):
        """Construit l'action « Lancez l'irrigation pendant X minutes… »
        + les compléments ANADER (moment, canicule, mildiou)."""
        d = calcul_volume_duree(dose_mm, superficie)
        extras = []
        if canicule:
            extras.append("Il fait très chaud : paillez le pied pour limiter l'évaporation.")
        if risque_mildiou:
            extras.append("Arrosez uniquement au pied, sans mouiller les feuilles (risque de mildiou).")
        suffixe = (" " + " ".join(extras)) if extras else ""
        if d["duree_minutes_arrondi"] is not None:
            # Pas de plan sur 2 apports (matin/soir) : le moteur se
            # ré-évalue toutes les 5 min sur les mesures réelles — c'est
            # LUI qui décide s'il faut arroser à nouveau plus tard, pas
            # une consigne figée donnée à l'avance qui deviendrait fausse
            # si l'humidité remonte après ce premier apport.
            action = (
                f"Lancez l'irrigation pendant {d['duree_minutes_arrondi']} minutes, "
                f"idéalement {moment}. Cela correspond à environ "
                f"{d['litres_total']} Litres d'eau pour l'ensemble de la parcelle.{suffixe}"
            )
            return action, d["duree_minutes_arrondi"]
        # Surface inconnue : on ne peut pas donner minutes/litres totaux
        action = (
            f"Lancez l'irrigation pour apporter environ {dose_mm} litres par m², "
            f"idéalement {moment} (renseignez la superficie de la parcelle pour "
            f"obtenir la durée exacte).{suffixe}"
        )
        return action, None

    # ---- F0 : pas de mesure fiable → aucune décision à l'aveugle ---
    if humidite is None:
        return presc(
            "Veuillez vérifier si le capteur est bien branché ou s'il a besoin d'être "
            "rechargé (panneau solaire/batterie). En attendant, fiez-vous à votre "
            "observation visuelle de la terre.",
            "Nous n'avons reçu aucune donnée du capteur d'humidité du sol depuis plus de "
            "24 heures. Le calcul automatique est suspendu par sécurité pour éviter de "
            "noyer la plante.",
            0.0, "moyenne")

    # ---- Calcul de dose FAO (utilisé par F1/F2/F3) -----------------
    recharge = max(0.0, (seuil_cible - humidite) * mm_par_point)
    dose_brute = recharge + etc - pluie
    dose = round(min(DOSE_MAX_MM, max(0.0, dose_brute) / EFFICACITE_IRRIGATION), 1)

    # ---- F4 : sol saturé — la sur-irrigation est aussi un danger ---
    if hum_max is not None and humidite >= hum_max:
        return presc(
            "N'arrosez pas aujourd'hui. Vérifiez plutôt que l'eau s'évacue bien du sol "
            "(drainage) pour ne pas étouffer les racines.",
            f"Le sol est déjà gorgé d'eau ({humidite} % d'humidité, au-dessus du plafond de "
            f"sécurité de {hum_max} %). Un excès d'eau ferait pourrir les racines et "
            f"favoriserait les maladies.",
            0.0, "moyenne")

    # ---- F1 : stress sévère — on irrigue, pluie ou pas -------------
    if hum_min is not None and humidite <= hum_min:
        vol = max(dose, DOSE_MIN_MM)
        action, duree = phrase_irrigation(vol)
        return presc(
            action,
            f"Le sol est très sec ({humidite} % d'humidité) et vos tomates sont {stade_txt}. "
            f"La plante est déjà en souffrance : il faut agir maintenant, sans attendre la pluie.",
            vol, "haute", duree)

    # ---- F2 : sous le seuil de déclenchement -----------------------
    if humidite < seuil_bas:
        # Report si la pluie prévue RAMÈNE le sol au-dessus du seuil.
        besoin_retour_seuil = (seuil_bas - humidite) * mm_par_point + etc
        if pluie > 0 and pluie >= besoin_retour_seuil:
            return presc(
                "N'arrosez pas maintenant : laissez la pluie faire le travail. "
                "Nous réévaluerons la situation au prochain contrôle.",
                f"Le sol est un peu sec ({humidite} % d'humidité), mais une pluie de "
                f"{pluie} mm est attendue aujourd'hui — elle suffira à réhydrater la terre.",
                0.0, "basse")
        action, duree = phrase_irrigation(dose)
        return presc(
            action,
            f"Le sol est sec ({humidite} % d'humidité) et vos tomates sont {stade_txt}. "
            f"{_phrase_pluie(pluie)}",
            dose, "haute", duree)

    # ---- F3 : entre seuil et cible — compenser le climat si besoin --
    if humidite < seuil_cible and etc > pluie:
        dose_entretien = round(min(DOSE_MAX_MM, (etc - pluie) / EFFICACITE_IRRIGATION), 1)
        if dose_entretien >= DOSE_MIN_MM:
            action, duree = phrase_irrigation(dose_entretien)
            return presc(
                action,
                f"L'humidité du sol est correcte ({humidite} %), mais la chaleur du jour va "
                f"évaporer plus d'eau que la pluie n'en apporte. Un petit apport maintient "
                f"vos plants {stade_txt} à leur niveau idéal.",
                dose_entretien, "moyenne", duree)

    # ---- A3 seule : rien à irriguer mais risque sanitaire ----------
    if risque_mildiou:
        return presc(
            "N'arrosez pas le feuillage. Surveillez les feuilles et, si besoin, arrosez "
            "uniquement au pied de la plante.",
            f"L'humidité du sol est correcte ({humidite} %), mais l'air est très humide "
            f"({h_air} %) pendant la floraison — des conditions qui favorisent le mildiou.",
            0.0, "basse")

    # ---- F5 : plage confortable — le silence est aussi une décision.
    return {"prescription": None, "etc_mm": etc, "et0_mm": et0, "duree_min": None}


# =========================================================
# 4) EXÉCUTION GLOBALE — planificateur (5 min) et route manuelle
# =========================================================
async def executer(ids_parcelles: list[int] | None = None) -> dict:
    """Fait tourner le moteur sur les parcelles demandées (ou toutes) :
      1. calcule et PERSISTE l'évaporation (parcelle.evaporation_mm) ;
      2. si la décision est identique à l'avis déjà actif (même action,
         même dose, même priorité), NE RENVOIE RIEN — la cadence est
         rapprochée (5 min) mais on ne spamme pas tant que la situation
         est stable ;
      3. sinon, remplace l'ancien avis « a_faire » (jamais de doublons)
         et insère la nouvelle prescription, diffusée en WebSocket.
    Une parcelle en erreur n'empêche JAMAIS les autres d'être traitées."""
    sb = get_supabase()
    bilan = {"parcelles_analysees": 0, "prescriptions_creees": 0, "details": []}

    profils = sb.table("profil_culture").select("*").order("debut_jour").execute().data

    requete = sb.table("parcelle").select("*")
    if ids_parcelles:
        requete = requete.in_("id", ids_parcelles)
    parcelles = requete.execute().data

    meteo = _meteo_24h(sb)  # la même fenêtre météo sert à toutes les parcelles

    for parcelle in parcelles:
        bilan["parcelles_analysees"] += 1
        try:
            resultat = analyser_parcelle(sb, parcelle, profils, meteo)

            # --- Persister l'évaporation calculée (affichage temps réel) ---
            if resultat["etc_mm"] is not None:
                try:
                    sb.table("parcelle").update(
                        {"evaporation_mm": resultat["etc_mm"]}
                    ).eq("id", parcelle["id"]).execute()
                    parcelle["evaporation_mm"] = resultat["etc_mm"]
                    await manager.broadcast({"type": "parcelle_update", "data": parcelle})
                except Exception as exc:
                    logger.warning(
                        "evaporation_mm non persistée (exécutez db/migration_prod.sql) : %s", exc
                    )

            # --- Avis actif actuel du moteur (pour comparaison de stabilité
            #     et pour le rafraîchissement) ---
            anciennes = (
                sb.table("prescription").select("id, justification, action, volume_eau, priorite, cree_le")
                .eq("id_parcelle", parcelle["id"]).eq("etat", "a_faire")
                .execute().data
            )
            actives_moteur = [p for p in anciennes if (p["justification"] or "").startswith(MARQUE)]

            # --- Alertes de cycle (capteur muet, pluie forte, irrigation
            #     en attente depuis trop longtemps) — indépendantes de la
            #     stabilité de la recommandation elle-même. ---
            try:
                await alerte_expert.verifier_cycle(
                    parcelle["id"],
                    _mesures_capteurs(sb, parcelle["id"]).get("humidite_sol"),
                    meteo,
                    anciennes,
                )
            except Exception as exc:
                logger.warning("Alertes de cycle — échec sur %s : %s", parcelle.get("nom"), exc)

            prescription = resultat["prescription"]

            if prescription is None:
                # Situation rentrée dans l'ordre : on efface l'ancien avis
                # du moteur s'il y en avait un (rien à faire maintenant).
                if actives_moteur:
                    sb.table("prescription").update({"etat": "ignoree"}) \
                        .in_("id", [p["id"] for p in actives_moteur]).execute()
                bilan["details"].append({"parcelle": parcelle["nom"],
                                         "decision": "Aucune action nécessaire",
                                         "etc_mm": resultat["etc_mm"]})
                continue

            # --- Stabilité : cadence 5 min, mais si la décision est
            #     IDENTIQUE à l'avis déjà actif (même action, même dose,
            #     même priorité, ET MÊME JUSTIFICATION), on ne réécrit
            #     rien — pas de spam tant que la mesure/situation n'a pas
            #     réellement changé. La justification est INCLUSE dans la
            #     comparaison exprès : elle porte le chiffre d'humidité
            #     mesuré, donc dès qu'il varie (même sans changer de
            #     règle F1-F5), l'avis est considéré différent et
            #     rafraîchi — les chiffres affichés ne peuvent plus
            #     devenir obsolètes pendant que la carte "État de la
            #     parcelle" continue d'afficher la valeur en direct. ---
            stable = any(
                a["action"] == prescription["action"]
                and a["volume_eau"] == prescription["volume_eau"]
                and a["priorite"] == prescription["priorite"]
                and a["justification"] == prescription["justification"]
                for a in actives_moteur
            )
            if stable:
                bilan["details"].append({"parcelle": parcelle["nom"],
                                         "decision": "Stable — aucun nouvel avis",
                                         "etc_mm": resultat["etc_mm"]})
                continue

            # --- Rafraîchir l'avis : les anciens « a_faire » du moteur
            #     passent à « ignoree » (les manuels sont préservés) ---
            if actives_moteur:
                sb.table("prescription").update({"etat": "ignoree"}) \
                    .in_("id", [p["id"] for p in actives_moteur]).execute()

            ligne = {
                "id_parcelle": parcelle["id"],
                "date": datetime.now(timezone.utc).date().isoformat(),
                "etat": "a_faire",
                **prescription,
            }
            # Durée d'arrosage (min) — n'insérée que si la colonne existe
            # (avant migration, la prescription reste créée sans elle).
            if resultat.get("duree_min") is not None and \
                    _colonne_existe(sb, "prescription", "duree_irrigation_minutes"):
                ligne["duree_irrigation_minutes"] = resultat["duree_min"]

            insere = sb.table("prescription").insert(ligne).execute().data[0]

            await manager.broadcast({"type": "prescription_update", "data": insere})

            bilan["prescriptions_creees"] += 1
            bilan["details"].append({"parcelle": parcelle["nom"],
                                     "decision": prescription["action"],
                                     "etc_mm": resultat["etc_mm"]})
            logger.info("Moteur expert — %s : %s", parcelle["nom"], prescription["action"])
        except Exception as exc:  # jamais bloquant pour les autres parcelles
            logger.warning("Moteur expert — échec sur %s : %s", parcelle.get("nom"), exc)
            bilan["details"].append({"parcelle": parcelle.get("nom"), "decision": f"Erreur : {exc}"})

    if bilan["prescriptions_creees"]:
        await manager.broadcast({"type": "prescriptions_bulk",
                                 "data": {"prescriptions_inserees": bilan["prescriptions_creees"],
                                          "id_parcelle": None}})
    return bilan
