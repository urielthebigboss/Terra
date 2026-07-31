

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.config.config import get_settings
from app.config.database import get_supabase
from app.schemas.iot import IotIngestPayload, IotMesureCreee
from app.services.mesure_service import extraire_grandeurs

logger = logging.getLogger("terra.iot")

# ---------------------------------------------------------
# Bornes de plausibilité physique. Une valeur hors de ces
# bornes trahit un capteur défaillant (court-circuit, fil
# débranché, saturation ADC) : on refuse de la stocker.
# ---------------------------------------------------------
BORNES = {
    "temperature": (-20.0, 60.0),   # °C — air sous abri agricole
    "humidite_air": (0.0, 100.0),   # % HR
    "humidite_sol": (0.0, 100.0),   # % volumétrique (déjà calibré côté nœud)
}

# Types de capteur attendus pour chaque grandeur du payload.
#   payload -> (grandeur interne, type de capteur cible)
_ROUTAGE = {
    "temperature_air": ("temperature", "dht22"),
    "humidity_air": ("humidite_air", "dht22"),
    "soil_moisture": ("humidite_sol", "humidite_sol"),
}


# =========================================================
# 1) Authentification de la passerelle (clé device)
# =========================================================
def verifier_cle_device(cle: str | None) -> None:
    """401 si la clé fournie dans X-Device-Key n'est pas autorisée.

    Fail-safe : si AUCUNE clé n'est configurée côté serveur
    (IOT_DEVICE_KEYS vide), l'ingestion est refusée en bloc — on ne
    veut pas d'un endpoint ouvert par défaut."""
    autorisees = get_settings().iot_device_keys_set
    if not autorisees:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion IoT désactivée : aucune clé device configurée (IOT_DEVICE_KEYS).",
        )
    if not cle or cle not in autorisees:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé device invalide ou absente (en-tête X-Device-Key).",
        )


# =========================================================
# 2) Résolution du nœud → parcelle + capteurs
# =========================================================
def _resoudre_noeud(node_id: str) -> tuple[int, dict[str, dict]]:
    """Retrouve les capteurs rattachés à un nœud physique.

    Retourne (id_parcelle, {type_capteur: ligne_capteur}). 404 si le
    nœud est inconnu (aucun capteur ne porte ce node_id). 409 si ses
    capteurs sont, par erreur de provisioning, sur des parcelles
    différentes."""
    rows = (
        get_supabase().table("capteur").select("*").eq("node_id", node_id).execute().data
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nœud « {node_id} » inconnu — provisionnez ses capteurs (voir migration_iot.sql).",
        )
    parcelles = {r["id_parcelle"] for r in rows}
    if len(parcelles) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Nœud « {node_id} » relié à plusieurs parcelles {parcelles} — corrigez le provisioning.",
        )
    par_type = {r["type"]: r for r in rows}
    return parcelles.pop(), par_type


# =========================================================
# 3) Plausibilité d'une grandeur
# =========================================================
def _plausible(grandeur: str, valeur: float) -> bool:
    bas, haut = BORNES.get(grandeur, (float("-inf"), float("inf")))
    # NaN échoue toujours les comparaisons → correctement rejeté.
    return valeur == valeur and bas <= valeur <= haut  # noqa: PLR0124 (valeur==valeur = filtre NaN)


# =========================================================
# 4) Ingestion complète d'un paquet
# =========================================================
def ingerer(payload: IotIngestPayload) -> tuple[int, list[IotMesureCreee], list[str], list[tuple[str, float]]]:
    """Traite un paquet de nœud et écrit les mesures valides.

    Retourne (id_parcelle, mesures_creees, ignorees, invalides).
    N'insère que des grandeurs réellement mesurées et plausibles ; ne
    lève une erreur que pour les problèmes structurels (nœud inconnu,
    clé invalide gérée en amont). `invalides` liste les grandeurs
    reçues mais hors bornes physiques (champ, valeur) — utilisé pour
    déclencher une alerte immédiate « capteur défaillant »."""
    supabase = get_supabase()
    id_parcelle, capteurs_par_type = _resoudre_noeud(payload.sensor_node_id)
    quand = (payload.measured_at or datetime.now(timezone.utc)).isoformat()

    ignorees: list[str] = []
    invalides: list[tuple[str, float]] = []

    # --- 4a. Filtrer + router les grandeurs vers leur capteur -----
    # On regroupe par id_capteur : le DHT22 combine 2 grandeurs dans
    # UNE ligne mesure ({"temperature":..,"humidite":..}).
    donnees_par_capteur: dict[int, tuple[dict, str]] = {}  # id_capteur -> (donnees, type)

    for champ, (grandeur, type_cible) in _ROUTAGE.items():
        valeur = getattr(payload, champ)
        if valeur is None:
            continue  # capteur non fourni (panne/absent) — silencieux, normal
        if not _plausible(grandeur, float(valeur)):
            ignorees.append(f"{champ} (hors bornes : {valeur})")
            invalides.append((champ, float(valeur)))
            logger.warning("Nœud %s : %s hors bornes (%s) — écarté.", payload.sensor_node_id, champ, valeur)
            continue
        capteur = capteurs_par_type.get(type_cible)
        if capteur is None:
            ignorees.append(f"{champ} (aucun capteur « {type_cible} » sur ce nœud)")
            continue
        # Clé JSONB interne : le DHT22 stocke l'humidité de l'air sous
        # « humidite », la température sous « temperature » ; le capteur
        # de sol stocke l'humidité du sol sous « humidite ».
        cle_json = "temperature" if grandeur == "temperature" else "humidite"
        donnees, _ = donnees_par_capteur.setdefault(capteur["id"], ({}, capteur["type"]))
        donnees[cle_json] = float(valeur)

    # --- 4b. Insérer une ligne par capteur (avec anti-doublon) ----
    creees: list[IotMesureCreee] = []
    for id_capteur, (donnees, type_capteur) in donnees_par_capteur.items():
        # Garde-fou : le JSONB doit être lisible par le point unique.
        if not extraire_grandeurs(type_capteur, donnees):
            ignorees.append(f"capteur {id_capteur} (payload non reconnu)")
            continue
        # Anti-doublon durable : même capteur + même horodatage déjà en base
        # (renvoi réseau de la passerelle) → on ne réécrit pas.
        deja = (
            supabase.table("mesure")
            .select("id")
            .eq("id_capteur", id_capteur)
            .eq("date", quand)
            .limit(1)
            .execute()
            .data
        )
        if deja:
            ignorees.append(f"capteur {id_capteur} (doublon {quand})")
            continue

        res = supabase.table("mesure").insert(
            {"id_capteur": id_capteur, "date": quand, "donnees": donnees}
        ).execute()
        row = res.data[0]
        supabase.table("capteur").update({"derniere_comm": quand}).eq("id", id_capteur).execute()
        creees.append(
            IotMesureCreee(
                id=row["id"], id_capteur=id_capteur, type=type_capteur,
                donnees=donnees, date=row["date"],
            )
        )

    logger.info(
        "Ingestion nœud %s (seq %s) : %s mesure(s) écrite(s), %s ignorée(s).",
        payload.sensor_node_id, payload.sequence_number, len(creees), len(ignorees),
    )
    return id_parcelle, creees, ignorees, invalides
