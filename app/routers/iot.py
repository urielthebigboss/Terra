"""
=========================================================
TERRA — Routes d'ingestion IoT (/api/v1/iot)

Point d'entrée des DISPOSITIFS physiques (passerelle ESP32), par
opposition à /api/v1/mesures qui est l'API des humains/frontend
(protégée par JWT utilisateur + ACL parcelle).

Ici l'authentification se fait par CLÉ DEVICE (en-tête X-Device-Key)
— un ESP32 ne peut pas porter de session Supabase. Chaque paquet
reçu est validé, normalisé, stocké, diffusé en WebSocket, puis
déclenche le moteur expert sur la parcelle concernée.
=========================================================
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, status

from app.schemas.iot import IotIngestPayload, IotIngestResponse
from app.services import iot_service, moteur_expert
from app.websocket.manager import manager

logger = logging.getLogger("terra.iot")

router = APIRouter(prefix="/api/v1/iot", tags=["IoT"])

# ---------------------------------------------------------
# Dépendance : authentification par clé device
# ---------------------------------------------------------
def require_device_key(x_device_key: str | None = Header(None)) -> None:
    """Valide l'en-tête X-Device-Key avant tout traitement."""
    iot_service.verifier_cle_device(x_device_key)


async def _declencher_moteur(id_parcelle: int) -> None:
    """Relance le moteur expert sur une parcelle, sans jamais faire
    échouer l'ingestion si le moteur rencontre un souci (il repassera
    de toute façon à son cycle régulier de 5 min)."""
    try:
        await moteur_expert.executer(ids_parcelles=[id_parcelle])
    except Exception as exc:  # noqa: BLE001 — tâche de fond, on log et on continue
        logger.warning("Moteur expert (post-ingestion parcelle %s) échoué : %s", id_parcelle, exc)


@router.post(
    "/ingest",
    response_model=IotIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingestion d'un paquet de nœud (passerelle ESP32)",
    dependencies=[Depends(require_device_key)],
)
async def ingest(payload: IotIngestPayload, taches: BackgroundTasks) -> IotIngestResponse:
    """Reçoit le paquet agrégé d'un nœud (DHT22 + capacitif), écrit
    les mesures valides, met à jour les dashboards en temps réel et
    relance le moteur expert."""
    id_parcelle, creees, ignorees = iot_service.ingerer(payload)

    # Temps réel : chaque mesure écrite est diffusée au format attendu
    # par le frontend (mêmes clés que MesureOut : id, id_capteur, date,
    # donnees). Les dashboards ouverts se mettent à jour sans recharger.
    for m in creees:
        await manager.broadcast({
            "type": "mesure_update",
            "data": {"id": m.id, "id_capteur": m.id_capteur, "date": m.date.isoformat(), "donnees": m.donnees},
        })

    # Moteur expert : relancé APRÈS la réponse (BackgroundTasks) pour ne
    # pas faire attendre la passerelle. Uniquement si des données sont
    # réellement arrivées.
    moteur_declenche = False
    if creees:
        taches.add_task(_declencher_moteur, id_parcelle)
        moteur_declenche = True

    return IotIngestResponse(
        status="ok" if creees else "aucune_mesure",
        node_id=payload.sensor_node_id,
        id_parcelle=id_parcelle,
        mesures_creees=creees,
        ignorees=ignorees,
        moteur_declenche=moteur_declenche,
    )

@router.get(
    "/ping",
    summary="Test de connectivité pour la passerelle",
    dependencies=[Depends(require_device_key)],
)
def ping() -> dict:
    """Permet au boîtier central de vérifier, au démarrage, que le
    backend est joignable ET que sa clé device est acceptée."""
    from datetime import datetime, timezone

    return {"ok": True, "service": "terra-iot", "time": datetime.now(timezone.utc).isoformat()}
