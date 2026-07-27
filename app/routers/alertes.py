"""
=========================================================
TERRA — Routes Alertes (/api/v1/alertes)
L'agriculteur suit ses signalements ; l'administrateur fait
avancer le workflow : en_attente → en_intervention → repare → cloture.
=========================================================
"""

from fastapi import APIRouter, Depends, Query

from app.routers.auth import admin_requis, utilisateur_courant
from app.schemas.alerte import AlerteOut, AlerteUpdate
from app.schemas.auth import MeResponse
from app.schemas.capteur import CapteurOut
from app.services import alerte_service
from app.services.acces import get_capteur_ou_404
from app.websocket.manager import manager

router = APIRouter(prefix="/api/v1/alertes", tags=["Alertes"])


@router.get("", response_model=list[AlerteOut], summary="Lister les alertes visibles")
def lister(
    etat: str | None = Query(None, description="Filtrer par état (en_attente, en_intervention…)"),
    user: MeResponse = Depends(utilisateur_courant),
) -> list[AlerteOut]:
    """Admin → toutes ; agriculteur → celles qu'il a émises."""
    return alerte_service.lister(user, etat=etat)


@router.patch("/{id_alerte}", response_model=AlerteOut, summary="Faire avancer une alerte (admin)")
async def changer_etat(
    id_alerte: int, corps: AlerteUpdate, admin: MeResponse = Depends(admin_requis)
) -> AlerteOut:
    """Passer à « repare » remet automatiquement le capteur associé
    en « actif ». Le changement est diffusé en WebSocket."""
    alerte = alerte_service.changer_etat(admin, id_alerte, corps)
    await manager.broadcast({"type": "alerte_update", "data": alerte.model_dump(mode="json")})
    # Réparé → le capteur est repassé en « actif » : on le diffuse aussi
    if corps.etat == "repare" and alerte.id_capteur:
        capteur = CapteurOut(**get_capteur_ou_404(alerte.id_capteur))
        await manager.broadcast({"type": "capteur_update", "data": capteur.model_dump(mode="json")})
    return alerte
