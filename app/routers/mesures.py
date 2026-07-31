"""
=========================================================
TERRA — Routes Mesures (/api/v1/mesures)

POST /  → point d'entrée des capteurs RÉELS (ESP32 → HTTP),
          toutes les 5 heures. Formats du champ `donnees` :
            capacitif sol : {"humidite": 27.6}
            DHT22         : {"temperature": 27.6, "humidite": 30}
          (valeurs numériques uniquement — les unités sont
          l'affaire de l'interface, pas de la base)
GET  /  → lecture (graphiques, dashboard)

Chaque mesure reçue est diffusée en WebSocket (mesure_update) :
les dashboards ouverts se mettent à jour instantanément.
=========================================================
"""

from fastapi import APIRouter, Depends, Query

from app.config.database import get_supabase
from app.routers.auth import utilisateur_courant
from app.schemas.auth import MeResponse
from app.schemas.mesure import MesureCreate, MesureOut
from app.services import alerte_expert, mesure_service, moteur_expert
from app.services.mesure_service import extraire_grandeurs
from app.websocket.manager import manager

router = APIRouter(prefix="/api/v1/mesures", tags=["Mesures"])


@router.get("", response_model=list[MesureOut], summary="Lire les mesures")
def lister(
    id_capteur: int | None = Query(None, description="Filtrer par capteur"),
    id_parcelle: int | None = Query(None, description="Filtrer par parcelle (tous ses capteurs)"),
    limit: int = Query(100, ge=1, le=1000),
    user: MeResponse = Depends(utilisateur_courant),
) -> list[MesureOut]:
    return mesure_service.lister(user, id_capteur=id_capteur, id_parcelle=id_parcelle, limit=limit)


@router.post("", response_model=MesureOut, status_code=201, summary="Enregistrer une mesure (capteur)")
async def ajouter(corps: MesureCreate, user: MeResponse = Depends(utilisateur_courant)) -> MesureOut:
    """Contrat des capteurs IoT : {id_capteur, donnees}. Le payload est
    validé selon le type du capteur, puis la mesure est diffusée en
    WebSocket (dashboard temps réel, sans rechargement) et déclenche
    les alertes immédiates (humidité critique, chaleur, froid…)."""
    mesure, capteur = mesure_service.ajouter(user, corps)
    await manager.broadcast({"type": "mesure_update", "data": mesure.model_dump(mode="json")})

    sb = get_supabase()
    stade = moteur_expert.stade_actuel(sb, capteur["id_parcelle"])
    grandeurs = extraire_grandeurs(capteur["type"], mesure.donnees)
    await alerte_expert.verifier_mesure(sb, capteur["id_parcelle"], grandeurs, stade)

    return mesure
