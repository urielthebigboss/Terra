"""
=========================================================
TERRA — Alertes immédiates du moteur expert
=========================================================
Complète le cycle de recommandation (toutes les 5 min, voir
moteur_expert.py) par des ALERTES INSTANTANÉES : déclenchées dès
qu'une condition critique est détectée, sans attendre le prochain
cycle. Elles sont UNIQUEMENT diffusées en WebSocket (type
"alerte_expert") — ce ne sont PAS des tickets de réparation
matérielle (voir la table `alerte`, réservée aux pannes de capteur
signalées par l'agriculteur, avec son propre cycle de vie
en_attente → en_intervention → repare).

Deux points de déclenchement :
  1. juste après l'ingestion d'une mesure (routers/iot.py et
     routers/mesures.py) → conditions lisibles sur UNE mesure seule
     (humidité critique/saturée, chaleur, froid, donnée invalide) ;
  2. dans le cycle du moteur expert, toutes les 5 min
     (services/moteur_expert.py) → conditions qui nécessitent un
     historique (capteur muet, pluie forte prévue, irrigation trop
     retardée, consommation d'eau anormale).

Toutes les valeurs utilisées sont réelles (mesures des capteurs,
prévisions météo stockées, seuils du profil_culture) — aucune
alerte n'est déclenchée sur une donnée inventée.
=========================================================
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from app.websocket.manager import manager

logger = logging.getLogger("terra.alertes")


def _irrigation_validee_aujourdhui(sb, id_parcelle: int) -> bool:
    """Une mission d'irrigation (volume_eau > 0) a-t-elle été validée
    AUJOURD'HUI sur cette parcelle ? Sert à suspendre l'alerte "sol
    saturé" juste après un arrosage volontaire.

    Granularité JOUR (pas de l'heure) : `prescription.date_faite` ne
    stocke que la date, pas l'instant précis de validation. C'est une
    approximation documentée — une colonne d'horodatage précis
    (`ALTER TABLE prescription ADD COLUMN heure_faite timestamptz`)
    permettrait une fenêtre de suspension plus courte (ex. 90 min) si
    besoin d'une précision plus fine."""
    try:
        rows = (
            sb.table("prescription").select("id")
            .eq("id_parcelle", id_parcelle).eq("etat", "faite")
            .gt("volume_eau", 0)
            .eq("date_faite", date.today().isoformat())
            .limit(1).execute().data
        )
        return bool(rows)
    except Exception:
        return False  # en cas de doute, on ne masque pas l'alerte

# ---------- Seuils (voir docs/MOTEUR_EXPERT.md, section Alertes) ----------
SEUIL_FROID_C = 12.0             # tomate : croissance stoppée en dessous
SEUIL_CANICULE_C = 35.0          # identique à la règle ANADER A2 du moteur
SEUIL_PLUIE_FORTE_MM = 20.0      # pluie prévue jugée « forte » sur 24 h
DELAI_IRRIGATION_URGENTE_H = 3   # prescription haute non traitée depuis + longtemps
FACTEUR_CONSO_ANORMALE = 1.5     # marge au-dessus du volume max théorique d'UNE dose


async def _emettre(id_parcelle: int, code: str, gravite: str, message: str) -> None:
    """Diffuse une alerte en WebSocket — jamais persistée en base (pas
    un ticket, une notification temps réel)."""
    logger.warning("ALERTE [%s/%s] parcelle %s : %s", code, gravite, id_parcelle, message)
    await manager.broadcast({
        "type": "alerte_expert",
        "data": {
            "id_parcelle": id_parcelle,
            "code": code,
            "gravite": gravite,  # "haute" | "moyenne"
            "message": message,
            "date": datetime.now(timezone.utc).isoformat(),
        },
    })


# =========================================================
# 1) Alertes jugées sur UNE mesure fraîchement reçue
# =========================================================
async def verifier_mesure(sb, id_parcelle: int, grandeurs: dict, stade: dict | None) -> None:
    """Appelée juste après l'insertion d'une mesure (ingestion IoT ou
    saisie manuelle /mesures) — ne nécessite aucun historique.

    IMPORTANT : l'humidité du sol est réévaluée avec la MÊME moyenne
    lissée (3 dernières mesures) que le moteur expert utilise pour sa
    recommandation — jamais la valeur brute instantanée seule. Sinon,
    l'alerte et la recommandation peuvent se contredire pendant une
    variation rapide (bruit du capteur, test manuel)."""
    if "humidite_sol" in grandeurs and stade:
        from app.services.moteur_expert import _mesures_capteurs
        h = _mesures_capteurs(sb, id_parcelle).get("humidite_sol")
        if h is None:
            h = grandeurs["humidite_sol"]  # repli si l'agrégation échoue
        seuil_min = stade.get("humidite_min")
        seuil_max = stade.get("humidite_max")
        if seuil_min is not None and h <= seuil_min:
            await _emettre(
                id_parcelle, "sol_critique", "haute",
                f"Humidité du sol critique ({h} %) — en dessous du seuil minimal "
                f"({seuil_min} %), risque de stress hydrique sévère pour la plante.",
            )
        elif seuil_max is not None and h >= seuil_max and not _irrigation_validee_aujourdhui(sb, id_parcelle):
            # Une irrigation volontaire fait saturer le sol LOCALEMENT,
            # le temps que l'eau se redistribue — ce n'est pas une
            # anomalie si on vient justement d'arroser cette parcelle.
            await _emettre(
                id_parcelle, "sol_sature", "moyenne",
                f"Sol saturé en eau ({h} %) — au-dessus du seuil maximal "
                f"({seuil_max} %), risque d'asphyxie racinaire.",
            )

    if "temperature" in grandeurs:
        t = grandeurs["temperature"]
        if t >= SEUIL_CANICULE_C:
            await _emettre(
                id_parcelle, "canicule", "haute",
                f"Température de l'air très élevée ({t} °C) — risque de stress "
                f"thermique, pensez au paillage et à l'arrosage au crépuscule.",
            )
        elif t <= SEUIL_FROID_C:
            await _emettre(
                id_parcelle, "froid", "moyenne",
                f"Température de l'air basse ({t} °C) — croissance de la tomate "
                f"ralentie en dessous de {SEUIL_FROID_C} °C, surveillez la culture.",
            )


async def verifier_donnee_invalide(id_parcelle: int, champ: str, valeur) -> None:
    """Une valeur reçue est hors bornes physiquement plausibles — le
    capteur est probablement défaillant, débranché ou saturé."""
    await _emettre(
        id_parcelle, "capteur_invalide", "moyenne",
        f"Donnée hors limites reçue ({champ} = {valeur}) — vérifiez le capteur "
        f"(court-circuit, fil débranché ou saturation possible).",
    )


# =========================================================
# 2) Alertes qui nécessitent un historique — 1 fois par cycle (5 min)
# =========================================================
async def verifier_cycle(
    id_parcelle: int,
    humidite_sol_fraiche,
    meteo: dict,
    prescriptions_actives: list[dict],
) -> None:
    """Appelée une fois par parcelle à chaque cycle du moteur expert."""
    # Capteur muet : aucune mesure d'humidité du sol fraîche (< 24 h)
    if humidite_sol_fraiche is None:
        await _emettre(
            id_parcelle, "capteur_muet", "haute",
            "Aucune donnée du capteur d'humidité du sol depuis plus de 24 heures "
            "— vérifiez son alimentation (panneau solaire/batterie) et sa connexion.",
        )

    # Pluie forte prévue : le moteur en tient déjà compte dans sa dose,
    # mais l'agriculteur doit être prévenu tout de suite (drainage).
    if meteo.get("disponible") and meteo.get("pluie_mm", 0) >= SEUIL_PLUIE_FORTE_MM:
        await _emettre(
            id_parcelle, "pluie_forte", "moyenne",
            f"Pluie forte prévue aujourd'hui ({meteo['pluie_mm']} mm) — le moteur "
            f"expert en tiendra compte, vérifiez le drainage de la parcelle.",
        )

    # Irrigation urgente en attente depuis trop longtemps
    for p in prescriptions_actives:
        if p.get("priorite") != "haute":
            continue
        cree_le = p.get("cree_le")
        if not cree_le:
            continue
        try:
            horodatage = datetime.fromisoformat(str(cree_le).replace("Z", "+00:00"))
            age_h = (datetime.now(timezone.utc) - horodatage).total_seconds() / 3600
        except ValueError:
            continue
        if age_h >= DELAI_IRRIGATION_URGENTE_H:
            await _emettre(
                id_parcelle, "irrigation_retardee", "haute",
                f"Une irrigation urgente est en attente depuis {round(age_h)} h — "
                f"la plante reste en stress hydrique tant que la mission n'est pas validée.",
            )
            break  # une seule alerte de ce type par cycle suffit


# =========================================================
# 3) Consommation d'eau anormale — à la validation d'une mission
# =========================================================
async def verifier_consommation(
    id_parcelle: int, volume_valide: float, superficie_ha: float | None
) -> None:
    """Compare le volume réellement validé au plafond théorique d'UNE
    dose du moteur expert (DOSE_MAX_MM), avec une marge de sécurité —
    signale une fuite ou une erreur de saisie possible."""
    from app.services.moteur_expert import DOSE_MAX_MM, M2_PAR_HECTARE

    if not superficie_ha or superficie_ha <= 0 or not volume_valide:
        return
    plafond_theorique = DOSE_MAX_MM * superficie_ha * M2_PAR_HECTARE * FACTEUR_CONSO_ANORMALE
    if volume_valide > plafond_theorique:
        await _emettre(
            id_parcelle, "conso_anormale", "moyenne",
            f"Volume d'eau apporté anormalement élevé ({round(volume_valide)} L, "
            f"attendu ≤ {round(plafond_theorique)} L pour cette parcelle) — vérifiez "
            f"qu'il n'y a pas de fuite ou d'erreur de saisie.",
        )
